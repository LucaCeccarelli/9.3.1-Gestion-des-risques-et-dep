import httpx

from meteo.domain import AddressNotFound, Forecast, Location

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class NominatimGeocoder:
    def __init__(self, client: httpx.Client) -> None:
        self.client = client

    def geocode(self, address: str) -> Location:
        response = self.client.get(NOMINATIM_URL, params={"q": address, "format": "json", "limit": 1})
        response.raise_for_status()
        results = response.json()
        if not results:
            raise AddressNotFound(address)
        return Location(float(results[0]["lat"]), float(results[0]["lon"]))


class OpenMeteoForecaster:
    def __init__(self, client: httpx.Client) -> None:
        self.client = client

    def forecast(self, location: Location) -> Forecast:
        params = {"latitude": location.latitude, "longitude": location.longitude, "hourly": "temperature_2m"}
        response = self.client.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
        hourly = response.json()["hourly"]
        return Forecast(times=hourly["time"], temperatures=hourly["temperature_2m"])
