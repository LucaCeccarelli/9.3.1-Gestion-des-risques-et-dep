import httpx
import pytest

from meteo.adapters.nominatim import NominatimGeocoder
from meteo.adapters.open_meteo import OpenMeteoForecaster
from meteo.models import Forecast, Location
from meteo.ports import AddressNotFound, Forecaster, Geocoder


def fake_client(payload, status=200, seen: list[httpx.Request] | None = None) -> httpx.Client:
    """httpx.Client whose transport answers every request with `payload`; records requests in `seen`."""

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_adapters_implement_the_ports():
    client = fake_client([])
    assert isinstance(NominatimGeocoder(client), Geocoder)
    assert isinstance(OpenMeteoForecaster(client), Forecaster)


def test_nominatim_maps_first_result_to_location():
    seen: list[httpx.Request] = []
    client = fake_client([{"lat": "44.125", "lon": "4.081"}, {"lat": "0", "lon": "0"}], seen=seen)

    assert NominatimGeocoder(client).geocode("Alès") == Location(latitude=44.125, longitude=4.081)
    assert seen[0].url.host == "nominatim.openstreetmap.org"
    assert seen[0].url.params["q"] == "Alès"
    assert seen[0].url.params["format"] == "json"


def test_nominatim_raises_address_not_found_on_empty_result():
    with pytest.raises(AddressNotFound):
        NominatimGeocoder(fake_client([])).geocode("nowhere at all")


def test_nominatim_raises_on_http_error():
    with pytest.raises(httpx.HTTPStatusError):
        NominatimGeocoder(fake_client([], status=503)).geocode("Alès")


def test_open_meteo_maps_hourly_to_forecast():
    seen: list[httpx.Request] = []
    payload = {"hourly": {"time": ["2026-09-18T00:00", "2026-09-18T01:00"], "temperature_2m": [17.2, 16.8]}}
    client = fake_client(payload, seen=seen)

    forecast = OpenMeteoForecaster(client).forecast(Location(latitude=48.85, longitude=2.35))

    assert forecast == Forecast(times=["2026-09-18T00:00", "2026-09-18T01:00"], temperatures=[17.2, 16.8])
    assert seen[0].url.host == "api.open-meteo.com"
    assert seen[0].url.params["latitude"] == "48.85"
    assert seen[0].url.params["longitude"] == "2.35"
    assert seen[0].url.params["hourly"] == "temperature_2m"


def test_open_meteo_raises_on_http_error():
    with pytest.raises(httpx.HTTPStatusError):
        OpenMeteoForecaster(fake_client({}, status=500)).forecast(Location(latitude=48.85, longitude=2.35))
