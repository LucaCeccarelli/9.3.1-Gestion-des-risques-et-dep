import httpx
import pytest

from meteo.adapters import NominatimGeocoder, OpenMeteoForecaster
from meteo.domain import AddressNotFound, Forecast, Location


def fake_client(payload, status=200, seen: list[httpx.Request] | None = None) -> httpx.Client:
    """httpx.Client whose transport answers every request with `payload`; records requests in `seen`."""

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_nominatim_maps_first_result_to_location():
    seen: list[httpx.Request] = []
    client = fake_client([{"lat": "44.125", "lon": "4.081"}, {"lat": "0", "lon": "0"}], seen=seen)

    assert NominatimGeocoder(client).geocode("Alès") == Location(44.125, 4.081)
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

    forecast = OpenMeteoForecaster(client).forecast(Location(48.85, 2.35))

    assert forecast == Forecast(times=["2026-09-18T00:00", "2026-09-18T01:00"], temperatures=[17.2, 16.8])
    assert seen[0].url.host == "api.open-meteo.com"
    assert seen[0].url.params["latitude"] == "48.85"
    assert seen[0].url.params["longitude"] == "2.35"
    assert seen[0].url.params["hourly"] == "temperature_2m"


def test_open_meteo_raises_on_http_error():
    with pytest.raises(httpx.HTTPStatusError):
        OpenMeteoForecaster(fake_client({}, status=500)).forecast(Location(48.85, 2.35))
