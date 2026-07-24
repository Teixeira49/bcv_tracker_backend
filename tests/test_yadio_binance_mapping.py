"""Issue #20: mapeo del JSON de Yadio y de Binance a objetos Currency.

Fija cómo se transforman las respuestas JSON de estas fuentes en tasas:

- **Yadio** (``getCurrenciesByYadio`` / ``getDollarByYadio``): la tasa VES/divisa
  se calcula como ``VES["VES"] / VES["<code>"]`` (USD, EUR) y el BTC se toma
  directo; el endpoint del dólar usa ``response["rate"]``.
- **Binance** (``getCurrenciesByBinance``): promedia los ``adv.price`` de las
  ofertas del par y arma el Currency del lado (Buy/Sell) correspondiente.
"""
from unittest.mock import AsyncMock

import pytest

from api.services.dollar_services import DollarService
from api.utils.constants.constants import Constants as c


# --------------------------------------------------------------------------- #
#  Yadio
# --------------------------------------------------------------------------- #
def _yadio_exrates():
    # response["VES"]["VES"] / response["VES"]["<code>"] = tasa en VES.
    return {"VES": {"VES": 1.0, "USD": 0.0025, "EUR": 0.002}, "BTC": 30000000.0}


@pytest.mark.asyncio
async def test_yadio_mapea_usd_eur_btc():
    service = DollarService()
    service.client.get = AsyncMock(return_value=_yadio_exrates())

    result = await service.getCurrenciesByYadio()

    by_code = {item["code"]: item for item in result}
    assert set(by_code) == {"USD", "EUR", "BTC"}
    assert by_code["USD"]["value"] == 400.0   # 1.0 / 0.0025
    assert by_code["EUR"]["value"] == 500.0   # 1.0 / 0.002
    assert by_code["BTC"]["value"] == 30000000.0  # tomado directo
    assert all(item["platform"] == c.YADIO_NAME for item in result)
    assert all(item["platform_img"] == c.YADIO_LOGO_URL for item in result)


@pytest.mark.asyncio
async def test_yadio_dollar_usa_campo_rate():
    service = DollarService()
    service.client.get = AsyncMock(return_value={"rate": 402.5, "base": "VES"})

    dollar = await service.getDollarByYadio()

    assert dollar["code"] == "USD"
    assert dollar["name"] == "Dolar"
    assert dollar["value"] == 402.5
    assert dollar["platform"] == c.YADIO_NAME


# --------------------------------------------------------------------------- #
#  Binance
# --------------------------------------------------------------------------- #
def _binance_offers(prices):
    return {"data": [{"adv": {"price": str(p)}} for p in prices]}


@pytest.mark.asyncio
async def test_binance_promedia_precios_de_las_ofertas():
    service = DollarService()
    service.client.post = AsyncMock(return_value=_binance_offers([800.0, 810.0, 820.0]))

    currency = await service.getCurrenciesByBinance(None, asset="USDT", fiat="VES", tradeType="Buy")

    assert currency.code == "USDT"
    # createCurrency normaliza el nombre con str.capitalize() -> "Tether-buy".
    assert currency.name == "Tether-buy"
    assert currency.value == 810.0  # promedio de 800/810/820
    assert currency.platform == c.BINANCE_NAME


@pytest.mark.asyncio
async def test_binance_usdc_sell_nombra_el_lado_correcto():
    service = DollarService()
    service.client.post = AsyncMock(return_value=_binance_offers([1000.0, 1010.0]))

    currency = await service.getCurrenciesByBinance(None, asset="USDC", fiat="VES", tradeType="Sell")

    assert currency.code == "USDC"
    # str.capitalize() -> "Usd coin-sell".
    assert currency.name == "Usd coin-sell"
    assert currency.value == 1005.0
