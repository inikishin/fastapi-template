"""
User model fields required by the Keycloak middleware.

This file is a reference snippet, not a standalone module. Merge these columns
into the project's User model (src/models/dbo/models.py in compact mode, or the
appropriate file under src/models/dbo/tables/ in extended mode), keep the
existing mixins, and regenerate the Alembic migration.

Required columns:
  - keycloak_id  — unique identifier taken from the token's `sub` claim.
  - first_name, last_name, email — populated from the token on every login.
  - is_admin, is_active — local authorization and soft-disable flags.
  - last_login — stamped on every successful authentication.

Rename or extend as the domain requires, but keep `keycloak_id` unique and
indexed — the middleware relies on an exact lookup by that column.
"""

from sqlalchemy import Boolean, Column, DateTime, String

from src.models.dbo.mixins import IDMixin, TimestampMixin
from src.models.dbo.models import Base  # or `base_model import Base` in extended mode


class User(Base, IDMixin, TimestampMixin):
    """Local user record synchronised from the Keycloak token on login."""

    __tablename__ = "users"

    username = Column(String, nullable=False, index=True)
    first_name = Column(String, nullable=True, index=True)
    last_name = Column(String, nullable=True, index=True)
    email = Column(String, nullable=True, index=True)

    keycloak_id = Column(String, nullable=True, unique=True, index=True)
    is_admin = Column(Boolean, nullable=False, default=False, server_default="false")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    last_login = Column(DateTime(timezone=True), nullable=True)
