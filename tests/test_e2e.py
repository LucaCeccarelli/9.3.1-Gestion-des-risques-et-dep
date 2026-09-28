"""End-to-end: Playwright's request API against the running container (docker compose up -d --wait).

No browser is involved: `playwright.request` drives HTTP directly, so `playwright install` is not needed.
"""

import pytest
from playwright.sync_api import APIRequestContext, Playwright

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def api(playwright: Playwright, base_url: str) -> APIRequestContext:
    context = playwright.request.new_context(base_url=base_url)
    yield context
    context.dispose()


def test_weather_for_a_real_address(api):
    response = api.get("/weather", params={"address": "Alès"})

    assert response.ok, response.text()
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

    assert response.status == 404
    assert "zzqqxx" in response.json()["detail"]


def test_missing_address_is_422(api):
    assert api.get("/weather").status == 422
