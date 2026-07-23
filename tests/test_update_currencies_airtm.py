"""Airtm persistible vía PUT /update-currencies.

Con `airtm=true`, las tasas de Airtm se recolectan y se envían a guardar en la
BD junto con el resto de fuentes seleccionadas.
"""
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from api.main import app
from api.controller import dollar_controller
from api.utils.constants.constants import Constants as c


client = TestClient(app, raise_server_exceptions=False)

UPDATE = f"{c.API_V1_STR}/venezuela/update-currencies"


def test_update_currencies_solo_airtm_persiste(monkeypatch):
    airtm_rows = [
        dollar_controller.dollar_service.createCurrency("USD", "Dolar-Buy", 1.0, c.AIRTM_NAME),
        dollar_controller.dollar_service.createCurrency("USD", "Dolar-Sell", 2.0, c.AIRTM_NAME),
    ]
    monkeypatch.setattr(
        dollar_controller.dollar_service, "get_raw_airtm_currencies",
        AsyncMock(return_value=airtm_rows),
    )
    saved = AsyncMock(return_value={"message": "ok", "updated_count": 2})
    monkeypatch.setattr(dollar_controller.dollar_service, "save_currencies_to_db_async", saved)

    # Solo airtm; el resto en False para aislar la fuente.
    r = client.put(UPDATE, params={
        "bcv": False, "yadio": False, "binance": False, "bybit": False,
        "okx": False, "bitget": False, "dolarapi": False,
        "exchange_monitor": False, "airtm": True,
    })

    assert r.status_code == 200
    args, _ = saved.call_args
    assert len(args[0]) == 2  # las 2 tasas de Airtm se enviaron a guardar
    assert all(cur.platform == c.AIRTM_NAME for cur in args[0])
