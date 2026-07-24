"""Issue #68: filtros enforce_em_* independientes para Exchange Monitor.

`GET /saved-currencies` debe poder acotar Exchange Monitor a su valor propio
("Exchange Monitor", code `em`) o a su promedio ("Monitor Dólar", code `average`)
de forma independiente, sin afectar a otras plataformas ni cambiar el
comportamiento por defecto (ambas entradas si no se activa ningún flag).
"""
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.controller import venezuela_controller
from api.utils.constants.constants import Constants as c


client = TestClient(app, raise_server_exceptions=False)

SAVED = f"{c.API_V1_STR}/venezuela/saved-currencies"


def _em(code, name):
    return {"platform": c.EXCHANGE_MONITOR_NAME, "code": code, "name": name, "value": 1.0, "change": 0.0}


def _bcv():
    return {"platform": c.BCV_NAME, "code": "USD", "name": "Dolar", "value": 1.0, "change": 0.0}


@pytest.fixture
def mock_saved(monkeypatch):
    """getSavedCurrencies devuelve las 2 entradas de EM + 1 de BCV."""
    rows = [
        _em(c.EM_CODE_OWN, "Exchange Monitor"),
        _em(c.EM_CODE_AVERAGE, "Monitor Dólar"),
        _bcv(),
    ]
    monkeypatch.setattr(venezuela_controller.dollar_service, "getSavedCurrencies", AsyncMock(return_value=rows))


def _names(body):
    return sorted(item["name"] for item in body["data"] if item["platform"] == c.EXCHANGE_MONITOR_NAME)


def test_sin_enforce_em_devuelve_ambas(mock_saved):
    r = client.get(SAVED, params={"exchange_monitor": True})
    assert r.status_code == 200
    assert _names(r.json()) == ["Exchange Monitor", "Monitor Dólar"]


def test_enforce_em_own_solo_valor_propio(mock_saved):
    r = client.get(SAVED, params={"exchange_monitor": True, "enforce_em_own": True})
    assert r.status_code == 200
    assert _names(r.json()) == ["Exchange Monitor"]


def test_enforce_em_average_solo_promedio(mock_saved):
    r = client.get(SAVED, params={"exchange_monitor": True, "enforce_em_average": True})
    assert r.status_code == 200
    assert _names(r.json()) == ["Monitor Dólar"]


def test_ambos_enforce_em_devuelven_ambas(mock_saved):
    r = client.get(SAVED, params={"exchange_monitor": True, "enforce_em_own": True, "enforce_em_average": True})
    assert r.status_code == 200
    assert _names(r.json()) == ["Exchange Monitor", "Monitor Dólar"]


def test_enforce_em_no_afecta_otras_plataformas(mock_saved):
    """El filtro de EM no debe tocar entradas de otras plataformas (BCV)."""
    r = client.get(SAVED, params={"exchange_monitor": True, "enforce_em_own": True})
    body = r.json()
    platforms = {item["platform"] for item in body["data"]}
    assert c.BCV_NAME in platforms  # el BCV sigue pasando
