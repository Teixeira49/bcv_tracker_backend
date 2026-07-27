"""OKX, Bitget y DolarAPI persistibles/consultables en ambos endpoints de datos.

Con el Body por mercado (#71):
- `PUT /update-currencies`: las 3 fuentes nuevas se recolectan y guardan; una
  fuente con {date, currencies} (BCV) sigue persistiendo su fecha.
- `POST /saved-currencies`: las 3 fuentes nuevas se leen de la BD (bd-todas).
"""
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from api.main import app
from api.controller import venezuela_controller
from api.utils.constants.constants import Constants as c


client = TestClient(app, raise_server_exceptions=False)
svc = venezuela_controller.dollar_service

UPDATE = f"{c.API_V1_STR}/venezuela/update-currencies"
SAVED = f"{c.API_V1_STR}/venezuela/saved-currencies"


def test_update_persiste_okx_bitget_dolarapi_y_fecha_bcv(monkeypatch):
    monkeypatch.setattr(svc, "get_raw_bcv_currencies",
                        AsyncMock(return_value={"date": "2026-07-09", "currencies": [svc.createCurrency("USD", "Dolar", 1.0, c.BCV_NAME)]}))
    monkeypatch.setattr(svc, "get_raw_okx_currencies",
                        AsyncMock(return_value=[svc.createCurrency("USDT", "Tether-Buy", 2.0, c.OKX_NAME),
                                                svc.createCurrency("USDT", "Tether-Sell", 3.0, c.OKX_NAME)]))
    monkeypatch.setattr(svc, "get_raw_bitget_currencies",
                        AsyncMock(return_value=[svc.createCurrency("USDT", "Tether-Buy", 4.0, c.BITGET_NAME)]))
    monkeypatch.setattr(svc, "get_raw_dolarapi_currencies",
                        AsyncMock(return_value=[svc.createCurrency("USD", "Oficial", 5.0, c.DOLARAPI_NAME)]))
    saved = AsyncMock(return_value={"message": "ok", "updated_count": 5})
    monkeypatch.setattr(svc, "save_currencies_to_db_async", saved)
    save_date = AsyncMock()
    monkeypatch.setattr(svc, "save_platform_date_async", save_date)

    # Body: BCV todas (en vivo), OKX/Bitget ambas (buy+sell), DolarAPI todas.
    r = client.put(UPDATE, json={"markets": {
        "bcv": "todas", "okx": "ambas", "bitget": "ambas", "dolarapi": "todas",
    }})

    assert r.status_code == 200
    stored = saved.call_args[0][0]
    platforms = sorted({cur.platform for cur in stored})
    assert platforms == sorted([c.BCV_NAME, c.OKX_NAME, c.BITGET_NAME, c.DOLARAPI_NAME])
    assert len(stored) == 5  # 1 BCV + 2 OKX + 1 Bitget + 1 DolarAPI
    # La fecha de plataforma de BCV (fuente tipo dict) se persistió
    save_date.assert_awaited_once_with(c.BCV_NAME, "2026-07-09")


def test_saved_currencies_selecciona_okx_bitget_dolarapi(monkeypatch):
    fetch = MagicMock(return_value=[])
    monkeypatch.setattr(svc, "_fetch_saved_for_platform", fetch)

    r = client.post(SAVED, json={"markets": {
        "okx": "bd-todas", "bitget": "bd-todas", "dolarapi": "bd-todas",
    }})

    assert r.status_code == 200
    read_platforms = {call.args[0] for call in fetch.call_args_list}
    assert c.OKX_NAME in read_platforms
    assert c.BITGET_NAME in read_platforms
    assert c.DOLARAPI_NAME in read_platforms
