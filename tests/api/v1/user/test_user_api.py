def test_client(client):
    user_id = 1
    _assert_response_body = {
        "id": 1,
        "username": "ilyanikishin",
        "email": "inikishin@gmail.com",
    }
    response = client.get(f"/api/v1/user/{user_id}")
    assert response.status_code == 200

    response_json = response.json()
    assert response_json == _assert_response_body
