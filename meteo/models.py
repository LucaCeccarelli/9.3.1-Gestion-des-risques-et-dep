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
