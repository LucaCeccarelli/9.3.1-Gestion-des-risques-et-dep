import httpx
import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient

from meteo.main import app
from meteo.models import Location
from meteo.ports import AddressNotFound


@pytest.fixture
def client(geocoder, forecaster) -> TestClient:
    with (
        app.container.geocoder.override(providers.Object(geocoder)),
        app.container.forecaster.override(providers.Object(forecaster)),
        app.container.geocoding_cache.override(providers.Object({})),
    ):
        yield TestClient(app)


def test_get_weather_returns_report_for_address(client, geocoder, forecaster):
    response = client.get("/weather", params={"address": "10 rue de Rivoli, 75004 Paris"})

    assert response.status_code == 200
    assert response.json() == {
        "address": "10 rue de Rivoli, 75004 Paris",
        "latitude": 48.85,
        "longitude": 2.35,
        "hourly": [{"time": "2026-09-18T00:00:00Z", "temperatureCelsius": 17.2}],
    }
    assert geocoder.calls == ["10 rue de Rivoli, 75004 Paris"]
    assert forecaster.calls == [Location(latitude=48.85, longitude=2.35)]  # geocoder output flowed into forecaster


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
    assert app.container.http_client().headers["user-agent"] == "TP2-MeteoApi/1.0 luca.ceccarelli@etu.mines-ales.fr"


def test_composition_root_wires_real_adapters_on_one_shared_client():
    from meteo.adapters.nominatim import NominatimGeocoder
    from meteo.adapters.open_meteo import OpenMeteoForecaster

    service = app.container.weather_service()

    assert isinstance(service.geocoder.geocoder, NominatimGeocoder)
    assert isinstance(service.forecaster, OpenMeteoForecaster)
    assert service.geocoder.geocoder.client is service.forecaster.client is app.container.http_client()


def test_same_address_twice_is_geocoded_once(client, geocoder):
    for _ in range(2):
        assert client.get("/weather", params={"address": "Alès"}).status_code == 200

    assert geocoder.calls == ["Alès"]


def test_demo_mode_uses_simulated_data(client, geocoder, forecaster):
    response = client.get("/weather", params={"address": "zzqqxx nowhere", "demo": "true"})

    assert response.status_code == 200
    body = response.json()
    assert body["address"] == "zzqqxx nowhere"
    assert (body["latitude"], body["longitude"]) == (44.1279, 4.0817)
    assert len(body["hourly"]) == 24
    assert geocoder.calls == forecaster.calls == []


@pytest.mark.parametrize("value", ["false", "0"])
def test_demo_false_uses_real_providers(client, geocoder, value):
    assert client.get("/weather", params={"address": "Paris", "demo": value}).status_code == 200
    assert geocoder.calls == ["Paris"]


def test_invalid_demo_value_is_422(client):
    assert client.get("/weather", params={"address": "Paris", "demo": "banana"}).status_code == 422


def test_demo_mode_still_requires_an_address(client):
    assert client.get("/weather", params={"demo": "true"}).status_code == 422
