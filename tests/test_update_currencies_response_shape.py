"""Issue #30: forma consistente de la respuesta de update-currencies.

``update_currencies`` devolvía ``updated_count`` en el camino de éxito pero
``updated_currencies`` en el early-return sin datos. La forma de la respuesta
era inconsistente entre ambos caminos (solo coincidía en el JSON final gracias
a ``populate_by_name`` + ``response_model``). Estos tests fijan que **ambos
caminos** devuelven exactamente la misma estructura y el mismo nombre de campo
(el alias ``updated_count`` de ``UpdateCurrenciesResponseData``).
"""
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import api.controller.venezuela_controller as ctrl
import api.main as main
from api.utils.constants.constants import Constants as c


client = TestClient(main.app)
svc = ctrl.dollar_service
UPDATE = f"{c.API_V1_STR}/venezuela/update-currencies"
ONLY_BCV = {
    "bcv": True, "yadio": False, "binance": False, "bybit": False, "okx": False,
    "bitget": False, "airtm": False, "dolarapi": False, "exchange_monitor": False,
}


def test_success_path_uses_updated_count(monkeypatch):
    """El camino de éxito expone `updated_count` con el conteo persistido."""
    monkeypatch.setattr(svc, "get_raw_bcv_currencies",
                        AsyncMock(return_value={"date": None, "currencies": [svc.createCurrency("USD", "Dolar", 1.0, c.BCV_NAME)]}))
    monkeypatch.setattr(svc, "save_currencies_to_db_async",
                        AsyncMock(return_value={"message": "ok", "updated_count": 1}))

    data = client.put(UPDATE, params=ONLY_BCV).json()["data"]

    assert set(data.keys()) == {"message", "updated_count"}
    assert data["updated_count"] == 1


def test_empty_path_uses_same_shape(monkeypatch):
    """El early-return sin datos usa la MISMA estructura y nombre de campo."""
    monkeypatch.setattr(svc, "get_raw_bcv_currencies",
                        AsyncMock(return_value={"date": None, "currencies": []}))

    data = client.put(UPDATE, params=ONLY_BCV).json()["data"]

    assert set(data.keys()) == {"message", "updated_count"}
    assert data["updated_count"] == 0


def test_both_paths_have_identical_field_set(monkeypatch):
    """Ambos caminos exponen exactamente el mismo conjunto de campos."""
    monkeypatch.setattr(svc, "get_raw_bcv_currencies",
                        AsyncMock(return_value={"date": None, "currencies": [svc.createCurrency("USD", "Dolar", 1.0, c.BCV_NAME)]}))
    monkeypatch.setattr(svc, "save_currencies_to_db_async",
                        AsyncMock(return_value={"message": "ok", "updated_count": 1}))
    success = client.put(UPDATE, params=ONLY_BCV).json()["data"]

    monkeypatch.setattr(svc, "get_raw_bcv_currencies",
                        AsyncMock(return_value={"date": None, "currencies": []}))
    empty = client.put(UPDATE, params=ONLY_BCV).json()["data"]

    assert set(success.keys()) == set(empty.keys())
