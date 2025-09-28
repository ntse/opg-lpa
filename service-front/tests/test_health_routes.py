from http import HTTPStatus


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["status"] == "ok"
    assert "timestamp" in payload


def test_ping(client):
    response = client.get("/ping")
    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["ping"] == "pong"
    assert "timestamp" in payload
