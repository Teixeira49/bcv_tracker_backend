"""Issue #55 (DT-011): integración de Airtm como fuente de tasa del dólar.

Airtm expone un JSON público sin auth en ``rates.airtm.io`` con la forma
``{"data": {"ves/usd": {"addValue": <compra>, "withdrawValue": <venta>}}}``.
Cubre el fetch (``getCurrenciesByAirtm`` / ``get_raw_airtm_currencies``) y el
caso sin datos (par ``ves/usd`` ausente o incompleto → ``SourceEmptyError`` 502),
igual que el resto de fuentes.
"""
from unittest.mock import AsyncMock

import pytest

from api.core.errors.exceptions import ExternalSourceError, SourceEmptyError
from api.services.dollar_services import DollarService
from api.utils.constants.constants import Constants as c


def _payload(add=842.41, withdraw=800.02):
    return {"data": {"ves/usd": {"addValue": add, "withdrawValue": withdraw},
                     "eur/usd": {"addValue": 0.91, "withdrawValue": 0.85}}}


@pytest.mark.asyncio
async def test_airtm_con_datos_devuelve_buy_y_sell():
    """Con el par ves/usd presente, devuelve Buy (addValue) y Sell (withdrawValue)."""
    service = DollarService()
    service.client.get = AsyncMock(return_value=_payload())

    currencies = await service.get_raw_airtm_currencies()

    assert len(currencies) == 2
    assert all(cur.platform == c.AIRTM_NAME and cur.code == "USD" for cur in currencies)
    by_value = {cur.value for cur in currencies}
    assert by_value == {842.41, 800.02}


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"data": {}},                                     # sin el par
    {"data": {"ves/usd": {}}},                        # par vacío
    {"data": {"ves/usd": {"addValue": 842.41}}},      # falta withdrawValue
    {"data": {"ves/usd": {"withdrawValue": 800.02}}}, # falta addValue
    {"data": None},
    {},
])
async def test_airtm_sin_par_ves_usd_lanza_error_tipado(payload):
    """Sin el par ves/usd (o incompleto) se propaga SourceEmptyError (502)."""
    service = DollarService()
    service.client.get = AsyncMock(return_value=payload)

    with pytest.raises(SourceEmptyError) as exc_info:
        await service.get_raw_airtm_currencies()

    error = exc_info.value
    assert isinstance(error, ExternalSourceError)
    assert error.status_code == c.STATUS_BAD_GATEWAY  # 502
    assert c.AIRTM_NAME in error.message


@pytest.mark.asyncio
async def test_airtm_serializado_incluye_logo():
    """getCurrenciesByAirtm serializa e incluye el logo de la plataforma."""
    service = DollarService()
    service.client.get = AsyncMock(return_value=_payload())

    serialized = await service.getCurrenciesByAirtm()

    assert len(serialized) == 2
    assert all(item["platform"] == c.AIRTM_NAME for item in serialized)
    assert all(item["platform_img"] == c.AIRTM_LOGO_URL for item in serialized)
