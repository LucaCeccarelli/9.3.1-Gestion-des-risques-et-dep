from contextlib import contextmanager

import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient
from test_forecaster_contract import CASES as FORECASTERS
from test_geocoder_contract import CASES as GEOCODERS

from meteo.main import app
from meteo.ports import Forecaster, Geocoder

EXPECTED = {
    "address": "Alès",
    "latitude": 44.125,
    "longitude": 4.081,
    "hourly": [
        {"time": "2026-09-18T00:00:00Z", "temperatureCelsius": 17.2},
        {"time": "2026-09-18T01:00:00Z", "temperatureCelsius": 16.8},
    ],
}


@contextmanager
def serving(geocoder: Geocoder, forecaster: Forecaster):
    with (
        app.container.geocoder.override(providers.Object(geocoder)),
        app.container.forecaster.override(providers.Object(forecaster)),
        app.container.geocoding_cache.override(providers.Object({})),
    ):
        yield TestClient(app)


@pytest.mark.parametrize("forecaster", list(FORECASTERS))
@pytest.mark.parametrize("geocoder", list(GEOCODERS))
def test_every_provider_combination_gives_the_same_json(geocoder, forecaster, stub_client):
    g, f = GEOCODERS[geocoder], FORECASTERS[forecaster]
    with serving(g["adapter"](stub_client(g["found"])), f["adapter"](stub_client(f["found"]))) as client:
        response = client.get("/weather", params={"address": "Alès"})

    assert response.status_code == 200
    assert response.json() == EXPECTED


def test_empty_forecast_keeps_the_shape(stub_client):
    g, f = GEOCODERS["ban"], FORECASTERS["met_norway"]
    with serving(g["adapter"](stub_client(g["found"])), f["adapter"](stub_client(f["empty"]))) as client:
        response = client.get("/weather", params={"address": "Alès"})

    assert response.json() == {**EXPECTED, "hourly": []}
