"""Issue #20: la capa HTTP (``HttpClient``) frente a respuestas simuladas.

Usa ``httpx.MockTransport`` para ejercer ``HttpClient`` de extremo a extremo sin
red real, cubriendo el camino feliz y los casos de error que el resto de la app
traduce a códigos semánticos (``source_guard`` -> 408/502):

- respuesta 200 con JSON -> se parsea;
- ``httpx.TimeoutException`` -> se propaga (la capa superior la mapea a 408);
- estado no-2xx -> ``raise_for_status`` lanza ``HTTPStatusError`` (mapea a 502);
- cuerpo vacío en ``get_content`` -> devuelve ``b""`` sin romper.
"""
import httpx
import pytest

from api.core.client.http_client import HttpClient


def _client(handler):
    """AsyncClient con MockTransport, inyectable en HttpClient vía ``client=``."""
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_get_parsea_json_de_una_respuesta_200():
    def handler(request):
        return httpx.Response(200, json={"rate": 402.5})

    http = HttpClient()
    async with _client(handler) as client:
        data = await http.get("https://fake.local/rate", client=client)

    assert data == {"rate": 402.5}


@pytest.mark.asyncio
async def test_timeout_se_propaga():
    def handler(request):
        raise httpx.ReadTimeout("timed out", request=request)

    http = HttpClient()
    async with _client(handler) as client:
        with pytest.raises(httpx.TimeoutException):
            await http.get("https://fake.local/slow", client=client)


@pytest.mark.asyncio
async def test_estado_no_2xx_lanza_http_status_error():
    def handler(request):
        return httpx.Response(502, text="bad gateway")

    http = HttpClient()
    async with _client(handler) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await http.get("https://fake.local/down", client=client)


@pytest.mark.asyncio
async def test_get_content_devuelve_cuerpo_vacio_sin_romper():
    def handler(request):
        return httpx.Response(200, content=b"")

    http = HttpClient()
    async with _client(handler) as client:
        content = await http.get_content("https://fake.local/empty", client=client)

    assert content == b""
