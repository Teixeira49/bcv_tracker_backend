"""Issue #3 (DT-012): integración de Exchange Monitor como fuente de tasa.

Exchange Monitor no expone API pública ni sirve las tasas en el HTML estático
(los contenedores llegan vacíos y se rellenan por JavaScript). La integración es
un scraping híbrido: se extrae el token CSRF del ``<meta>`` con BeautifulSoup y
con él se pide el JSON de datos. Estas pruebas cubren:

- Extracción del token CSRF del HTML y envío en el header ``X-CSRF-Token``.
- El endpoint en vivo devuelve todos los mercados (valor propio + promedio + resto).
- La persistencia guarda SOLO el valor propio y el promedio estimado.
- Manejo tipado (502) cuando la respuesta no trae datos o falta el token.
"""
from unittest.mock import AsyncMock

import pytest

from api.core.errors.exceptions import (
    ExternalSourceError,
    SourceEmptyError,
    SourceParsingError,
)
from api.services.dollar_services import DollarService
from api.utils.constants.constants import Constants as c


CSRF = "a" * 64

PAGE_HTML = f"""
<html><head>
  <meta name="csrf-token" content="{CSRF}">
</head><body>
  <div class="rate-container skeleton"></div>
</body></html>
""".encode("utf-8")

# Payload representativo del endpoint /data/rates/ve (recortado).
PAYLOAD = {
    "success": True,
    "settings": {"date": "2026-07-09 00:31:09", "base_currency": "USD"},
    "data": [
        {"id": "ve-em", "name": "EM", "name_large": "Exchange Monitor", "rate": "782,74"},
        {"id": "ve-md", "name": "Monitor Dólar", "name_large": None, "rate": "823,99"},
        {"id": "ve-average", "name": "Promedio", "name_large": None, "rate": "758,58"},
        {"id": "ve-bcv", "name": "BCV", "name_large": "Banco Central de Venezuela", "rate": "700,22"},
    ],
}


def _mock_client(service, payload=PAYLOAD, html=PAGE_HTML):
    """Mockea el flujo de red: GET de la página (HTML) + POST del JSON."""
    service.client.get_content = AsyncMock(return_value=html)
    service.client.post = AsyncMock(return_value=payload)


@pytest.mark.asyncio
async def test_em_live_devuelve_todos_los_mercados():
    """El endpoint en vivo expone valor propio + promedio + el resto de mercados."""
    service = DollarService()
    _mock_client(service)

    result = await service.getCurrenciesByExchangeMonitor()

    assert result["date"] == "2026-07-09 00:31:09"
    assert len(result["currencies"]) == 4
    codes = {cur["code"] for cur in result["currencies"]}
    assert codes == {"em", "md", "average", "bcv"}
    # Todas quedan bajo la plataforma Exchange Monitor, con su logo.
    assert all(cur["platform"] == c.EXCHANGE_MONITOR_NAME for cur in result["currencies"])
    assert all(cur["platform_img"] == c.EXCHANGE_MONITOR_LOGO_URL for cur in result["currencies"])
    em = next(cur for cur in result["currencies"] if cur["code"] == "em")
    assert em["value"] == 782.74


@pytest.mark.asyncio
async def test_em_persistencia_solo_valor_propio_y_promedio():
    """La persistencia guarda únicamente el valor propio (em) y el promedio."""
    service = DollarService()
    _mock_client(service)

    result = await service.get_raw_exchange_monitor_currencies()

    codes = {cur.code for cur in result["currencies"]}
    assert codes == {"em", "average"}  # se descartan md, bcv, etc.
    assert result["date"] == "2026-07-09 00:31:09"
    assert all(cur.platform == c.EXCHANGE_MONITOR_NAME for cur in result["currencies"])


@pytest.mark.asyncio
async def test_em_envia_token_csrf_extraido_del_html():
    """El token del <meta> viaja en el header X-CSRF-Token del POST de datos."""
    service = DollarService()
    captured = {}

    service.client.get_content = AsyncMock(return_value=PAGE_HTML)

    async def fake_post(url, data=None, headers=None, client=None):
        captured["headers"] = headers or {}
        captured["data"] = data
        return PAYLOAD

    service.client.post = fake_post

    await service.getCurrenciesByExchangeMonitor()

    assert captured["headers"].get("X-CSRF-Token") == CSRF
    # La zona horaria se envía en el body, como hace el sitio.
    assert captured["data"].get(c.EM_TIMEZONE_KEY) == c.EM_TIMEZONE


@pytest.mark.asyncio
async def test_em_sin_token_lanza_parsing_error():
    """Si el HTML no trae el token CSRF, se propaga un SourceParsingError (502)."""
    service = DollarService()
    _mock_client(service, html=b"<html><head></head><body></body></html>")

    with pytest.raises(SourceParsingError) as exc_info:
        await service.getCurrenciesByExchangeMonitor()

    assert isinstance(exc_info.value, ExternalSourceError)
    assert exc_info.value.status_code == c.STATUS_BAD_GATEWAY
    assert c.EXCHANGE_MONITOR_NAME in exc_info.value.message


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"success": False, "message": "Error 403."},
    {"success": True, "data": []},
    {"success": True, "data": None},
    {},
])
async def test_em_respuesta_sin_datos_lanza_empty_error(payload):
    """Una respuesta sin datos utilizables se traduce a SourceEmptyError (502)."""
    service = DollarService()
    _mock_client(service, payload=payload)

    with pytest.raises(SourceEmptyError):
        await service.getCurrenciesByExchangeMonitor()


@pytest.mark.asyncio
async def test_em_persistencia_sin_ids_esperados_lanza_empty_error():
    """Si el JSON no trae ni el valor propio ni el promedio, la persistencia falla tipada."""
    service = DollarService()
    only_others = {
        "success": True,
        "settings": {"date": "2026-07-09"},
        "data": [{"id": "ve-md", "name": "Monitor Dólar", "name_large": None, "rate": "823,99"}],
    }
    _mock_client(service, payload=only_others)

    with pytest.raises(SourceEmptyError):
        await service.get_raw_exchange_monitor_currencies()
