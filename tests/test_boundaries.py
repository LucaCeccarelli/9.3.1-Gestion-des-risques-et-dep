from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent / "meteo"
PROVIDER_FIELDS = (
    "features",
    "geometry",
    "timeseries",
    "air_temperature",
    "hourly",
    "temperature_2m",
    "display_name",
    '"lat"',
    '"lon"',
)


def modules_outside_adapters() -> list[Path]:
    return [path for path in PACKAGE.rglob("*.py") if "adapters" not in path.parts]


def test_only_the_container_imports_adapters():
    for module in modules_outside_adapters():
        if module.name != "container.py":
            assert "meteo.adapters" not in module.read_text(), module.name


def test_provider_fields_stay_inside_adapters():
    for module in modules_outside_adapters():
        source = module.read_text()
        for field in PROVIDER_FIELDS:
            assert field not in source, f"{field} leaks into {module.name}"
