"""Regresión del issue #12: el manejo de errores pierde información y todo colapsa a 500.

Verifica que **todos** los caminos de error de la API se rindan con el mismo
envelope ``ErrorResponse`` ({status, message}) y con el código HTTP correcto:

- Una ``HTTPException`` de validación (400) usa el envelope uniforme, no el
  ``{"detail": ...}`` por defecto de FastAPI.
- Un ``ExternalSourceError`` tipado se traduce a su código semántico (408
  timeout / 502 fuente caída) e incluye el nombre de la fuente en el mensaje.
- Una excepción no controlada colapsa a un 500 uniforme con mensaje genérico,
  **sin filtrar** el detalle interno (``str(exc)``) al cliente.
"""
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.controller import dollar_controller
from api.core.errors.exceptions import SourceTimeoutError, SourceUnavailableError
from api.utils.constants.constants import Constants as c


client = TestClient(app, raise_server_exceptions=False)


def _assert_error_envelope(body):
    """El cuerpo de error debe ser el envelope uniforme, no el `{detail}` de FastAPI."""
    assert set(body.keys()) == {"status", "message"}
    assert body["status"] == c.STATUS_ERROR_MSG
    assert isinstance(body["message"], str) and body["message"]
    assert "detail" not in body


def test_400_usa_envelope_uniforme():
    """La validación de 'ninguna fuente seleccionada' (400) usa el envelope uniforme."""
    response = client.put(
        f"{c.API_V1_STR}/venezuela/update-currencies",
        params={"bcv": False, "yadio": False, "binance": False, "bybit": False, "okx": False, "bitget": False, "airtm": False, "dolarapi": False, "exchange_monitor": False},
    )
    assert response.status_code == 400
    _assert_error_envelope(response.json())


def test_source_timeout_se_traduce_a_408(monkeypatch):
    """Un SourceTimeoutError se rinde como 408 con la fuente en el mensaje."""
    monkeypatch.setattr(
        dollar_controller.dollar_service,
        "getCurrenciesByBCV",
        AsyncMock(side_effect=SourceTimeoutError(c.BCV_NAME)),
    )
    response = client.get(f"{c.API_V1_STR}/venezuela/bcv")
    assert response.status_code == 408
    body = response.json()
    _assert_error_envelope(body)
    assert c.BCV_NAME in body["message"]


def test_source_unavailable_se_traduce_a_502(monkeypatch):
    """Un SourceUnavailableError se rinde como 502 con la fuente en el mensaje."""
    monkeypatch.setattr(
        dollar_controller.dollar_service,
        "getCurrenciesByYadio",
        AsyncMock(side_effect=SourceUnavailableError(c.YADIO_NAME, detail="connection refused")),
    )
    response = client.get(f"{c.API_V1_STR}/venezuela/yadio")
    assert response.status_code == 502
    body = response.json()
    _assert_error_envelope(body)
    assert c.YADIO_NAME in body["message"]


def test_excepcion_no_controlada_devuelve_500_generico(monkeypatch):
    """Una excepción inesperada colapsa a 500 uniforme sin filtrar el detalle interno."""
    secret = "internal-boom-do-not-leak"
    monkeypatch.setattr(
        dollar_controller.dollar_service,
        "getCurrenciesByBCV",
        AsyncMock(side_effect=ValueError(secret)),
    )
    response = client.get(f"{c.API_V1_STR}/venezuela/bcv")
    assert response.status_code == 500
    body = response.json()
    _assert_error_envelope(body)
    assert body["message"] == c.INTERNAL_ERROR_MSG
    # No se debe filtrar el detalle interno de la excepción al cliente.
    assert secret not in response.text
