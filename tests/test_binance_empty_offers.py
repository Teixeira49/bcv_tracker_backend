"""Regresión del issue #11: ZeroDivisionError al promediar precios de Binance P2P.

Verifica que, si Binance P2P responde sin ofertas (lista ``data`` vacía o
ausente), ``getCurrenciesByBinance`` no revienta con ``ZeroDivisionError`` sino
que propaga un error tipado (``SourceEmptyError`` -> HTTP 502) con mensaje claro.
"""
from unittest.mock import AsyncMock

import pytest

from api.core.errors.exceptions import ExternalSourceError, SourceEmptyError
from api.services.dollar_services import DollarService
from api.utils.constants.constants import Constants as c


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{"data": []}, {"data": None}, {}])
async def test_binance_sin_ofertas_lanza_error_tipado(payload):
    """Una respuesta sin ofertas debe traducirse a un error de fuente vacía (502)."""
    service = DollarService()
    service.client.post = AsyncMock(return_value=payload)

    with pytest.raises(SourceEmptyError) as exc_info:
        await service.getCurrenciesByBinance(client=None)

    error = exc_info.value
    assert isinstance(error, ExternalSourceError)
    assert error.status_code == c.STATUS_BAD_GATEWAY  # 502
    assert c.BINANCE_NAME in error.message


@pytest.mark.asyncio
async def test_binance_con_ofertas_calcula_promedio():
    """Con ofertas válidas debe promediar correctamente sin lanzar error."""
    service = DollarService()
    service.client.post = AsyncMock(
        return_value={"data": [
            {"adv": {"price": "40.0"}},
            {"adv": {"price": "42.0"}},
        ]}
    )

    currency = await service.getCurrenciesByBinance(client=None, asset="USDT", tradeType="Buy")

    assert currency.value == 41.0
    assert currency.platform == c.BINANCE_NAME
