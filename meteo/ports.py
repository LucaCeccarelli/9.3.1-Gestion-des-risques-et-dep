from abc import ABC, abstractmethod

from meteo.models import Forecast, Location


class AddressNotFound(Exception):
    pass


class Geocoder(ABC):
    @abstractmethod
    def geocode(self, address: str) -> Location: ...


class Forecaster(ABC):
    @abstractmethod
    def forecast(self, location: Location) -> Forecast: ...
