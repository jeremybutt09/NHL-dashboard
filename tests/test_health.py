def test_health_returns_200(client):
    response = client.get('/api/health')
    assert response.status_code == 200


def test_health_returns_ok_and_connected(client):
    response = client.get('/api/health')
    data = response.get_json()
    assert data['ok'] is True
    assert data['db'] == 'connected'
