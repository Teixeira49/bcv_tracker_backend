"""Issue #58 (DT-016): integración de DolarAPI como fuente agregada del dólar.

DolarAPI (ve.dolarapi.com/v1/dolares) devuelve una lista de entradas por fuente
(oficial, paralelo, ...) con ``promedio`` (y a veces ``compra``/``venta``).
Cubre el mapeo a Currency (usando ``promedio``, con fallback a compra/venta) y el
caso sin datos usables (→ ``SourceEmptyError`` 502), igual que el resto de fuentes.
"""
from unittest.mock import AsyncMock

import pytest

from api.core.errors.exceptions import ExternalSourceError, SourceEmptyError
from api.services.dollar_services import DollarService
from api.utils.constants.constants import Constants as c


def _payload():
    return [
        {"moneda": "USD", "fuente": "oficial", "nombre": "Dólar", "compra": None, "venta": None, "promedio": 737.23},
        {"moneda": "USD", "fuente": "paralelo", "nombre": "Paralelo", "compra": None, "venta": None, "promedio": 843.32},
    ]


@pytest.mark.asyncio
async def test_dolarapi_mapea_oficial_y_paralelo():
    """Con datos válidos mapea cada fuente a Currency usando 'promedio'."""
    service = DollarService()
    service.client.get = AsyncMock(return_value=_payload())

    currencies = await service.get_raw_dolarapi_currencies()

    assert len(currencies) == 2
    assert all(cur.platform == c.DOLARAPI_NAME for cur in currencies)
    values = sorted(cur.value for cur in currencies)
    assert values == [737.23, 843.32]


@pytest.mark.asyncio
async def test_dolarapi_fallback_a_compra_venta_si_promedio_nulo():
    """Si 'promedio' viene nulo, promedia compra/venta disponibles."""
    service = DollarService()
    service.client.get = AsyncMock(return_value=[
        {"moneda": "USD", "fuente": "oficial", "compra": 700.0, "venta": 720.0, "promedio": None},
    ])

    currencies = await service.get_raw_dolarapi_currencies()

    assert len(currencies) == 1
    assert currencies[0].value == 710.0  # (700 + 720) / 2


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    [],
    [{"moneda": "USD", "fuente": "oficial", "compra": None, "venta": None, "promedio": None}],
    None,
])
async def test_dolarapi_sin_datos_usables_lanza_error_tipado(payload):
    """Sin ninguna tasa usable se propaga SourceEmptyError (502)."""
    service = DollarService()
    service.client.get = AsyncMock(return_value=payload)

    with pytest.raises(SourceEmptyError) as exc_info:
        await service.get_raw_dolarapi_currencies()

    error = exc_info.value
    assert isinstance(error, ExternalSourceError)
    assert error.status_code == c.STATUS_BAD_GATEWAY  # 502
    assert c.DOLARAPI_NAME in error.message


@pytest.mark.asyncio
async def test_dolarapi_serializado_incluye_logo():
    """getCurrenciesByDolarApi serializa e incluye el logo de la plataforma."""
    service = DollarService()
    service.client.get = AsyncMock(return_value=_payload())

    serialized = await service.getCurrenciesByDolarApi()

    assert len(serialized) == 2
    assert all(item["platform"] == c.DOLARAPI_NAME for item in serialized)
    assert all(item["platform_img"] == c.DOLARAPI_LOGO_URL for item in serialized)
