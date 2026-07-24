"""Airtm seleccionable en GET /saved-currencies.

`airtm=true` debe incluir Airtm entre las plataformas consultadas en BD y
devolver sus filas guardadas, igual que el resto de fuentes.
"""
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.controller import venezuela_controller
from api.utils.constants.constants import Constants as c


client = TestClient(app, raise_server_exceptions=False)

SAVED = f"{c.API_V1_STR}/venezuela/saved-currencies"


def _airtm(name):
    return {"platform": c.AIRTM_NAME, "code": "USD", "name": name, "value": 1.0, "change": 0.0}


def test_airtm_true_consulta_y_devuelve_airtm(monkeypatch):
    saved = AsyncMock(return_value=[_airtm("Dolar-Buy"), _airtm("Dolar-Sell")])
    monkeypatch.setattr(venezuela_controller.dollar_service, "getSavedCurrencies", saved)

    r = client.get(SAVED, params={"airtm": True})

    assert r.status_code == 200
    # Airtm se pidió a la BD como plataforma
    _, kwargs = saved.call_args
    assert c.AIRTM_NAME in kwargs["platforms"]
    # y sus filas vuelven en la respuesta
    names = sorted(item["name"] for item in r.json()["data"] if item["platform"] == c.AIRTM_NAME)
    assert names == ["Dolar-Buy", "Dolar-Sell"]
