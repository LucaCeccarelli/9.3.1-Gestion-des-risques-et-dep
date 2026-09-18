import httpx
import pytest
from fastapi.testclient import TestClient

from meteo.domain import AddressNotFound, Location, WeatherService
from meteo.main import app, get_weather_service


@pytest.fixture
def client(geocoder, forecaster) -> TestClient:
    app.dependency_overrides[get_weather_service] = lambda: WeatherService(geocoder, forecaster)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_weather_returns_forecast_for_address(client, geocoder, forecaster):
    response = client.get("/weather", params={"address": "10 rue de Rivoli, 75004 Paris"})

    assert response.status_code == 200
    assert response.json() == {
        "address": "10 rue de Rivoli, 75004 Paris",
        "latitude": 48.85,
        "longitude": 2.35,
        "hourly": {"time": ["2026-09-18T00:00"], "temperature_2m": [17.2]},
    }
    assert geocoder.calls == ["10 rue de Rivoli, 75004 Paris"]
    assert forecaster.calls == [Location(48.85, 2.35)]  # geocoder output flowed into forecaster


def test_missing_address_is_422(client):
    assert client.get("/weather").status_code == 422


def test_empty_address_is_422(client):
    assert client.get("/weather", params={"address": ""}).status_code == 422


def test_unknown_address_is_404(client, geocoder):
    geocoder.error = AddressNotFound("nowhere")
    response = client.get("/weather", params={"address": "nowhere"})
    assert response.status_code == 404
    assert "nowhere" in response.json()["detail"]


def test_upstream_failure_is_502(client, geocoder):
    geocoder.error = httpx.ConnectError("boom")
    assert client.get("/weather", params={"address": "Paris"}).status_code == 502


def test_http_client_sends_identifying_user_agent():
    from meteo.main import get_http_client

    assert get_http_client().headers["user-agent"] == "meteo-tp1"
