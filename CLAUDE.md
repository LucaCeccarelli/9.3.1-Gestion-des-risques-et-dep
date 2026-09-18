# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

TP1/TP2 school assignment: a FastAPI service where `GET /weather?address=<postal address>` geocodes the address (Nominatim or BAN), then fetches an hourly temperature forecast (Open-Meteo or MET Norway); the provider for each step is chosen by environment variable. The spec (`TP1.pdf`, one directory above the repo) grades on loose coupling, IoC and DI, plus unit and end-to-end tests. The implementation plan lives in `docs/superpowers/plans/` (untracked).

The code is deliberately minimal (ponytail discipline: stdlib/native first, no speculative abstractions, sync httpx, configuration limited to three `METEO_*` environment variables). Keep it that way; add only what a real need demands.

## Commands

Everything runs through `uv` from the repo root. The project has no `[build-system]` on purpose: it is not installed as a package, `pythonpath = ["."]` in pytest config and the working directory make `import meteo` work.

```bash
uv sync                                   # install (dev group included)
uv run fastapi dev meteo/main.py          # local dev server on :8000, docs at /docs
uv run pytest                             # hermetic suite: unit + API tests, no network
uv run pytest tests/test_api.py::test_unknown_address_is_404 -v   # single test
docker compose up -d --build --wait       # build image, start service `api` on :8000, block until healthy
uv run pytest -m e2e                      # Playwright e2e against the running container + real external services
docker compose down
curl -G --data-urlencode 'address=Alès' http://localhost:8000/weather   # accented addresses must be URL-encoded; raw UTF-8 gets 400 from uvicorn
METEO_GEOCODER=ban METEO_FORECASTER=met_norway docker compose up -d --wait   # switch providers, no rebuild
```

Test layering, controlled by `pyproject.toml`:
- `addopts = "-m 'not e2e'"` deselects the e2e tests by default; `-m e2e` on the CLI overrides it.
- `base_url = "http://localhost:8000"` is the pytest-base-url ini key the e2e tests read.
- The e2e tests use Playwright's `request` API (`playwright.request.new_context`), so no browser is needed. Do not run `playwright install`.
- Two pytest warnings are expected: deprecations from Starlette's TestClient and anyio, not project code.

## Architecture

Import direction, one way only: `models` ← `ports` ← `services` ← `adapters.*` ← `container` ← `main`. Only `main` imports FastAPI; only `container` and `main` import dependency-injector.

- `meteo/models.py`: Pydantic `Location`, `Forecast`, `WeatherReport` (nested response model).
- `meteo/ports.py`: `Geocoder` and `Forecaster` ABCs plus `AddressNotFound`. Adapters and test fakes inherit explicitly.
- `meteo/services.py`: `WeatherService.report(address) -> WeatherReport`, the only business flow.
- `meteo/adapters/`: one module per provider, each subclassing a port and taking an injected `httpx.Client`. Geocoders: `nominatim.py`, `ban.py` (BAN returns GeoJSON `[lon, lat]`). Forecasters: `open_meteo.py`, `met_norway.py`. Empty payload: geocoders raise `AddressNotFound`, forecasters return an empty `Forecast`. Provider field names never leave these modules (`tests/test_boundaries.py` enforces it).
- `meteo/container.py`: `Configuration` read from `METEO_GEOCODER` (`nominatim`|`ban`), `METEO_FORECASTER` (`open_meteo`|`met_norway`), `METEO_USER_AGENT` at import time; `http_client` is a `ThreadSafeSingleton` whose `User-Agent` comes from config (Nominatim and MET Norway both require an identifying one); `geocoder` and `forecaster` are `Selector`s over `Factory` providers. The hermetic suite assumes no `METEO_*` variable is set.
- `meteo/main.py`: app, two `exception_handler`s (`AddressNotFound` → 404 with the address in `detail`, `httpx.HTTPError` → 502), the `/weather` endpoint injected with `Depends(Provide[Container.weather_service])` under `@inject`, then `container.wire()` at the very end of the module. Wiring is explicit by choice; a `wiring_config` would also work provided `Container()` is instantiated after the endpoint definition.

Tests follow the same seams:
- `tests/conftest.py`: `FakeGeocoder` / `FakeForecaster` subclass the ABCs; fixtures `geocoder` / `forecaster`.
- `tests/test_geocoder_contract.py`, `tests/test_forecaster_contract.py`: one contract per port, parametrized over every implementation via a `CASES` dict (adapter class, host, stub payloads); add a new provider by adding a case.
- `tests/test_container.py`: provider selection via `container.config.from_dict(...)`. `tests/test_boundaries.py`: no adapter import and no provider field name outside `meteo/adapters/` (except `container.py` for wiring).
- `tests/test_api.py`: overrides `app.container.geocoder` / `forecaster` with `providers.Object(fake)` inside a `with` block, then `TestClient`.
- `tests/test_e2e.py`: Playwright request API against the compose container; the only tests marked `e2e`.

When adding a provider: one module in `adapters/` subclassing the port, one entry in the matching `Selector` in `container.py`, one `CASES` entry in the port's contract test. Unknown `METEO_*` values fail at the first request, not at startup. Changing the contract itself: model in `models.py`, port in `ports.py`, endpoint in `main.py`.

## Docker

`Dockerfile` copies `pyproject.toml` + `uv.lock` first and runs `uv sync --frozen --no-dev` before copying `meteo/`, then runs `.venv/bin/fastapi run meteo/main.py --port 8000` directly. `compose.yaml` has one service `api` whose healthcheck uses the image's own `python` against `/docs` (slim image has no curl), which is what makes `--wait` work. `.dockerignore` excludes `tests` and `docs`.

## Conventions

- Commit messages: conventional prefix (`feat:`, `fix:`, `build:`, `test:`, `docs:`), no Co-Authored-By trailer (the user removed them deliberately).
- README is in French; keep it that way.
