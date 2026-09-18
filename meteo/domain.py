from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class Forecast:
    times: list[str]
    temperatures: list[float]


class AddressNotFound(Exception):
    pass


class Geocoder(Protocol):
    def geocode(self, address: str) -> Location: ...


class Forecaster(Protocol):
    def forecast(self, location: Location) -> Forecast: ...


class WeatherService:
    """Chains geocoding then forecasting. Depends only on the two Protocols above."""

    def __init__(self, geocoder: Geocoder, forecaster: Forecaster) -> None:
        self.geocoder = geocoder
        self.forecaster = forecaster

    def forecast_for(self, address: str) -> tuple[Location, Forecast]:
        location = self.geocoder.geocode(address)
        return location, self.forecaster.forecast(location)
