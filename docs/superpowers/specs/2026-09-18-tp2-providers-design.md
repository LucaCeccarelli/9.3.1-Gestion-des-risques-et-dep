# TP2 — Changement d'API : nouveaux fournisseurs et sélection par configuration

Date : 2026-09-18. Branche `TP2`, état de départ `ee9220c`. Source : `TP2.pdf` (un niveau au-dessus du dépôt).

## Exigences du TP

1. Nouvel adaptateur de géocodage **BAN** (`api-adresse.data.gouv.fr/search/?q=Alès&limit=1`) et nouvel adaptateur météo **MET Norway** (`api.met.no/weatherapi/locationforecast/2.0/compact?lat=44.12&lon=4.08`), derrière les abstractions existantes (`ports.Geocoder`, `ports.Forecaster`). MET Norway exige un `User-Agent` identifiant avec un contact (sinon 403).
2. Choix du fournisseur configurable sans recompilation ; les deux anciens fournisseurs restent disponibles.
3. Une suite de tests de contrat unique, exécutée contre chaque implémentation d'une même abstraction, avec bouchon HTTP : adresse valide, adresse introuvable, réponse vide, caractères accentués.
4. Les objets propres à chaque API (DTO, noms de champs, formats) ne sortent pas de leur adaptateur.

Mesure principale : le coût du changement. Objectif : `ports.py`, `services.py`, `models.py`, `main.py` inchangés.

## Adaptateurs

- `meteo/adapters/ban.py` — `BanGeocoder(Geocoder)`, `BAN_URL = "https://api-adresse.data.gouv.fr/search/"`. GET avec `q=<adresse>`, `limit=1`. `raise_for_status()`. `features = response.json().get("features") or []` ; vide → `AddressNotFound(address)`. Sinon `longitude, latitude = features[0]["geometry"]["coordinates"]` (GeoJSON : lon d'abord) → `Location(latitude=…, longitude=…)`.
- `meteo/adapters/met_norway.py` — `MetNorwayForecaster(Forecaster)`, `MET_NORWAY_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"`. GET avec `lat`, `lon`. `raise_for_status()`. `series = response.json().get("properties", {}).get("timeseries") or []` → `Forecast(times=[e["time"]…], temperatures=[e["data"]["instant"]["details"]["air_temperature"]…])`.
- `meteo/adapters/open_meteo.py` — une ligne : `hourly = response.json().get("hourly") or {}` puis `hourly.get("time", [])` / `hourly.get("temperature_2m", [])`, pour que la réponse vide donne un `Forecast` vide.
- `meteo/adapters/nominatim.py` — inchangé (`{}`/`[]` sont déjà traités comme « introuvable »).

Sémantique commune « réponse vide » (`{}`) : géocodeur → `AddressNotFound` ; forecaster → `Forecast(times=[], temperatures=[])`.

## Configuration (conteneur)

`meteo/container.py` :

```python
class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    config.geocoder.from_env("METEO_GEOCODER", default="nominatim")
    config.forecaster.from_env("METEO_FORECASTER", default="open_meteo")
    config.user_agent.from_env("METEO_USER_AGENT", default="TP2-MeteoApi/1.0 luca.ceccarelli@etu.mines-ales.fr")

    http_client = providers.ThreadSafeSingleton(
        httpx.Client, timeout=10, headers=providers.Dict({"User-Agent": config.user_agent})
    )
    geocoder = providers.Selector(
        config.geocoder,
        nominatim=providers.Factory(NominatimGeocoder, client=http_client),
        ban=providers.Factory(BanGeocoder, client=http_client),
    )
    forecaster = providers.Selector(
        config.forecaster,
        open_meteo=providers.Factory(OpenMeteoForecaster, client=http_client),
        met_norway=providers.Factory(MetNorwayForecaster, client=http_client),
    )
    weather_service = providers.Factory(WeatherService, geocoder=geocoder, forecaster=forecaster)
```

Variables d'environnement : `METEO_GEOCODER` ∈ {`nominatim`, `ban`} (défaut `nominatim`), `METEO_FORECASTER` ∈ {`open_meteo`, `met_norway`} (défaut `open_meteo`), `METEO_USER_AGENT` (défaut ci-dessus). Valeur inconnue → erreur `Selector` au premier appel. Les valeurs sont lues à l'import du conteneur (démarrage du processus).

`compose.yaml` laisse passer les trois variables (`environment: [METEO_GEOCODER, METEO_FORECASTER, METEO_USER_AGENT]`) : changer de fournisseur = relancer `docker compose up -d` avec l'env voulu, sans rebuild.

## Tests

- `tests/conftest.py` gagne une fixture `stub_client` : `stub_client(payload, status=200, seen=None) -> httpx.Client` (MockTransport, enregistre les requêtes dans `seen`).
- `tests/test_geocoder_contract.py` : dictionnaire `CASES` (`nominatim`, `ban`) avec `adapter`, `host`, payloads `found` (Alès → 44.125 / 4.081), `not_found`, `empty` ; fixture paramétrée `case`. Tests : est un `Geocoder` ; adresse valide → `Location` exacte et `type(...) is Location`, hôte attendu ; introuvable → `AddressNotFound` ; réponse vide → `AddressNotFound` ; `q == "Alès"` transmis intact ; 503 → `httpx.HTTPStatusError`.
- `tests/test_forecaster_contract.py` : `CASES` (`open_meteo`, `met_norway`) avec `adapter`, `host`, `found`, `empty`. Tests : est un `Forecaster` ; payload valide → `Forecast` attendu (2 heures) et `type(...) is Forecast`, hôte ; lat/lon présents dans les paramètres ; réponse vide → `Forecast` vide ; 500 → `HTTPStatusError`.
- `tests/test_adapters.py` supprimé (couvert par les contrats).
- `tests/test_container.py` : sélection `ban` + `met_norway` via `container.config.from_dict(...)` ; anciens fournisseurs toujours disponibles ; `User-Agent` issu de la config.
- `tests/test_boundaries.py` : hors `meteo/adapters/`, seul `container.py` importe `meteo.adapters` ; aucun nom de champ propre à une API (`features`, `geometry`, `timeseries`, `air_temperature`, `hourly`, `temperature_2m`, `display_name`, `"lat"`, `"lon"`) n'apparaît hors `meteo/adapters/`.
- `tests/test_api.py` : le test User-Agent attend le nouveau défaut. Le test de composition root (défauts Nominatim + Open-Meteo) reste.
- e2e : inchangés ; exécutés deux fois contre le conteneur, avec les défauts puis avec `METEO_GEOCODER=ban METEO_FORECASTER=met_norway`.

La suite hermétique suppose qu'aucune variable `METEO_*` n'est définie dans le shell.

## Docs

README : section « Fournisseurs » (tableau des variables, exemple de bascule sans rebuild) ; arborescence mise à jour. CLAUDE.md : variables, sélecteur, contrats, règle d'étanchéité.

## Hors périmètre

Fichier de configuration (l'env suffit), rechargement à chaud, validation des valeurs au démarrage, pagination BAN, autres champs météo.
