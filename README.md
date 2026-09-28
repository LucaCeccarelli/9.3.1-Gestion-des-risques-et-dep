# TP1 à TP4 — API Météo

`GET /weather?address=<adresse postale>[&demo=true]` → géocodage (Nominatim ou BAN, mis en cache), puis prévisions horaires (Open-Meteo ou MET Norway). Le fournisseur de chaque étape se choisit par variable d'environnement ; `demo=true` renvoie des données simulées sans aucun appel externe.

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
  "latitude": 44.125,
  "longitude": 4.085,
  "hourly": [
    {"time": "2026-09-18T00:00:00Z", "temperatureCelsius": 17.2}
  ]
}
```

Même forme, mêmes noms de champs quel que soit le fournisseur ou le mode démo (vérifié par tests/test_format.py) ; seul le contenu change. Les heures sont en UTC.

Codes : `422` adresse absente ou vide, ou `demo` non booléen, `404` adresse inconnue, `502` service externe en erreur.

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

## Mode démo et cache (TP3)

```bash
curl -G --data-urlencode 'address=Alès' -d demo=true http://localhost:8000/weather
```

- **Mode démo** : `demo=true` sert `DemoGeocoder` et `DemoForecaster` (`meteo/adapters/demo.py`), deux implémentations des ports existants. Aucun appel réseau : `tests/test_format.py` le prouve avec un client HTTP qui échoue à la moindre requête.
- **Cache de géocodage** : `CachedGeocoder` (`meteo/cache.py`) enveloppe le géocodeur actif ; deux appels pour la même adresse ne font qu'un appel réseau. Le stockage est un `MutableMapping` injecté par le conteneur (`geocoding_cache`, un singleton du conteneur, pas une variable statique). Pour le faire évoluer (TTL, LRU, Redis…), seul ce provider change. Les échecs (adresse inconnue, erreur HTTP) ne sont pas mis en cache.

## Licences (TP4)

Audit complet (scan brut, classification, fiches de décision, CI) : [`docs/audit-licences.md`](docs/audit-licences.md). Scan brut : [`licenses.md`](licenses.md).

La CI (`.github/workflows/licences.yml`) échoue si une dépendance, directe ou transitive, dev comprise, porte une licence absente de la liste blanche. Seule exception : `text-unidecode:1.3`, épinglée à cette version et justifiée dans l'audit. Pour régénérer le scan :

```bash
uvx pip-licenses@5.5.5 --python .venv/bin/python --from=mixed --format=markdown --output-file licenses.md
```

## Architecture

```
meteo/
  main.py            app FastAPI : endpoints, handlers d'erreurs, câblage du conteneur
  container.py       conteneur dependency-injector : configuration + sélection des fournisseurs
  models.py          modèles Pydantic : Location, Forecast, WeatherReport (domaine) ; ForecastResponse (contrat JSON)
  ports.py           ports abstraits (ABC) : Geocoder, Forecaster ; AddressNotFound
  services.py        WeatherService : geocode → forecast → WeatherReport
  cache.py           CachedGeocoder(Geocoder) : cache injecté devant le géocodeur actif
  adapters/
    nominatim.py     NominatimGeocoder(Geocoder)
    ban.py           BanGeocoder(Geocoder)              — Base Adresse Nationale
    open_meteo.py    OpenMeteoForecaster(Forecaster)
    met_norway.py    MetNorwayForecaster(Forecaster)    — MET Norway Locationforecast
    demo.py          DemoGeocoder(Geocoder), DemoForecaster(Forecaster) — données simulées
```

- **Couplage faible** : `services.py` ne connaît que les ports abstraits de `ports.py`. Les adaptateurs HTTP en héritent explicitement et reçoivent leur `httpx.Client` par constructeur. Seul `main.py` importe FastAPI.
- **Inversion de contrôle** : aucun module ne construit ses dépendances. `container.py` déclare le graphe (`ThreadSafeSingleton` pour le client HTTP avec le `User-Agent` exigé par Nominatim et MET Norway, `Factory` pour les adaptateurs et le service) ; `main.py` le câble en fin de module.
- **Injection de dépendances** : l'endpoint reçoit les deux providers `WeatherService` via `Depends(Provide[Container.weather_service.provider])` et `Depends(Provide[Container.demo_weather_service.provider])`, et n'appelle que celui choisi par `demo`. Les tests API remplacent `geocoder` et `forecaster` par des fakes avec `app.container.<provider>.override(...)`, sans réseau.
- **Pydantic** : `ForecastResponse` est le `response_model` de l'endpoint ; le schéma apparaît dans `/docs`.
- **Coût du changement (TP2)** : ajouter BAN et MET Norway n'a touché ni `ports.py`, ni `services.py`, ni `models.py`, ni `main.py` : deux fichiers d'adaptateur, deux `Selector` dans le conteneur, et deux lignes dans l'adaptateur Open-Meteo révélées par la suite de contrat (réponse vide).

### Patterns (Partie 6 : Découpler ses dépendances)

| Pattern | Où | Problème résolu |
|---|---|---|
| Boundary / seam | `ports.py` | le métier ne connaît que `Geocoder` / `Forecaster` ; les tests y glissent des fakes |
| Adapter | `adapters/*.py`, `ForecastResponse.from_report` | chaque API externe → modèle interne ; modèle interne → contrat JSON public |
| Facade | `WeatherService.report` | orchestre géocodage puis prévisions derrière une seule méthode |
| Strategy | `DemoGeocoder` / `DemoForecaster` vs adaptateurs réels, choisis par `demo` à chaque requête | changer de comportement sans changer l'appelant |
| Factory | `container.py` (`Factory`, `Selector`) | création centralisée, dépendante du contexte (variables d'environnement), injectée par la DI |

**Coût du changement (TP3)** : `ports.py`, `services.py` et les quatre adaptateurs existants n'ont pas bougé. Ajouts : `cache.py`, `adapters/demo.py`, `ForecastResponse` dans `models.py`, trois providers dans le conteneur, un paramètre `demo` dans l'endpoint.
