async def test_get_user_by_id_returns_200(client):
    """GET /api/v1/user/{id} returns a user loaded from the dump."""
    response = await client.get("/api/v1/user/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
    }


async def test_get_user_by_id_not_found(client):
    """GET /api/v1/user/{id} with a missing id returns 404 with a typed body."""
    response = await client.get("/api/v1/user/999999")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "404"
    assert "User not found" in body["message"]
