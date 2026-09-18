from meteo.models import Forecast, Location, WeatherReport
from meteo.services import WeatherService


def test_report_chains_geocoder_then_forecaster(geocoder, forecaster):
    report = WeatherService(geocoder, forecaster).report("Paris")

    assert geocoder.calls == ["Paris"]
    assert forecaster.calls == [Location(latitude=48.85, longitude=2.35)]
    assert report == WeatherReport(
        address="Paris",
        location=Location(latitude=48.85, longitude=2.35),
        forecast=Forecast(times=["2026-09-18T00:00"], temperatures=[17.2]),
    )
