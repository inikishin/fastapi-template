"""
Baseline Keycloak authentication middleware.

Copied into src/middlewares/keycloak_middleware.py by the initial-setup skill
on demand. It handles only the generic OIDC flow:

  1. Collects the public routes.
  2. Validates the incoming Bearer token against Keycloak.
  3. Loads (or upserts) the user from the local DB by keycloak_id.
  4. Attaches AuthCredentials(["authenticated"]) + the user instance to the scope.

Domain-specific extensions (role mapping, contractor handling, 1C linking, etc.)
belong to the report-microservice skill and must be added next to this middleware,
not inlined into it.

Prerequisites — before enabling this middleware:
  - The User model has the columns documented in user_columns_snippet.py.
  - The migration adding those columns has been applied
    (see migration_example.py for the shape).
  - AppConfig has the KEYCLOAK_* fields and they are filled in .env.
  - UserManager exposes get_user_by_keycloak_id(keycloak_id=..., ...) —
    it is expected to upsert the user with data from the token.
"""

from datetime import datetime, timezone

from jwcrypto.common import JWException
from keycloak import KeycloakError, KeycloakOpenID
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
)
from starlette.requests import HTTPConnection

from src.config.logger import LoggerProvider
from src.config.postgres.db_config import get_async_session
from src.config.settings import app_config
from src.models.managers.user import UserManager

log = LoggerProvider().get_logger(__name__)

# Routes that never require authentication.
PUBLIC_ROUTES: set[str] = {
    "/docs",
    "/api/docs",
    "/api/openapi",
    "/api/openapi.json",
    "/favicon.ico",
    "/api/v1/healthcheck",
}

# URL prefixes that never require authentication (partial match, startswith).
PUBLIC_ROUTE_PREFIXES: tuple[str, ...] = ()


class KeycloakMiddleware(AuthenticationBackend):
    """Validates Bearer tokens issued by Keycloak and loads the matching user."""

    def __init__(self):
        self.keycloak_openid = KeycloakOpenID(
            server_url=app_config.keycloak_server_url,
            client_id=app_config.keycloak_client_id,
            realm_name=app_config.keycloak_realm,
            client_secret_key=app_config.keycloak_client_secret,
            verify=app_config.keycloak_verify_ssl,
        )

    async def authenticate(self, conn: HTTPConnection):
        if self._is_public(conn):
            return None

        if conn.scope.get("method") == "OPTIONS":
            return None

        auth_header = conn.headers.get("Authorization")
        if not auth_header:
            err = AuthenticationError("Not authenticated")
            err.status_code = 401
            raise err

        token = self._extract_token(auth_header)

        try:
            await self.keycloak_openid.a_introspect(token)
            decoded = await self.keycloak_openid.a_decode_token(token=token)
        except (KeycloakError, JWException, ValueError) as e:
            log.debug(f"Token validation failed: {e}")
            raise AuthenticationError(str(e))

        keycloak_id = decoded.get("sub")
        if not keycloak_id:
            raise AuthenticationError("Token is missing 'sub' claim")

        async with get_async_session() as session:
            user_manager = UserManager(session)
            user = await user_manager.get_user_by_keycloak_id(
                keycloak_id=keycloak_id,
                username=decoded.get("preferred_username"),
                first_name=decoded.get("given_name"),
                last_name=decoded.get("family_name"),
                email=decoded.get("email"),
                last_login=datetime.now(timezone.utc),
            )

        if user is None:
            raise AuthenticationError("User is not allowed in this service")

        return AuthCredentials(["authenticated"]), user

    @staticmethod
    def _is_public(conn: HTTPConnection) -> bool:
        if conn.url.path in PUBLIC_ROUTES:
            return True
        return any(conn.url.path.startswith(prefix) for prefix in PUBLIC_ROUTE_PREFIXES)

    @staticmethod
    def _extract_token(auth_header: str) -> str:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        # Allow raw tokens for legacy clients.
        return parts[0]
