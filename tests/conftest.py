import pytest

from meteo.domain import Forecast, Location


class FakeGeocoder:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.error: Exception | None = None

    def geocode(self, address: str) -> Location:
        self.calls.append(address)
        if self.error:
            raise self.error
        return Location(48.85, 2.35)


class FakeForecaster:
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
