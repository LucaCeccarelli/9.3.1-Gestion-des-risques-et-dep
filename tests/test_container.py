from meteo.adapters.ban import BanGeocoder
from meteo.adapters.met_norway import MetNorwayForecaster
from meteo.adapters.nominatim import NominatimGeocoder
from meteo.adapters.open_meteo import OpenMeteoForecaster
from meteo.container import Container

UA = "TP2-MeteoApi/1.0 test@example.org"


def configured(geocoder: str, forecaster: str) -> Container:
    container = Container()
    container.config.from_dict({"geocoder": geocoder, "forecaster": forecaster, "user_agent": UA})
    return container


def test_new_providers_are_selected_by_config():
    service = configured("ban", "met_norway").weather_service()

    assert isinstance(service.geocoder, BanGeocoder)
    assert isinstance(service.forecaster, MetNorwayForecaster)


def test_legacy_providers_remain_available():
    service = configured("nominatim", "open_meteo").weather_service()

    assert isinstance(service.geocoder, NominatimGeocoder)
    assert isinstance(service.forecaster, OpenMeteoForecaster)


def test_user_agent_comes_from_config():
    assert configured("ban", "met_norway").http_client().headers["user-agent"] == UA


def test_defaults_when_env_is_unset():
    container = Container()

    assert container.config.geocoder() == "nominatim"
    assert container.config.forecaster() == "open_meteo"
    assert container.config.user_agent() == "TP2-MeteoApi/1.0 luca.ceccarelli@etu.mines-ales.fr"
