from datetime import UTC, datetime

from pydantic import BaseModel


class Location(BaseModel):
    latitude: float
    longitude: float


class Forecast(BaseModel):
    times: list[str]
    temperatures: list[float]


class WeatherReport(BaseModel):
    address: str
    location: Location
    forecast: Forecast


class HourlyTemperature(BaseModel):
    time: datetime
    temperatureCelsius: float


class ForecastResponse(BaseModel):
    address: str
    latitude: float
    longitude: float
    hourly: list[HourlyTemperature]

    @classmethod
    def from_report(cls, report: WeatherReport) -> "ForecastResponse":
        return cls(
            address=report.address,
            latitude=report.location.latitude,
            longitude=report.location.longitude,
            hourly=[
                HourlyTemperature(time=datetime.fromisoformat(time).replace(tzinfo=UTC), temperatureCelsius=celsius)
                for time, celsius in zip(report.forecast.times, report.forecast.temperatures, strict=True)
            ],
        )
