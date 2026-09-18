import httpx

from meteo.models import Forecast, Location
from meteo.ports import Forecaster

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoForecaster(Forecaster):
    def __init__(self, client: httpx.Client) -> None:
        self.client = client

    def forecast(self, location: Location) -> Forecast:
        params = {"latitude": location.latitude, "longitude": location.longitude, "hourly": "temperature_2m"}
        response = self.client.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
        hourly = response.json().get("hourly") or {}
        return Forecast(times=hourly.get("time", []), temperatures=hourly.get("temperature_2m", []))
