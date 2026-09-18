from meteo.models import WeatherReport
from meteo.ports import Forecaster, Geocoder


class WeatherService:
    """Enchaîne géocodage puis prévision. Ne dépend que des ports abstraits."""

    def __init__(self, geocoder: Geocoder, forecaster: Forecaster) -> None:
        self.geocoder = geocoder
        self.forecaster = forecaster

    def report(self, address: str) -> WeatherReport:
        location = self.geocoder.geocode(address)
        return WeatherReport(address=address, location=location, forecast=self.forecaster.forecast(location))
