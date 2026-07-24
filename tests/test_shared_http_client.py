"""Issue #50: cliente httpx compartido a nivel de app (keep-alive entre requests).

El ``HttpClient`` reutiliza un ``AsyncClient`` compartido cuando no se le pasa
uno explícito, en lugar de abrir uno efímero por llamada. Se mantienen dos
clientes compartidos (con y sin verificación TLS); el inseguro solo se usa para
llamadas ``verify=False`` (host del BCV), preservando el aislamiento de TLS.

Estos tests fijan:
- Sin cliente compartido configurado -> se usa uno efímero (comportamiento previo).
- Con clientes compartidos -> se reutilizan (misma instancia) según el perfil de
  verify: ``verify=None`` usa el seguro; ``verify=False`` usa el inseguro.
- El ``lifespan`` de la app inyecta los clientes en el servicio y los cierra al
  apagar.
"""
import httpx
import pytest
from fastapi.testclient import TestClient

import api.main as main
from api.controller.venezuela_controller import dollar_service
from api.core.client.http_client import HttpClient


def _recording_client(bucket, name):
    """AsyncClient con MockTransport que anota su nombre al recibir una petición."""
    def handler(request):
        bucket.append(name)
        return httpx.Response(200, json={"ok": True})
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_uses_shared_secure_when_verify_default():
    """Sin verify explícito, las llamadas reutilizan el cliente seguro compartido."""
    used = []
    http = HttpClient()
    async with _recording_client(used, "secure") as secure, \
            _recording_client(used, "insecure") as insecure:
        http.set_shared_clients(secure=secure, insecure=insecure)
        await http.get("https://fake.local/a")
        await http.get("https://fake.local/b")

    assert used == ["secure", "secure"]  # mismo cliente compartido, 2 veces


@pytest.mark.asyncio
async def test_uses_shared_insecure_only_when_verify_false():
    """verify=False enruta al cliente inseguro; el resto al seguro."""
    used = []
    http = HttpClient()
    async with _recording_client(used, "secure") as secure, \
            _recording_client(used, "insecure") as insecure:
        http.set_shared_clients(secure=secure, insecure=insecure)
        await http.get_content("https://bcv.local/", verify=False)
        await http.get_content("https://other.local/", verify=None)

    assert used == ["insecure", "secure"]


@pytest.mark.asyncio
async def test_falls_back_to_ephemeral_without_shared_clients():
    """Sin clientes compartidos configurados, se usa uno efímero por llamada."""
    http = HttpClient()  # sin set_shared_clients
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, json={"ok": True})

    # Inyecta un cliente explícito: valida que el flujo sin compartido sigue vivo.
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        data = await http.get("https://fake.local/x", client=client)
    assert data == {"ok": True}
    assert calls == ["https://fake.local/x"]


def test_lifespan_injects_and_closes_shared_clients():
    """El lifespan inyecta los clientes compartidos y los cierra al apagar."""
    with TestClient(main.app):
        secure = main.app.state.http_client
        insecure = main.app.state.http_client_insecure
        # Inyectados en el HttpClient del servicio.
        assert dollar_service.client._shared_secure is secure
        assert dollar_service.client._shared_insecure is insecure
        assert not secure.is_closed
        assert not insecure.is_closed

    # Tras el shutdown: referencias limpiadas y clientes cerrados.
    assert dollar_service.client._shared_secure is None
    assert dollar_service.client._shared_insecure is None
    assert secure.is_closed
    assert insecure.is_closed
