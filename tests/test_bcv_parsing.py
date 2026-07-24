"""Issue #20: parseo del HTML del BCV con un fixture HTML grabado.

El core del BCV es scraping frágil sobre el HTML del portal oficial
(``getCurrenciesByBCV`` / ``getDollarValueByBCV`` en
``api/services/dollar_services.py``). Estos tests fijan el contrato de parseo
usando un fixture HTML grabado (``tests/fixtures/bcv_rates.html``): si el parseo
o los selectores (``ScrappingTags``) cambian y rompen la extracción, fallan.
"""
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from api.services.dollar_services import DollarService
from api.utils.constants.constants import Constants as c


FIXTURE = (Path(__file__).parent / "fixtures" / "bcv_rates.html").read_bytes()


@pytest.mark.asyncio
async def test_getCurrenciesByBCV_parses_date_and_all_currencies():
    """Extrae la fecha de vigencia y las 5 divisas publicadas (USD, EUR, CNY, TRY, RUB)."""
    service = DollarService()
    service.client.get_content = AsyncMock(return_value=FIXTURE)

    result = await service.getCurrenciesByBCV()

    assert result["date"] == "2026-07-24T00:00:00-04:00"
    by_code = {c_["code"]: c_ for c_ in result["currencies"]}
    assert set(by_code) == {"USD", "EUR", "CNY", "TRY", "RUB"}
    # Valor con coma decimal y ceros de relleno -> float limpio.
    assert by_code["USD"]["value"] == 782.74
    assert by_code["EUR"]["value"] == 850.12
    # El nombre proviene del atributo id del bloque (capitalizado por createCurrency).
    assert by_code["USD"]["name"] == "Dolar"
    assert by_code["EUR"]["name"] == "Euro"
    # Todas quedan atribuidas al BCV con su logo.
    assert all(item["platform"] == c.BCV_NAME for item in result["currencies"])
    assert all(item["platform_img"] == c.BCV_LOGO_URL for item in result["currencies"])


@pytest.mark.asyncio
async def test_getDollarValueByBCV_parses_only_usd():
    """El endpoint del dólar aísla el bloque id='dolar' y devuelve solo USD."""
    service = DollarService()
    service.client.get_content = AsyncMock(return_value=FIXTURE)

    dollar = await service.getDollarValueByBCV()

    assert dollar["code"] == "USD"
    assert dollar["value"] == 782.74
    assert dollar["platform"] == c.BCV_NAME
    assert dollar["platform_img"] == c.BCV_LOGO_URL


@pytest.mark.asyncio
async def test_getCurrenciesByBCV_without_date_element_degrades_to_none():
    """Si falta el elemento de fecha, ``date`` es None y las divisas se parsean igual."""
    service = DollarService()
    html_sin_fecha = FIXTURE.replace(b"date-display-single", b"otra-clase")
    service.client.get_content = AsyncMock(return_value=html_sin_fecha)

    result = await service.getCurrenciesByBCV()

    assert result["date"] is None
    assert len(result["currencies"]) == 5
