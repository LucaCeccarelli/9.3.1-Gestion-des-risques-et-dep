import httpx
from dependency_injector import containers, providers

from meteo.adapters.ban import BanGeocoder
from meteo.adapters.met_norway import MetNorwayForecaster
from meteo.adapters.nominatim import NominatimGeocoder
from meteo.adapters.open_meteo import OpenMeteoForecaster
from meteo.services import WeatherService


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    config.geocoder.from_env("METEO_GEOCODER", default="nominatim")
    config.forecaster.from_env("METEO_FORECASTER", default="open_meteo")
    config.user_agent.from_env("METEO_USER_AGENT", default="TP2-MeteoApi/1.0 luca.ceccarelli@etu.mines-ales.fr")

    http_client = providers.ThreadSafeSingleton(
        httpx.Client, timeout=10, headers=providers.Dict({"User-Agent": config.user_agent})
    )
    geocoder = providers.Selector(
        config.geocoder,
        nominatim=providers.Factory(NominatimGeocoder, client=http_client),
        ban=providers.Factory(BanGeocoder, client=http_client),
    )
    forecaster = providers.Selector(
        config.forecaster,
        open_meteo=providers.Factory(OpenMeteoForecaster, client=http_client),
        met_norway=providers.Factory(MetNorwayForecaster, client=http_client),
    )
    weather_service = providers.Factory(WeatherService, geocoder=geocoder, forecaster=forecaster)
