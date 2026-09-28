from collections.abc import MutableMapping

from meteo.models import Location
from meteo.ports import Geocoder


class CachedGeocoder(Geocoder):
    def __init__(self, geocoder: Geocoder, cache: MutableMapping[str, Location]) -> None:
        self.geocoder = geocoder
        self.cache = cache

    def geocode(self, address: str) -> Location:
        location = self.cache.get(address)
        if location is None:
            location = self.cache[address] = self.geocoder.geocode(address)
        return location
