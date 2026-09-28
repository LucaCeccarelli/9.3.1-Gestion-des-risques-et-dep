import httpx

from meteo.models import Location
from meteo.ports import AddressNotFound, Geocoder

BAN_URL = "https://api-adresse.data.gouv.fr/search/"


class BanGeocoder(Geocoder):
    def __init__(self, client: httpx.Client) -> None:
        self.client = client

    def geocode(self, address: str) -> Location:
        response = self.client.get(BAN_URL, params={"q": address, "limit": 1})
        response.raise_for_status()
        features = response.json().get("features") or []
        if not features:
            raise AddressNotFound(address)
        longitude, latitude = features[0]["geometry"]["coordinates"]
        return Location(latitude=latitude, longitude=longitude)
