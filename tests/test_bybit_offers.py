"""Issue #2 (DT-009): integración de Bybit P2P como fuente de tasa del dólar.

Cubre el fetch por par (``getCurrenciesByBybit``) —análogo a Binance— y la
**degradación elegante** de ``get_raw_bybit_currencies``: omite los pares sin
ofertas (caso real: USDC/Buy sin liquidez en VES) y solo propaga
``SourceEmptyError`` (502) si NINGÚN par devuelve datos.
"""
import json
from unittest.mock import AsyncMock

import pytest

from api.core.errors.exceptions import ExternalSourceError, SourceEmptyError
from api.services.dollar_services import DollarService
from api.utils.constants.constants import Constants as c


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"result": {"items": []}},
    {"result": {"items": None}},
    {"result": None},
    {},
])
async def test_bybit_sin_ofertas_lanza_error_tipado(payload):
    """Un par sin ofertas debe traducirse a un error de fuente vacía (502)."""
    service = DollarService()
    service.client.post = AsyncMock(return_value=payload)

    with pytest.raises(SourceEmptyError) as exc_info:
        await service.getCurrenciesByBybit(client=None)

    error = exc_info.value
    assert isinstance(error, ExternalSourceError)
    assert error.status_code == c.STATUS_BAD_GATEWAY  # 502
    assert c.BYBIT_NAME in error.message


@pytest.mark.asyncio
async def test_bybit_con_ofertas_calcula_promedio():
    """Con ofertas válidas debe promediar correctamente sin lanzar error."""
    service = DollarService()
    service.client.post = AsyncMock(
        return_value={"result": {"items": [
            {"price": "820.0"},
            {"price": "824.0"},
        ]}}
    )

    currency = await service.getCurrenciesByBybit(client=None, asset="USDT", tradeType="Buy")

    assert currency.value == 822.0
    assert currency.platform == c.BYBIT_NAME


@pytest.mark.asyncio
async def test_bybit_tradetype_mapea_side():
    """tradeType 'Buy' -> side '1' (asks); 'Sell' -> side '0' (bids)."""
    service = DollarService()
    captured = {}

    async def fake_post(url, data=None, headers=None, client=None):
        captured["side"] = json.loads(data)["side"]
        return {"result": {"items": [{"price": "10.0"}]}}

    service.client.post = fake_post

    await service.getCurrenciesByBybit(client=None, tradeType="Buy")
    assert captured["side"] == "1"

    await service.getCurrenciesByBybit(client=None, tradeType="Sell")
    assert captured["side"] == "0"


@pytest.mark.asyncio
async def test_bybit_degradacion_omite_pares_vacios():
    """Degradación elegante: si algunos pares no tienen ofertas se omiten."""
    service = DollarService()

    async def fake_pair(client, asset="USDT", fiat="VES", tradeType="Buy"):
        # USDC/Buy sin liquidez (como en el mercado real); el resto responde.
        if asset == "USDC" and tradeType == "Buy":
            raise SourceEmptyError(c.BYBIT_NAME)
        return service.createCurrency(asset, asset, 100.0, c.BYBIT_NAME)

    service.getCurrenciesByBybit = fake_pair

    currencies = await service.get_raw_bybit_currencies()

    assert len(currencies) == 3  # 4 pares - 1 vacío
    assert all(cur.platform == c.BYBIT_NAME for cur in currencies)


@pytest.mark.asyncio
async def test_bybit_todos_los_pares_vacios_lanza_error():
    """Si NINGÚN par tiene ofertas, se propaga SourceEmptyError (502)."""
    service = DollarService()

    async def fake_pair(client, asset="USDT", fiat="VES", tradeType="Buy"):
        raise SourceEmptyError(c.BYBIT_NAME)

    service.getCurrenciesByBybit = fake_pair

    with pytest.raises(SourceEmptyError):
        await service.get_raw_bybit_currencies()


@pytest.mark.asyncio
async def test_bybit_fallo_real_se_propaga_no_se_omite():
    """Un fallo real (no 'vacío') NO debe omitirse: se propaga tal cual."""
    service = DollarService()

    async def fake_pair(client, asset="USDT", fiat="VES", tradeType="Buy"):
        from api.core.errors.exceptions import SourceUnavailableError
        raise SourceUnavailableError(c.BYBIT_NAME)

    service.getCurrenciesByBybit = fake_pair

    with pytest.raises(ExternalSourceError):
        await service.get_raw_bybit_currencies()


def test_average_by_asset_promedia_lados_disponibles():
    """average_by_asset promedia por activo; con un solo lado usa ese valor."""
    service = DollarService()
    currencies = [
        service.createCurrency("USDT", "Tether-Buy", 828.0, c.BYBIT_NAME),
        service.createCurrency("USDT", "Tether-Sell", 820.0, c.BYBIT_NAME),
        service.createCurrency("USDC", "USD Coin-Sell", 742.0, c.BYBIT_NAME),  # solo un lado
    ]

    averaged = {cur.code: cur.value for cur in service.average_by_asset(currencies, c.BYBIT_NAME)}

    assert averaged["USDT"] == 824.0   # (828 + 820) / 2
    assert averaged["USDC"] == 742.0   # único lado disponible
