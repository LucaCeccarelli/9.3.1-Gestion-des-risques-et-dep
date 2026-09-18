import httpx
from dependency_injector import containers, providers

from meteo.adapters.nominatim import NominatimGeocoder
from meteo.adapters.open_meteo import OpenMeteoForecaster
from meteo.services import WeatherService


class Container(containers.DeclarativeContainer):
    """Composition root : déclare le graphe d'objets, câblé sur meteo.main."""

    # Politique d'usage Nominatim : un User-Agent identifiant est obligatoire.
    http_client = providers.Singleton(httpx.Client, timeout=10, headers={"User-Agent": "meteo-tp1"})
    geocoder = providers.Factory(NominatimGeocoder, client=http_client)
    forecaster = providers.Factory(OpenMeteoForecaster, client=http_client)
    weather_service = providers.Factory(WeatherService, geocoder=geocoder, forecaster=forecaster)
