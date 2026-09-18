# TP1 — API Météo

`GET /weather?address=<adresse postale>` → géocodage Nominatim, puis prévisions horaires Open-Meteo.

## Lancer

Avec Docker :

```bash
docker compose up -d --build --wait
curl -G --data-urlencode 'address=Alès' http://localhost:8000/weather
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

## Réponse

```json
{
  "address": "Alès",
  "location": {"latitude": 44.125, "longitude": 4.085},
  "forecast": {"times": ["2026-09-18T00:00", "..."], "temperatures": [17.2, 16.8]}
}
```

Codes : `422` adresse absente ou vide, `404` adresse inconnue, `502` service externe en erreur.

## Architecture

```
meteo/
  main.py            app FastAPI : endpoints, handlers d'erreurs, câblage du conteneur
  container.py       conteneur dependency-injector (composition root)
  models.py          modèles Pydantic : Location, Forecast, WeatherReport
  ports.py           ports abstraits (ABC) : Geocoder, Forecaster ; AddressNotFound
  services.py        WeatherService : geocode → forecast → WeatherReport
  adapters/
    nominatim.py     NominatimGeocoder(Geocoder)
    open_meteo.py    OpenMeteoForecaster(Forecaster)
```

- **Couplage faible** : `services.py` ne connaît que les ports abstraits de `ports.py`. Les adaptateurs HTTP en héritent explicitement et reçoivent leur `httpx.Client` par constructeur. Seul `main.py` importe FastAPI.
- **Inversion de contrôle** : aucun module ne construit ses dépendances. `container.py` déclare le graphe (`Singleton` pour le client HTTP avec le `User-Agent` exigé par Nominatim, `Factory` pour les adaptateurs et le service) ; `main.py` le câble en fin de module.
- **Injection de dépendances** : l'endpoint reçoit `WeatherService` via `Depends(Provide[Container.weather_service])`. Les tests API remplacent `geocoder` et `forecaster` par des fakes avec `app.container.<provider>.override(...)`, sans réseau.
- **Pydantic** : `WeatherReport` est le `response_model` de l'endpoint ; le schéma apparaît dans `/docs`.
