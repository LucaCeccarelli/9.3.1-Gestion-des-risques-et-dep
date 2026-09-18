from functools import lru_cache
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query

from meteo.adapters import NominatimGeocoder, OpenMeteoForecaster
from meteo.domain import AddressNotFound, WeatherService

app = FastAPI(title="Météo", description="Adresse postale -> prévisions (Nominatim + Open-Meteo)")


@lru_cache
def get_http_client() -> httpx.Client:
    # Nominatim's usage policy requires an identifying User-Agent.
    return httpx.Client(timeout=10, headers={"User-Agent": "meteo-tp1"})


def get_weather_service(client: Annotated[httpx.Client, Depends(get_http_client)]) -> WeatherService:
    return WeatherService(NominatimGeocoder(client), OpenMeteoForecaster(client))


@app.get("/weather")
def weather(
    address: Annotated[str, Query(min_length=1, description="Adresse postale")],
    service: Annotated[WeatherService, Depends(get_weather_service)],
) -> dict:
    try:
        location, forecast = service.forecast_for(address)
    except AddressNotFound:
        raise HTTPException(status_code=404, detail=f"Address not found: {address}")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream service error: {exc}")
    return {
        "address": address,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "hourly": {"time": forecast.times, "temperature_2m": forecast.temperatures},
    }
