from datetime import datetime

import httpx

from meteo.models import Forecast, Location
from meteo.ports import Forecaster

MET_NORWAY_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"


class MetNorwayForecaster(Forecaster):
    def __init__(self, client: httpx.Client) -> None:
        self.client = client

    def forecast(self, location: Location) -> Forecast:
        response = self.client.get(
            MET_NORWAY_URL, params={"lat": round(location.latitude, 4), "lon": round(location.longitude, 4)}
        )
        response.raise_for_status()
        series = response.json().get("properties", {}).get("timeseries") or []
        return Forecast(
            times=[datetime.fromisoformat(entry["time"]).strftime("%Y-%m-%dT%H:%M") for entry in series],
            temperatures=[entry["data"]["instant"]["details"]["air_temperature"] for entry in series],
        )
