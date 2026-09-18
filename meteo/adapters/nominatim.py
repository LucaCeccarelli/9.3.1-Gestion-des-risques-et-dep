import httpx

from meteo.models import Location
from meteo.ports import AddressNotFound, Geocoder

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


class NominatimGeocoder(Geocoder):
    def __init__(self, client: httpx.Client) -> None:
        self.client = client

    def geocode(self, address: str) -> Location:
        response = self.client.get(NOMINATIM_URL, params={"q": address, "format": "json", "limit": 1})
        response.raise_for_status()
        results = response.json()
        if not results:
            raise AddressNotFound(address)
        return Location(latitude=float(results[0]["lat"]), longitude=float(results[0]["lon"]))
