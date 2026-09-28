import httpx
import pytest

pytestmark = pytest.mark.e2e

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def api():
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        yield client


def test_weather_for_a_real_address(api):
    response = api.get("/weather", params={"address": "Alès"})

    assert response.is_success, response.text
    body = response.json()
    assert body["address"] == "Alès"
    assert 44 < body["latitude"] < 45
    assert 3 < body["longitude"] < 5
    assert body["hourly"]
    assert set(body["hourly"][0]) == {"time", "temperatureCelsius"}
    assert body["hourly"][0]["time"].endswith("Z")


def test_demo_mode_has_the_same_shape_as_real_data(api):
    real = api.get("/weather", params={"address": "Alès"}).json()
    demo = api.get("/weather", params={"address": "Alès", "demo": "true"}).json()

    assert set(demo) == set(real) == {"address", "latitude", "longitude", "hourly"}
    assert set(demo["hourly"][0]) == set(real["hourly"][0])


def test_unknown_address_is_404(api):
    response = api.get("/weather", params={"address": "zzqqxx nowhere 00000 zzqqxx"})

    assert response.status_code == 404
    assert "zzqqxx" in response.json()["detail"]


def test_missing_address_is_422(api):
    assert api.get("/weather").status_code == 422
