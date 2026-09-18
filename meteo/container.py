import httpx
from dependency_injector import containers, providers

from meteo.adapters.nominatim import NominatimGeocoder
from meteo.adapters.open_meteo import OpenMeteoForecaster
from meteo.services import WeatherService


class Container(containers.DeclarativeContainer):
    http_client = providers.ThreadSafeSingleton(httpx.Client, timeout=10, headers={"User-Agent": "meteo-tp1"})
    geocoder = providers.Factory(NominatimGeocoder, client=http_client)
    forecaster = providers.Factory(OpenMeteoForecaster, client=http_client)
    weather_service = providers.Factory(WeatherService, geocoder=geocoder, forecaster=forecaster)
