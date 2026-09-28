from collections.abc import Callable
from typing import Annotated

import httpx
from dependency_injector.wiring import Provide, inject
from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse

from meteo.container import Container
from meteo.models import ForecastResponse
from meteo.ports import AddressNotFound
from meteo.services import WeatherService

app = FastAPI(title="Meteo")


@app.exception_handler(AddressNotFound)
def address_not_found(request: Request, exc: AddressNotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": f"Address not found: {exc}"})


@app.exception_handler(httpx.HTTPError)
def upstream_error(request: Request, exc: httpx.HTTPError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": f"Upstream service error: {exc}"})


@app.get("/weather", response_model=ForecastResponse)
@inject
def weather(
    address: Annotated[str, Query(min_length=1, description="Adresse postale")],
    demo: Annotated[bool, Query(description="Données simulées, aucun appel externe")] = False,
    service: Callable[[], WeatherService] = Depends(Provide[Container.weather_service.provider]),
    demo_service: Callable[[], WeatherService] = Depends(Provide[Container.demo_weather_service.provider]),
) -> ForecastResponse:
    return ForecastResponse.from_report((demo_service if demo else service)().report(address))


# Câblage explicite en fin de module : l'endpoint doit exister avant que le conteneur l'injecte.
container = Container()
container.wire(modules=[__name__])
app.container = container
