# TP1 — API Météo

`GET /weather?address=<adresse postale>` → géocodage Nominatim, puis prévisions horaires Open-Meteo.

## Lancer

Avec Docker :

```bash
docker compose up -d --build --wait
curl 'http://localhost:8000/weather?address=Alès'
docker compose down
```

En local :

```bash
uv sync
uv run fastapi dev meteo/main.py
```

Docs interactives : http://localhost:8000/docs

## Tester

```bash
uv run pytest                              # unitaires + API (services externes remplacés par des fakes)
docker compose up -d --build --wait
uv run pytest -m e2e                       # end-to-end Playwright contre le conteneur (réseau requis)
docker compose down
```

## Architecture

- `meteo/domain.py` — cœur sans dépendance : `Location`, `Forecast`, ports `Geocoder` / `Forecaster` (Protocols), `WeatherService` qui les enchaîne.
- `meteo/adapters.py` — implémentations HTTP des ports (`NominatimGeocoder`, `OpenMeteoForecaster`) ; le `httpx.Client` est injecté.
- `meteo/main.py` — composition root : FastAPI `Depends` fournit le client HTTP puis le `WeatherService`. Les tests API remplacent `get_weather_service` via `app.dependency_overrides`.
- `tests/test_e2e.py` — Playwright (`request` API, sans navigateur) contre le service lancé par `compose.yaml`.

Couplage faible / IoC / DI : le domaine ne connaît ni httpx ni FastAPI ; les adaptateurs ne se construisent pas eux-mêmes leur client ; seul `main.py` assemble.
