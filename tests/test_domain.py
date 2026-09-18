from meteo.domain import Forecast, Location, WeatherService


def test_service_chains_geocoder_then_forecaster(geocoder, forecaster):
    location, forecast = WeatherService(geocoder, forecaster).forecast_for("Paris")

    assert geocoder.calls == ["Paris"]
    assert forecaster.calls == [Location(48.85, 2.35)]
    assert location == Location(48.85, 2.35)
    assert forecast == Forecast(times=["2026-09-18T00:00"], temperatures=[17.2])
