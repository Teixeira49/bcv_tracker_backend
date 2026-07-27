"""Modos de Exchange Monitor en el Body por mercado (#71, reemplaza a #68).

Los antiguos flags ``enforce_em_own`` / ``enforce_em_average`` de saved-currencies
se sustituyen por los modos por mercado de Exchange Monitor:

- ``own``          → solo el valor propio ("Exchange Monitor", code ``em``).
- ``own+monitor``  → valor propio + promedio ("Monitor Dólar", code ``average``).

Estos tests fijan el filtrado por modo a nivel de servicio (``_live_market``),
que es donde vive la máquina de estados.
"""
from unittest.mock import AsyncMock

import pytest

from api.services.dollar_services import DollarService
from api.models.market_request import MarketName, MarketMode, MarketSelection
from api.utils.constants.constants import Constants as c


def _em_payload(service):
    """Payload en vivo de EM con sus dos entradas propias (own + average)."""
    return {
        "date": "2026-07-24",
        "currencies": [
            service.createCurrency(c.EM_CODE_OWN, "Exchange Monitor", 1.0, c.EXCHANGE_MONITOR_NAME),
            service.createCurrency(c.EM_CODE_AVERAGE, "Monitor Dolar", 2.0, c.EXCHANGE_MONITOR_NAME),
        ],
    }


@pytest.mark.asyncio
async def test_em_own_devuelve_solo_valor_propio(monkeypatch):
    service = DollarService()
    monkeypatch.setattr(service, "get_raw_exchange_monitor_currencies",
                        AsyncMock(return_value=_em_payload(service)))

    currencies, date = await service._live_market(MarketName.EXCHANGE_MONITOR, MarketMode.EM_OWN)

    assert [cur.code for cur in currencies] == [c.EM_CODE_OWN]
    assert date == "2026-07-24"


@pytest.mark.asyncio
async def test_em_own_monitor_devuelve_ambas(monkeypatch):
    service = DollarService()
    monkeypatch.setattr(service, "get_raw_exchange_monitor_currencies",
                        AsyncMock(return_value=_em_payload(service)))

    currencies, _date = await service._live_market(MarketName.EXCHANGE_MONITOR, MarketMode.EM_OWN_MONITOR)

    assert sorted(cur.code for cur in currencies) == sorted([c.EM_CODE_OWN, c.EM_CODE_AVERAGE])


def test_em_rejects_invalid_mode():
    """El Body valida: un modo no permitido para EM (p. ej. 'solo-dolar') falla."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        MarketSelection(markets={"exchange_monitor": "solo-dolar"})
