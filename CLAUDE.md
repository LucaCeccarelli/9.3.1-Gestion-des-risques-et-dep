# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

TP1 school assignment: a FastAPI service where `GET /weather?address=<postal address>` geocodes the address with Nominatim, then fetches an hourly `temperature_2m` forecast from Open-Meteo. The spec (`/home/luca/git/9-3-Dep/TP1.pdf`, outside the repo) grades on loose coupling, IoC and DI, plus unit and end-to-end tests. The implementation plan lives in `docs/superpowers/plans/` (untracked).

The code is deliberately minimal (ponytail discipline: stdlib/native first, no speculative abstractions, sync httpx, no settings/env config). Keep it that way; add only what a real need demands.

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
- `meteo/adapters/nominatim.py`, `meteo/adapters/open_meteo.py`: HTTP implementations over an injected `httpx.Client`. Empty Nominatim result raises `AddressNotFound`; non-2xx raises `httpx.HTTPStatusError`.
- `meteo/container.py`: `dependency_injector` `DeclarativeContainer`. `http_client` is a `Singleton` carrying `User-Agent: meteo-tp1` (Nominatim policy) and a 10 s timeout; `geocoder`, `forecaster`, `weather_service` are `Factory`.
- `meteo/main.py`: app, two `exception_handler`s (`AddressNotFound` → 404 with the address in `detail`, `httpx.HTTPError` → 502), the `/weather` endpoint injected with `Depends(Provide[Container.weather_service])` under `@inject`, then `container.wire()` at the very end of the module. The wiring must stay after the endpoint definition, which is why the container has no `wiring_config`.

Tests follow the same seams:
- `tests/conftest.py`: `FakeGeocoder` / `FakeForecaster` subclass the ABCs; fixtures `geocoder` / `forecaster`.
- `tests/test_adapters.py`: `httpx.MockTransport`, asserts host and query params.
- `tests/test_api.py`: overrides `app.container.geocoder` / `forecaster` with `providers.Object(fake)` inside a `with` block, then `TestClient`.
- `tests/test_e2e.py`: Playwright request API against the compose container; the only tests marked `e2e`.

When adding a provider or changing the contract: model in `models.py`, port in `ports.py`, HTTP implementation in `adapters/`, provider in `container.py`, endpoint in `main.py`.

## Docker

`Dockerfile` copies `pyproject.toml` + `uv.lock` first and runs `uv sync --frozen --no-dev` before copying `meteo/`, then runs `.venv/bin/fastapi run meteo/main.py --port 8000` directly. `compose.yaml` has one service `api` whose healthcheck uses the image's own `python` against `/docs` (slim image has no curl), which is what makes `--wait` work. `.dockerignore` excludes `tests` and `docs`.

## Conventions

- Commit messages: conventional prefix (`feat:`, `fix:`, `build:`, `test:`, `docs:`), no Co-Authored-By trailer (the user removed them deliberately).
- README is in French; keep it that way.
