# TP1 / TP2 — API Météo

`GET /weather?address=<adresse postale>` → géocodage (Nominatim ou BAN), puis prévisions horaires (Open-Meteo ou MET Norway). Le fournisseur de chaque étape se choisit par variable d'environnement.

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

## Fournisseurs

Le fournisseur de chaque port se choisit par variable d'environnement, sans rebuild :

| Variable | Valeurs | Défaut |
|---|---|---|
| `METEO_GEOCODER` | `nominatim`, `ban` | `nominatim` |
| `METEO_FORECASTER` | `open_meteo`, `met_norway` | `open_meteo` |
| `METEO_USER_AGENT` | texte libre avec un contact (exigé par Nominatim et MET Norway) | `TP2-MeteoApi/1.0 luca.ceccarelli@etu.mines-ales.fr` |

Les variables peuvent aussi être posées dans un fichier `.env` à côté de `compose.yaml` (lu automatiquement par Docker Compose) : `cp .env.example .env` puis modifier les valeurs. Une valeur inconnue provoque une erreur à la première requête, pas au démarrage.

```bash
METEO_GEOCODER=ban METEO_FORECASTER=met_norway docker compose up -d --wait
uv run pytest -m e2e
```

Chaque port a une suite de contrat unique exécutée contre toutes ses implémentations (`tests/test_geocoder_contract.py`, `tests/test_forecaster_contract.py`) : adresse valide, introuvable, réponse vide, accents, erreur HTTP. `tests/test_boundaries.py` vérifie qu'aucun champ propre à une API ne sort de `meteo/adapters/`.

## Architecture

```
meteo/
  main.py            app FastAPI : endpoints, handlers d'erreurs, câblage du conteneur
  container.py       conteneur dependency-injector : configuration + sélection des fournisseurs
  models.py          modèles Pydantic : Location, Forecast, WeatherReport
  ports.py           ports abstraits (ABC) : Geocoder, Forecaster ; AddressNotFound
  services.py        WeatherService : geocode → forecast → WeatherReport
  adapters/
    nominatim.py     NominatimGeocoder(Geocoder)
    ban.py           BanGeocoder(Geocoder)              — Base Adresse Nationale
    open_meteo.py    OpenMeteoForecaster(Forecaster)
    met_norway.py    MetNorwayForecaster(Forecaster)    — MET Norway Locationforecast
```

- **Couplage faible** : `services.py` ne connaît que les ports abstraits de `ports.py`. Les adaptateurs HTTP en héritent explicitement et reçoivent leur `httpx.Client` par constructeur. Seul `main.py` importe FastAPI.
- **Inversion de contrôle** : aucun module ne construit ses dépendances. `container.py` déclare le graphe (`ThreadSafeSingleton` pour le client HTTP avec le `User-Agent` exigé par Nominatim et MET Norway, `Factory` pour les adaptateurs et le service) ; `main.py` le câble en fin de module.
- **Injection de dépendances** : l'endpoint reçoit `WeatherService` via `Depends(Provide[Container.weather_service])`. Les tests API remplacent `geocoder` et `forecaster` par des fakes avec `app.container.<provider>.override(...)`, sans réseau.
- **Pydantic** : `WeatherReport` est le `response_model` de l'endpoint ; le schéma apparaît dans `/docs`.
- **Coût du changement (TP2)** : ajouter BAN et MET Norway n'a touché ni `ports.py`, ni `services.py`, ni `models.py`, ni `main.py` : deux fichiers d'adaptateur, deux `Selector` dans le conteneur, et deux lignes dans l'adaptateur Open-Meteo révélées par la suite de contrat (réponse vide).
