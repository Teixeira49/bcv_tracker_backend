"""Issue #18: el ``response_model`` declarado debe aplicarse a la respuesta real.

Antes, ``api_response`` devolvía un ``JSONResponse`` crudo. Cuando un endpoint
retorna un ``Response`` directamente, FastAPI **no valida ni serializa** contra
el ``response_model`` del decorador: el schema quedaba solo como documentación y
la salida real no estaba garantizada (drift doc-vs-realidad).

El fix hace que ``api_response`` devuelva el **envelope como dict**, de modo que
FastAPI aplica el ``response_model=BaseResponse[T]`` (lo valida, serializa y
filtra). Estos tests son el **guardrail** que impide reintroducir el drift:

- ``api_response`` devuelve un dict plano, no un ``Response`` (si alguien vuelve
  a envolver en ``JSONResponse``, este test falla).
- Toda ruta de negocio declara ``response_model`` (el contrato existe en OpenAPI).
- FastAPI realmente **filtra** los campos ajenos al schema en la salida.
- Un payload que **no** cumple el schema ahora **falla** (se detecta el drift) en
  vez de devolverse silenciosamente con forma incorrecta.
"""
from unittest.mock import AsyncMock

from fastapi.responses import Response
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from api.main import app
from api.controller import venezuela_controller
from api.core.response.response_wrapper import api_response
from api.utils.constants.constants import Constants as c


client = TestClient(app, raise_server_exceptions=False)

YADIO = f"{c.API_V1_STR}/venezuela/yadio"


def test_api_response_returns_plain_dict_not_response():
    """``api_response`` debe devolver un dict (no un ``Response``).

    Es lo que permite a FastAPI aplicar el ``response_model``. Si se revirtiera a
    ``JSONResponse``, FastAPI omitiría la validación y volvería el drift.
    """
    result = api_response({"foo": "bar"})
    assert isinstance(result, dict)
    assert not isinstance(result, Response)
    assert result["status"] == c.STATUS_OK_MSG
    assert result["data"] == {"foo": "bar"}


def test_api_response_omits_data_when_none():
    """La clave ``data`` se omite cuando no se provee payload."""
    result = api_response()
    assert "data" not in result
    assert set(result.keys()) == {"status", "message"}


def test_all_business_routes_declare_response_model():
    """Cada ruta del router de Venezuela declara un ``response_model``.

    Garantiza que el contrato documentado en OpenAPI existe para toda operación
    (base del guardrail: sin ``response_model`` no hay nada que FastAPI enforce).
    """
    routes = [r for r in venezuela_controller.router.routes if isinstance(r, APIRoute)]
    assert routes, "el router de Venezuela no expone rutas"
    sin_modelo = [f"{sorted(r.methods)} {r.path}" for r in routes if r.response_model is None]
    assert not sin_modelo, f"rutas sin response_model: {sin_modelo}"


def test_response_model_filters_extra_fields(monkeypatch):
    """FastAPI filtra los campos ajenos al schema declarado.

    Prueba de extremo a extremo de que el ``response_model`` se aplica: un campo
    que no pertenece a ``CurrencySchema`` no debe aparecer en la salida real.
    """
    monkeypatch.setattr(
        venezuela_controller.dollar_service, "getCurrenciesByYadio",
        AsyncMock(return_value=[{
            "code": "USD", "name": "Dolar", "platform": c.YADIO_NAME,
            "value": 100.0, "change": 0.0,
            "campo_intruso": "debería_filtrarse",
        }]),
    )

    r = client.get(YADIO)

    assert r.status_code == 200
    item = r.json()["data"][0]
    assert "campo_intruso" not in item        # filtrado por response_model
    assert item["code"] == "USD"
    assert "id" in item                        # campo del schema presente (None)


def test_response_model_rejects_shape_drift(monkeypatch):
    """Un payload que no cumple el schema ahora falla (no se devuelve como 200).

    ``CurrencySchema`` exige ``code``, ``name``, ``platform``, ``value`` y
    ``change``. Un item incompleto provoca un error de validación de respuesta,
    de modo que el drift se detecta en vez de servirse silenciosamente.
    """
    monkeypatch.setattr(
        venezuela_controller.dollar_service, "getCurrenciesByYadio",
        AsyncMock(return_value=[{"code": "USD"}]),  # faltan campos requeridos
    )

    r = client.get(YADIO)

    assert r.status_code != 200
    assert r.status_code >= 500
