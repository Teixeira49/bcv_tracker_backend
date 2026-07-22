"""Issue #57 (DT-015): integración de Bitget P2P como fuente de tasa del dólar.

Cubre el fetch por par (``getCurrenciesByBitget``) —análogo a Binance/Bybit/OKX
sobre el endpoint P2P público de Bitget (POST)— y la **degradación elegante** de
``get_raw_bitget_currencies``: omite los pares sin ofertas y solo propaga
``SourceEmptyError`` (502) si NINGÚN par devuelve datos.
"""
import json
from unittest.mock import AsyncMock

import httpx
import pytest

from api.core.errors.exceptions import ExternalSourceError, SourceEmptyError, SourceUnavailableError
from api.services.dollar_services import DollarService
from api.utils.constants.constants import Constants as c


def _http_429():
    """Construye un httpx.HTTPStatusError 429 (Retry-After: 0 para no dormir)."""
    req = httpx.Request("POST", "https://www.bitget.com/v1/p2p/pub/adv/queryAdvList")
    resp = httpx.Response(429, request=req, headers={"Retry-After": "0"})
    return httpx.HTTPStatusError("429 Too Many Requests", request=req, response=resp)


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"data": {"dataList": []}},
    {"data": {"dataList": None}},
    {"data": None},
    {},
])
async def test_bitget_sin_ofertas_lanza_error_tipado(payload):
    """Un par sin ofertas debe traducirse a un error de fuente vacía (502)."""
    service = DollarService()
    service.client.post = AsyncMock(return_value=payload)

    with pytest.raises(SourceEmptyError) as exc_info:
        await service.getCurrenciesByBitget(client=None, tradeType="Buy")

    error = exc_info.value
    assert isinstance(error, ExternalSourceError)
    assert error.status_code == c.STATUS_BAD_GATEWAY  # 502
    assert c.BITGET_NAME in error.message


@pytest.mark.asyncio
async def test_bitget_con_ofertas_calcula_promedio():
    """Con ofertas válidas debe promediar correctamente sin lanzar error."""
    service = DollarService()
    service.client.post = AsyncMock(
        return_value={"data": {"dataList": [
            {"price": "864.0"},
            {"price": "868.0"},
        ]}}
    )

    currency = await service.getCurrenciesByBitget(client=None, asset="USDT", tradeType="Buy")

    assert currency.value == 866.0
    assert currency.platform == c.BITGET_NAME


@pytest.mark.asyncio
async def test_bitget_tradetype_mapea_side():
    """tradeType 'Buy' -> side 1 (asks); 'Sell' -> side 2 (bids)."""
    service = DollarService()
    captured = {}

    async def fake_post(url, data=None, headers=None, client=None):
        captured["side"] = json.loads(data)["side"]
        return {"data": {"dataList": [{"price": "10.0"}]}}

    service.client.post = fake_post

    await service.getCurrenciesByBitget(client=None, tradeType="Buy")
    assert captured["side"] == 1

    await service.getCurrenciesByBitget(client=None, tradeType="Sell")
    assert captured["side"] == 2


@pytest.mark.asyncio
async def test_bitget_degradacion_omite_pares_vacios():
    """Degradación elegante: si algunos pares no tienen ofertas se omiten."""
    service = DollarService()

    async def fake_pair(client, asset="USDT", fiat="VES", tradeType="Buy"):
        if asset == "USDC" and tradeType == "Buy":
            raise SourceEmptyError(c.BITGET_NAME)
        return service.createCurrency(asset, asset, 100.0, c.BITGET_NAME)

    service.getCurrenciesByBitget = fake_pair

    currencies = await service.get_raw_bitget_currencies()

    assert len(currencies) == 3  # 4 pares - 1 vacío
    assert all(cur.platform == c.BITGET_NAME for cur in currencies)


@pytest.mark.asyncio
async def test_bitget_todos_los_pares_vacios_lanza_error():
    """Si NINGÚN par tiene ofertas, se propaga SourceEmptyError (502)."""
    service = DollarService()

    async def fake_pair(client, asset="USDT", fiat="VES", tradeType="Buy"):
        raise SourceEmptyError(c.BITGET_NAME)

    service.getCurrenciesByBitget = fake_pair

    with pytest.raises(SourceEmptyError):
        await service.get_raw_bitget_currencies()


@pytest.mark.asyncio
async def test_bitget_reintenta_ante_429_y_tiene_exito(monkeypatch):
    """DT-017: un 429 transitorio se reintenta y la 2ª respuesta OK se usa."""
    service = DollarService()
    calls = {"n": 0}

    async def flaky_post(url, data=None, headers=None, client=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _http_429()
        return {"data": {"dataList": [{"price": "800.0"}]}}

    monkeypatch.setattr(service.client, "post", flaky_post)

    currency = await service.getCurrenciesByBitget(client=None, tradeType="Buy")

    assert currency.value == 800.0
    assert calls["n"] == 2  # reintentó exactamente una vez


@pytest.mark.asyncio
async def test_bitget_429_persistente_se_rinde_como_502(monkeypatch):
    """DT-017: si el 429 persiste tras los reintentos, se rinde como 502 tipado."""
    service = DollarService()
    calls = {"n": 0}

    async def always_429(url, data=None, headers=None, client=None):
        calls["n"] += 1
        raise _http_429()

    monkeypatch.setattr(service.client, "post", always_429)

    with pytest.raises(SourceUnavailableError):
        await service.getCurrenciesByBitget(client=None, tradeType="Buy")

    assert calls["n"] == c.BITGET_MAX_RETRIES + 1  # intento inicial + reintentos


@pytest.mark.asyncio
async def test_bitget_fallo_real_se_propaga_no_se_omite():
    """Un fallo real (no 'vacío') NO debe omitirse: se propaga tal cual."""
    service = DollarService()

    async def fake_pair(client, asset="USDT", fiat="VES", tradeType="Buy"):
        from api.core.errors.exceptions import SourceUnavailableError
        raise SourceUnavailableError(c.BITGET_NAME)

    service.getCurrenciesByBitget = fake_pair

    with pytest.raises(ExternalSourceError):
        await service.get_raw_bitget_currencies()
