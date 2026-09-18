# Refonte IoC / DI, Pydantic et découpage des modules — design

Date : 2026-09-18. Périmètre : le dépôt `meteo` (TP1 API Météo), état de départ = commit `a6ea019` (six commits, suite verte : 12 tests hermétiques + 3 e2e Playwright).

## Motivation

Le correcteur note explicitement « couplage faible, Inversion de Contrôle (IoC) et Injection de Dépendances (DI) ». La version actuelle les réalise implicitement (Protocols structurels, `Depends` FastAPI mélangé au fichier de l'app, dataclasses sans schéma de réponse). On veut les rendre explicites et lisibles :

1. Un seul fichier contient l'app FastAPI et ses endpoints ; tout le code métier et le câblage vivent ailleurs.
2. L'IoC/DI passe par un conteneur déclaratif `dependency-injector`.
3. Les ports sont des classes abstraites (ABC) avec héritage explicite.
4. Pydantic modélise le domaine et le contrat de réponse.

Le comportement HTTP (GET `/weather?address=`, codes 200/404/422/502, User-Agent Nominatim, Docker, e2e Playwright) est conservé ; seule la forme du JSON de réponse change (imbriquée).

## Découpage des modules

```
meteo/
  __init__.py
  main.py            app FastAPI, endpoints, exception handlers, création du conteneur
  container.py       Container(DeclarativeContainer)
  models.py          Pydantic : Location, Forecast, WeatherReport
  ports.py           ABC Geocoder, ABC Forecaster, exception AddressNotFound
  services.py        WeatherService
  adapters/
    __init__.py
    nominatim.py     NominatimGeocoder(Geocoder)
    open_meteo.py    OpenMeteoForecaster(Forecaster)
```

Sens des dépendances (import) :

- `models` : pydantic seulement.
- `ports` : `models`.
- `services` : `ports`, `models`.
- `adapters.*` : httpx, `ports`, `models`.
- `container` : dependency-injector, httpx, `adapters`, `services`.
- `main` : fastapi, httpx (pour le type d'exception), dependency-injector (wiring), `container`, `models`, `ports`, `services`.

Aucun module autre que `main` n'importe FastAPI. Aucun module autre que `container` et `main` n'importe dependency-injector.

## Modèles (`meteo/models.py`)

```python
from pydantic import BaseModel


class Location(BaseModel):
    latitude: float
    longitude: float


class Forecast(BaseModel):
    times: list[str]
    temperatures: list[float]


class WeatherReport(BaseModel):
    address: str
    location: Location
    forecast: Forecast
```

Les modèles sont immuables par convention (pas de `frozen=True`, inutile ici). L'égalité Pydantic par valeur suffit aux assertions des tests.

## Ports (`meteo/ports.py`)

```python
from abc import ABC, abstractmethod

from meteo.models import Forecast, Location


class AddressNotFound(Exception):
    pass


class Geocoder(ABC):
    @abstractmethod
    def geocode(self, address: str) -> Location: ...


class Forecaster(ABC):
    @abstractmethod
    def forecast(self, location: Location) -> Forecast: ...
```

## Service (`meteo/services.py`)

```python
class WeatherService:
    def __init__(self, geocoder: Geocoder, forecaster: Forecaster) -> None: ...
    def report(self, address: str) -> WeatherReport:
        location = self.geocoder.geocode(address)
        return WeatherReport(address=address, location=location, forecast=self.forecaster.forecast(location))
```

Le service renvoie le `WeatherReport` complet ; l'endpoint le retourne tel quel.

## Adaptateurs (`meteo/adapters/`)

Comportement identique à aujourd'hui, avec héritage explicite :

- `NominatimGeocoder(Geocoder)`, constructeur `client: httpx.Client`. GET `https://nominatim.openstreetmap.org/search` avec `q`, `format=json`, `limit=1`. `raise_for_status()`. Liste vide → `AddressNotFound(address)`. Sinon `Location(latitude=float(lat), longitude=float(lon))` du premier résultat.
- `OpenMeteoForecaster(Forecaster)`, constructeur `client: httpx.Client`. GET `https://api.open-meteo.com/v1/forecast` avec `latitude`, `longitude`, `hourly=temperature_2m`. `raise_for_status()`. Renvoie `Forecast(times=hourly["time"], temperatures=hourly["temperature_2m"])`.

## Conteneur (`meteo/container.py`)

```python
import httpx
from dependency_injector import containers, providers

from meteo.adapters.nominatim import NominatimGeocoder
from meteo.adapters.open_meteo import OpenMeteoForecaster
from meteo.services import WeatherService


class Container(containers.DeclarativeContainer):
    http_client = providers.Singleton(httpx.Client, timeout=10, headers={"User-Agent": "meteo-tp1"})
    geocoder = providers.Factory(NominatimGeocoder, client=http_client)
    forecaster = providers.Factory(OpenMeteoForecaster, client=http_client)
    weather_service = providers.Factory(WeatherService, geocoder=geocoder, forecaster=forecaster)
```

- `http_client` est un singleton : une seule connexion pool, un seul User-Agent (exigence de la politique d'usage Nominatim).
- `geocoder`, `forecaster`, `weather_service` sont des `Factory` : objets légers, une instance par requête.
- Pas de `wiring_config` : `main.py` importe le conteneur, définit ses endpoints, puis appelle `container.wire(modules=[__name__])` en fin de module. Câblage explicite par choix de lisibilité ; un `wiring_config` fonctionnerait aussi à condition d'instancier `Container()` après la définition de l'endpoint.

## App (`meteo/main.py`)

```python
from typing import Annotated

import httpx
from dependency_injector.wiring import Provide, inject
from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse

from meteo.container import Container
from meteo.models import WeatherReport
from meteo.ports import AddressNotFound
from meteo.services import WeatherService

app = FastAPI(title="Météo", description="Adresse postale -> prévisions (Nominatim + Open-Meteo)")


@app.exception_handler(AddressNotFound)
def address_not_found(request: Request, exc: AddressNotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": f"Address not found: {exc}"})


@app.exception_handler(httpx.HTTPError)
def upstream_error(request: Request, exc: httpx.HTTPError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": f"Upstream service error: {exc}"})


@app.get("/weather", response_model=WeatherReport)
@inject
def weather(
    address: Annotated[str, Query(min_length=1, description="Adresse postale")],
    service: WeatherService = Depends(Provide[Container.weather_service]),
) -> WeatherReport:
    return service.report(address)


container = Container()
container.wire(modules=[__name__])
app.container = container
```

Note : `@inject` doit être la décoration la plus proche de la fonction (sous `@app.get`). `Depends(Provide[...])` est la forme d'intégration FastAPI documentée par dependency-injector ; avec `Annotated` elle ne fonctionne pas, d'où la valeur par défaut.

Contrat HTTP inchangé : 422 (adresse absente ou vide, FastAPI), 404 (`AddressNotFound`, `detail` contient l'adresse), 502 (`httpx.HTTPError`, y compris `HTTPStatusError` levé par `raise_for_status`). Le 200 renvoie le `WeatherReport` imbriqué :

```json
{"address": "Alès", "location": {"latitude": 44.12, "longitude": 4.08},
 "forecast": {"times": ["2026-09-18T00:00", "..."], "temperatures": [17.2, 0.0]}}
```

## Tests

Même pyramide, adaptée :

- `tests/conftest.py` : `FakeGeocoder(Geocoder)` (attributs `calls`, `error`) et `FakeForecaster(Forecaster)` (attribut `calls`) ; fixtures `geocoder`, `forecaster`. Comme les ABC ont des méthodes abstraites, les fakes doivent les implémenter, ce qui est vérifié à l'instanciation.
- `tests/test_services.py` : `WeatherService(geocoder, forecaster).report("Paris")` renvoie un `WeatherReport` attendu et enchaîne bien les deux ports.
- `tests/test_adapters.py` : inchangé dans l'esprit (MockTransport, hôte, paramètres, mapping, erreurs) ; imports mis à jour ; un test vérifie `isinstance(NominatimGeocoder(client), Geocoder)`.
- `tests/test_api.py` : fixture `client` qui fait `with app.container.geocoder.override(providers.Object(geocoder)), app.container.forecaster.override(providers.Object(forecaster)): yield TestClient(app)`. Cas : 200 (forme imbriquée, adresse propagée jusqu'au forecaster), 422 absent, 422 vide, 404 avec adresse dans `detail`, 502 sur `httpx.ConnectError`. Le test User-Agent devient `app.container.http_client().headers["user-agent"] == "meteo-tp1"`.
- `tests/test_e2e.py` : Playwright `request` inchangé ; assertions adaptées à `body["location"]["latitude"]`, `body["forecast"]["times"]`.

`uv run pytest` reste hermétique (aucun réseau) ; `-m e2e` reste opt-in.

## Dépendances, outillage, docs

- `pyproject.toml` : ajouter `dependency-injector>=4.41` aux dépendances. Pydantic est déjà transitif via FastAPI (pas d'ajout explicite, on importe `pydantic` fourni par `fastapi`). Ajouter `.python-version` = `3.12` pour aligner la venv locale et l'image Docker.
- Dockerfile / compose : inchangés (le lock est régénéré, `uv sync --frozen --no-dev` le consomme).
- README (français) : section Architecture réécrite pour décrire conteneur, ABC, Pydantic ; exemple de réponse imbriquée.
- `CLAUDE.md` : section Architecture mise à jour.

## Hors périmètre

Configuration par variables d'environnement (`providers.Configuration`), asynchrone, cache, retry, `raise ... from`, validation d'adresse blanche. À ajouter sur besoin réel.
