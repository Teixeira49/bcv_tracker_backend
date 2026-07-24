"""Airtm seleccionable en POST /saved-currencies (Body por mercado, #71).

Con ``{"markets": {"airtm": "bd-todas"}}`` se lee Airtm de la BD y se devuelven
sus filas guardadas, igual que el resto de fuentes.
"""
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.main import app
from api.controller import venezuela_controller
from api.utils.constants.constants import Constants as c


client = TestClient(app, raise_server_exceptions=False)

SAVED = f"{c.API_V1_STR}/venezuela/saved-currencies"


def _airtm(name):
    return {"platform": c.AIRTM_NAME, "code": "USD", "name": name, "value": 1.0, "change": 0.0}


def test_airtm_bd_todas_consulta_y_devuelve_airtm(monkeypatch):
    fetch = MagicMock(return_value=[_airtm("Dolar-Buy"), _airtm("Dolar-Sell")])
    monkeypatch.setattr(venezuela_controller.dollar_service, "_fetch_saved_for_platform", fetch)

    r = client.post(SAVED, json={"markets": {"airtm": "bd-todas"}})

    assert r.status_code == 200
    # Airtm se leyó de la BD como plataforma, sin filtro de solo-dólar.
    args, kwargs = fetch.call_args
    assert args[0] == c.AIRTM_NAME
    assert (args[1:] or (kwargs.get("dollar_only"),))[0] is False
    # y sus filas vuelven en la respuesta
    names = sorted(item["name"] for item in r.json()["data"] if item["platform"] == c.AIRTM_NAME)
    assert names == ["Dolar-Buy", "Dolar-Sell"]
