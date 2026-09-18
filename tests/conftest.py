import httpx
import pytest

from meteo.models import Forecast, Location
from meteo.ports import Forecaster, Geocoder


class FakeGeocoder(Geocoder):
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.error: Exception | None = None

    def geocode(self, address: str) -> Location:
        self.calls.append(address)
        if self.error:
            raise self.error
        return Location(latitude=48.85, longitude=2.35)


class FakeForecaster(Forecaster):
    def __init__(self) -> None:
        self.calls: list[Location] = []

    def forecast(self, location: Location) -> Forecast:
        self.calls.append(location)
        return Forecast(times=["2026-09-18T00:00"], temperatures=[17.2])


@pytest.fixture
def geocoder() -> FakeGeocoder:
    return FakeGeocoder()


@pytest.fixture
def forecaster() -> FakeForecaster:
    return FakeForecaster()


@pytest.fixture
def stub_client():
    def make(payload, status=200, seen: list[httpx.Request] | None = None) -> httpx.Client:
        def handler(request: httpx.Request) -> httpx.Response:
            if seen is not None:
                seen.append(request)
            return httpx.Response(status, json=payload)

        return httpx.Client(transport=httpx.MockTransport(handler))

    return make
