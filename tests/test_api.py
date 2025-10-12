import pytest

@pytest.fixture
def client():
    from server.app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'ok'

def test_filter_endpoint_valid(client):
    response = client.post('/filter', json={'title': 'funny cats', 'strength': 0.8})
    assert response.status_code == 200
    assert 'probability' in response.json
    assert 0 <= response.json['probability'] <= 1

def test_filter_endpoint_invalid_strength(client):
    response = client.post('/filter', json={'title': 'test', 'strength': 5.0})
    assert response.status_code == 400
    assert 'error' in response.json
