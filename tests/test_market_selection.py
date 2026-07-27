"""Issue #71: Body estructurado + máquina de estados por mercado.

Cubre el schema (`MarketSelection`), su validación por (mercado, modo), el
filtrado en vivo por modo (`_live_market`) y los orquestadores de ambos
endpoints (`update_from_selection`, `read_from_selection`), incluyendo el
default `off` para mercados no mencionados.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

import api.controller.venezuela_controller as ctrl
import api.main as main
from api.services.dollar_services import DollarService
from api.models.market_request import MarketName, MarketMode, MarketSelection
from api.utils.constants.constants import Constants as c


client = TestClient(main.app, raise_server_exceptions=False)
svc = ctrl.dollar_service
UPDATE = f"{c.API_V1_STR}/venezuela/update-currencies"
SAVED = f"{c.API_V1_STR}/venezuela/saved-currencies"


# --- Schema / validación ----------------------------------------------------

def test_active_excludes_off_and_absent():
    sel = MarketSelection(markets={"bcv": "todas", "yadio": "off"})
    active = sel.active()
    assert MarketName.BCV in active
    assert MarketName.YADIO not in active  # off
    assert MarketName.BINANCE not in active  # ausente = off


def test_invalid_mode_for_market_rejected():
    # 'average' es de cripto, no aplica a BCV.
    with pytest.raises(ValidationError):
        MarketSelection(markets={"bcv": "average"})


def test_empty_body_is_all_off():
    assert MarketSelection().active() == {}


# --- _live_market: filtrado por modo ----------------------------------------

@pytest.mark.asyncio
async def test_live_dollar_filters_usd(monkeypatch):
    service = DollarService()
    monkeypatch.setattr(service, "get_raw_yadio_currencies", AsyncMock(return_value=[
        service.createCurrency("USD", "Dolar", 1.0, c.YADIO_NAME),
        service.createCurrency("EUR", "Euro", 2.0, c.YADIO_NAME),
        service.createCurrency("BTC", "Bitcoin", 3.0, c.YADIO_NAME),
    ]))
    currencies, _ = await service._live_market(MarketName.YADIO, MarketMode.LIVE_DOLLAR)
    assert [cur.code for cur in currencies] == ["USD"]


@pytest.mark.asyncio
async def test_average_mode_averages_by_asset(monkeypatch):
    service = DollarService()
    monkeypatch.setattr(service, "get_raw_binance_currencies", AsyncMock(return_value=[
        service.createCurrency("USDT", "Tether-Buy", 10.0, c.BINANCE_NAME),
        service.createCurrency("USDT", "Tether-Sell", 20.0, c.BINANCE_NAME),
    ]))
    currencies, _ = await service._live_market(MarketName.BINANCE, MarketMode.AVERAGE)
    assert len(currencies) == 1
    assert currencies[0].code == "USDT"
    assert currencies[0].value == 15.0  # (10+20)/2


# --- update_from_selection --------------------------------------------------

@pytest.mark.asyncio
async def test_update_persists_only_active_live_markets(monkeypatch):
    service = DollarService()
    monkeypatch.setattr(service, "get_raw_bcv_currencies",
                        AsyncMock(return_value={"date": "2026-07-24", "currencies": [service.createCurrency("USD", "Dolar", 1.0, c.BCV_NAME)]}))
    saved = AsyncMock(return_value={"message": "ok", "updated_count": 1})
    monkeypatch.setattr(service, "save_currencies_to_db_async", saved)
    save_date = AsyncMock()
    monkeypatch.setattr(service, "save_platform_date_async", save_date)

    sel = MarketSelection(markets={"bcv": "todas", "yadio": "off"})
    result = await service.update_from_selection(sel)

    assert result["updated_count"] == 1
    save_date.assert_awaited_once_with(c.BCV_NAME, "2026-07-24")


@pytest.mark.asyncio
async def test_update_empty_selection_returns_zero():
    service = DollarService()
    result = await service.update_from_selection(MarketSelection())
    assert result["updated_count"] == 0


# --- read_from_selection ----------------------------------------------------

@pytest.mark.asyncio
async def test_read_mixes_db_and_live(monkeypatch):
    service = DollarService()
    # BCV desde BD.
    monkeypatch.setattr(service, "_fetch_saved_for_platform",
                        MagicMock(return_value=[{"platform": c.BCV_NAME, "code": "USD", "name": "Dolar", "value": 1.0, "change": 0.0, "id": 1}]))
    # Yadio en vivo (con ROC calculado, que mockeamos como identidad).
    monkeypatch.setattr(service, "get_raw_yadio_currencies",
                        AsyncMock(return_value=[service.createCurrency("USD", "Dolar", 2.0, c.YADIO_NAME)]))
    monkeypatch.setattr(service, "calculate_live_changes", AsyncMock(side_effect=lambda x: x))

    sel = MarketSelection(markets={"bcv": "bd-todas", "yadio": "todas"})
    results = await service.read_from_selection(sel)

    platforms = {item["platform"] for item in results}
    assert platforms == {c.BCV_NAME, c.YADIO_NAME}


# --- Endpoints --------------------------------------------------------------

def test_update_endpoint_rejects_bd_mode():
    r = client.put(UPDATE, json={"markets": {"bcv": "bd-todas"}})
    assert r.status_code == 422


def test_saved_endpoint_is_post_with_body(monkeypatch):
    monkeypatch.setattr(svc, "read_from_selection", AsyncMock(return_value=[]))
    r = client.post(SAVED, json={"markets": {"bcv": "bd-todas"}})
    assert r.status_code == 200
    assert r.json()["data"] == []
    # El antiguo GET ya no existe.
    assert client.get(SAVED).status_code == 405
