import httpx
import pytest

from meteo.adapters.ban import BanGeocoder
from meteo.adapters.nominatim import NominatimGeocoder
from meteo.models import Location
from meteo.ports import AddressNotFound, Geocoder

ALES = Location(latitude=44.125, longitude=4.081)

CASES = {
    "nominatim": dict(
        adapter=NominatimGeocoder,
        host="nominatim.openstreetmap.org",
        found=[{"lat": "44.125", "lon": "4.081", "display_name": "Alès, Gard, France"}],
        not_found=[],
        empty={},
    ),
    "ban": dict(
        adapter=BanGeocoder,
        host="api-adresse.data.gouv.fr",
        found={
            "type": "FeatureCollection",
            "features": [{"geometry": {"type": "Point", "coordinates": [4.081, 44.125]}, "properties": {"label": "Alès"}}],
        },
        not_found={"type": "FeatureCollection", "features": []},
        empty={},
    ),
}


@pytest.fixture(params=list(CASES), ids=list(CASES))
def case(request):
    return CASES[request.param]


def test_is_a_geocoder(case, stub_client):
    assert isinstance(case["adapter"](stub_client(case["found"])), Geocoder)


def test_valid_address_gives_a_location(case, stub_client):
    seen: list[httpx.Request] = []
    location = case["adapter"](stub_client(case["found"], seen=seen)).geocode("Alès")

    assert location == ALES
    assert type(location) is Location
    assert seen[0].url.host == case["host"]


def test_unknown_address_raises(case, stub_client):
    with pytest.raises(AddressNotFound):
        case["adapter"](stub_client(case["not_found"])).geocode("zzqqxx nowhere 00000")


def test_empty_response_raises(case, stub_client):
    with pytest.raises(AddressNotFound):
        case["adapter"](stub_client(case["empty"])).geocode("Alès")


def test_accented_address_is_sent_intact(case, stub_client):
    seen: list[httpx.Request] = []
    case["adapter"](stub_client(case["found"], seen=seen)).geocode("Alès")

    assert seen[0].url.params["q"] == "Alès"


def test_http_error_propagates(case, stub_client):
    with pytest.raises(httpx.HTTPStatusError):
        case["adapter"](stub_client(case["found"], status=503)).geocode("Alès")
