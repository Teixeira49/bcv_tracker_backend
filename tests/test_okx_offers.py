"""Issue #56 (DT-014): integración de OKX P2P como fuente de tasa del dólar.

Cubre el fetch por par (``getCurrenciesByOkx``) —análogo a Binance/Bybit sobre el
endpoint C2C público de OKX— y la **degradación elegante** de
``get_raw_okx_currencies``: omite los pares sin ofertas (caso real: USDC/Buy sin
liquidez en VES) y solo propaga ``SourceEmptyError`` (502) si NINGÚN par
devuelve datos.
"""
from unittest.mock import AsyncMock

import pytest

from api.core.errors.exceptions import ExternalSourceError, SourceEmptyError
from api.services.dollar_services import DollarService
from api.utils.constants.constants import Constants as c


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"data": {"sell": []}},
    {"data": {"sell": None}},
    {"data": None},
    {},
])
async def test_okx_sin_ofertas_lanza_error_tipado(payload):
    """Un par sin ofertas debe traducirse a un error de fuente vacía (502)."""
    service = DollarService()
    service.client.get = AsyncMock(return_value=payload)

    with pytest.raises(SourceEmptyError) as exc_info:
        await service.getCurrenciesByOkx(client=None, tradeType="Buy")

    error = exc_info.value
    assert isinstance(error, ExternalSourceError)
    assert error.status_code == c.STATUS_BAD_GATEWAY  # 502
    assert c.OKX_NAME in error.message


@pytest.mark.asyncio
async def test_okx_con_ofertas_calcula_promedio():
    """Con ofertas válidas debe promediar correctamente sin lanzar error."""
    service = DollarService()
    service.client.get = AsyncMock(
        return_value={"data": {"sell": [
            {"price": "832.0"},
            {"price": "834.0"},
        ]}}
    )

    currency = await service.getCurrenciesByOkx(client=None, asset="USDT", tradeType="Buy")

    assert currency.value == 833.0
    assert currency.platform == c.OKX_NAME


@pytest.mark.asyncio
async def test_okx_tradetype_mapea_side():
    """tradeType 'Buy' -> side 'sell' (anunciante vende); 'Sell' -> side 'buy'."""
    service = DollarService()
    captured = {}

    async def fake_get(url, params=None, headers=None, client=None):
        captured["side"] = params["side"]
        return {"data": {params["side"]: [{"price": "10.0"}]}}

    service.client.get = fake_get

    await service.getCurrenciesByOkx(client=None, tradeType="Buy")
    assert captured["side"] == "sell"

    await service.getCurrenciesByOkx(client=None, tradeType="Sell")
    assert captured["side"] == "buy"


@pytest.mark.asyncio
async def test_okx_degradacion_omite_pares_vacios():
    """Degradación elegante: si algunos pares no tienen ofertas se omiten."""
    service = DollarService()

    async def fake_pair(client, asset="USDT", fiat="VES", tradeType="Buy"):
        # USDC/Buy sin liquidez (como en el mercado real); el resto responde.
        if asset == "USDC" and tradeType == "Buy":
            raise SourceEmptyError(c.OKX_NAME)
        return service.createCurrency(asset, asset, 100.0, c.OKX_NAME)

    service.getCurrenciesByOkx = fake_pair

    currencies = await service.get_raw_okx_currencies()

    assert len(currencies) == 3  # 4 pares - 1 vacío
    assert all(cur.platform == c.OKX_NAME for cur in currencies)


@pytest.mark.asyncio
async def test_okx_todos_los_pares_vacios_lanza_error():
    """Si NINGÚN par tiene ofertas, se propaga SourceEmptyError (502)."""
    service = DollarService()

    async def fake_pair(client, asset="USDT", fiat="VES", tradeType="Buy"):
        raise SourceEmptyError(c.OKX_NAME)

    service.getCurrenciesByOkx = fake_pair

    with pytest.raises(SourceEmptyError):
        await service.get_raw_okx_currencies()


@pytest.mark.asyncio
async def test_okx_fallo_real_se_propaga_no_se_omite():
    """Un fallo real (no 'vacío') NO debe omitirse: se propaga tal cual."""
    service = DollarService()

    async def fake_pair(client, asset="USDT", fiat="VES", tradeType="Buy"):
        from api.core.errors.exceptions import SourceUnavailableError
        raise SourceUnavailableError(c.OKX_NAME)

    service.getCurrenciesByOkx = fake_pair

    with pytest.raises(ExternalSourceError):
        await service.get_raw_okx_currencies()
