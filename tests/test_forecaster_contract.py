import httpx
import pytest

from meteo.adapters.met_norway import MetNorwayForecaster
from meteo.adapters.open_meteo import OpenMeteoForecaster
from meteo.models import Forecast, Location
from meteo.ports import Forecaster

ALES = Location(latitude=44.125, longitude=4.081)
EXPECTED = Forecast(times=["2026-09-18T00:00", "2026-09-18T01:00"], temperatures=[17.2, 16.8])

CASES = {
    "open_meteo": dict(
        adapter=OpenMeteoForecaster,
        host="api.open-meteo.com",
        found={"hourly": {"time": ["2026-09-18T00:00", "2026-09-18T01:00"], "temperature_2m": [17.2, 16.8]}},
        empty={},
    ),
    "met_norway": dict(
        adapter=MetNorwayForecaster,
        host="api.met.no",
        found={
            "properties": {
                "timeseries": [
                    {"time": "2026-09-18T00:00:00Z", "data": {"instant": {"details": {"air_temperature": 17.2}}}},
                    {"time": "2026-09-18T01:00:00Z", "data": {"instant": {"details": {"air_temperature": 16.8}}}},
                ]
            }
        },
        empty={},
    ),
}


@pytest.fixture(params=list(CASES), ids=list(CASES))
def case(request):
    return CASES[request.param]


def test_is_a_forecaster(case, stub_client):
    assert isinstance(case["adapter"](stub_client(case["found"])), Forecaster)


def test_valid_location_gives_a_forecast(case, stub_client):
    seen: list[httpx.Request] = []
    forecast = case["adapter"](stub_client(case["found"], seen=seen)).forecast(ALES)

    assert forecast == EXPECTED
    assert type(forecast) is Forecast
    assert seen[0].url.host == case["host"]


def test_location_is_sent_as_query(case, stub_client):
    seen: list[httpx.Request] = []
    case["adapter"](stub_client(case["found"], seen=seen)).forecast(ALES)

    assert {"44.125", "4.081"} <= set(seen[0].url.params.values())


def test_empty_response_gives_empty_forecast(case, stub_client):
    assert case["adapter"](stub_client(case["empty"])).forecast(ALES) == Forecast(times=[], temperatures=[])


def test_http_error_propagates(case, stub_client):
    with pytest.raises(httpx.HTTPStatusError):
        case["adapter"](stub_client(case["found"], status=500)).forecast(ALES)


def test_met_norway_sends_at_most_four_decimals(stub_client):
    seen: list[httpx.Request] = []
    MetNorwayForecaster(stub_client(CASES["met_norway"]["found"], seen=seen)).forecast(
        Location(latitude=44.1253665, longitude=4.0852818)
    )

    assert seen[0].url.params["lat"] == "44.1254"
    assert seen[0].url.params["lon"] == "4.0853"
