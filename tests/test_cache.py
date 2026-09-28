import pytest

from meteo.cache import CachedGeocoder
from meteo.models import Location
from meteo.ports import AddressNotFound, Geocoder

PARIS = Location(latitude=48.85, longitude=2.35)
ALES = Location(latitude=44.125, longitude=4.081)


def test_is_a_geocoder(geocoder):
    assert isinstance(CachedGeocoder(geocoder, {}), Geocoder)


def test_same_address_reaches_the_real_geocoder_once(geocoder):
    cached = CachedGeocoder(geocoder, {})

    assert cached.geocode("Paris") == cached.geocode("Paris") == PARIS
    assert geocoder.calls == ["Paris"]


def test_different_addresses_are_geocoded_separately(geocoder):
    cached = CachedGeocoder(geocoder, {})
    cached.geocode("Paris")
    cached.geocode("Alès")

    assert geocoder.calls == ["Paris", "Alès"]


def test_failures_are_not_cached(geocoder):
    cached = CachedGeocoder(geocoder, {})
    geocoder.error = AddressNotFound("Paris")
    with pytest.raises(AddressNotFound):
        cached.geocode("Paris")

    geocoder.error = None
    assert cached.geocode("Paris") == PARIS
    assert geocoder.calls == ["Paris", "Paris"]


def test_storage_is_injected(geocoder):
    store = {"Alès": ALES}
    cached = CachedGeocoder(geocoder, store)

    assert cached.geocode("Alès") == ALES
    assert geocoder.calls == []
    cached.geocode("Paris")
    assert store["Paris"] == PARIS
