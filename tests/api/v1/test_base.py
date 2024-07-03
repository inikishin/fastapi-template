def test_index(api_client):
    response = api_client.get("/api/v1")
    assert response.status_code == 200
