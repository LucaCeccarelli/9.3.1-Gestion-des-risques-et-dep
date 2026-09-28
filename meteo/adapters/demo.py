from meteo.models import Forecast, Location
from meteo.ports import Forecaster, Geocoder


class DemoGeocoder(Geocoder):
    def geocode(self, address: str) -> Location:
        return Location(latitude=44.1279, longitude=4.0817)


class DemoForecaster(Forecaster):
    def forecast(self, location: Location) -> Forecast:
        return Forecast(
            times=[f"2025-06-10T{hour:02d}:00" for hour in range(24)],
            temperatures=[15 + hour / 2 for hour in range(24)],
        )
