import json
from contextlib import asynccontextmanager

import httpx

from api.utils.constants.constants import Constants as c


class HttpClient:
    """Cliente HTTP asíncrono real basado en ``httpx.AsyncClient``.

    Todos los métodos son ``async`` y realizan I/O no bloqueante, de modo que
    los ``asyncio.gather(...)`` de la capa de servicios/controladores se
    resuelven realmente en paralelo (a diferencia de ``requests``, que bloquea
    el event loop).

    Cada método acepta un ``client: httpx.AsyncClient`` opcional para reutilizar
    un único cliente por request. Si no se provee, se usa el **cliente
    compartido a nivel de app** (keep-alive entre requests, ver
    ``set_shared_clients`` y el ``lifespan`` de ``api/main.py``); si tampoco hay
    cliente compartido configurado, se crea uno efímero por llamada.

    Aislamiento de TLS: se mantienen dos clientes compartidos, uno con
    verificación TLS (``verify=True``, el normal) y otro sin ella
    (``verify=False``). El inseguro solo se usa cuando la llamada pide
    explícitamente ``verify=False`` (hoy, únicamente el scraping del BCV), de
    modo que la desactivación de TLS no se filtra al resto de fuentes.
    """

    def __init__(self, timeout: float = c.HTTP_TIMEOUT):
        self._timeout = httpx.Timeout(timeout)
        # Clientes compartidos a nivel de app (los inyecta el lifespan). None
        # hasta que se configuren; en ese caso se cae a clientes efímeros.
        self._shared_secure = None
        self._shared_insecure = None

    def set_shared_clients(self, secure=None, insecure=None):
        """Registra los ``AsyncClient`` compartidos de la app (keep-alive).

        :param secure: cliente con verificación TLS (``verify=True``).
        :param insecure: cliente sin verificación TLS (``verify=False``), usado
            solo para las llamadas que piden ``verify=False`` (BCV).
        """
        self._shared_secure = secure
        self._shared_insecure = insecure

    def _shared_for(self, verify_flag):
        """Devuelve el cliente compartido adecuado según el perfil de verify."""
        if verify_flag is False:
            return self._shared_insecure
        return self._shared_secure

    @asynccontextmanager
    async def acquire(self, insecure: bool = False):
        """Cede un ``AsyncClient`` para varias peticiones concurrentes del request.

        Reutiliza el cliente compartido de la app si está configurado (no lo
        cierra: su ciclo de vida lo gobierna el ``lifespan``); si no, crea uno
        efímero y lo cierra al salir del bloque.

        :param insecure: si ``True``, usa el perfil sin verificación TLS.
        """
        shared = self._shared_insecure if insecure else self._shared_secure
        if shared is not None:
            yield shared
        else:
            async with httpx.AsyncClient(verify=(c.VERIFY if insecure else True)) as ephemeral:
                yield ephemeral

    async def get(self, url, params=None, headers=None, client=None):
        """GET que devuelve el cuerpo ya parseado como JSON.

        :param url: URL a consultar.
        :param params: query params opcionales.
        :param headers: cabeceras opcionales.
        :param client: ``httpx.AsyncClient`` a reutilizar; si es ``None`` se crea
            uno efímero por llamada.
        :return: el cuerpo de la respuesta deserializado (dict/list).
        """
        response = await self._send("GET", url, client=client, params=params, headers=headers)
        return self._parse_json(response)

    async def get_content(self, url, params=None, headers=None, verify=None, client=None):
        """GET que devuelve el cuerpo crudo en bytes (p. ej. HTML para scraping).

        :param verify: verificación TLS (solo se aplica al crear un cliente
            efímero; con ``client`` provisto se usa la del cliente).
        :param client: ``httpx.AsyncClient`` a reutilizar, u ``None`` para uno efímero.
        :return: ``response.content`` en bytes.
        """
        response = await self._send(
            "GET", url, client=client, params=params, headers=headers, verify=verify
        )
        return response.content

    async def post(self, url, data=None, headers=None, client=None):
        """POST que devuelve el cuerpo ya parseado como JSON.

        :param data: form-data (dict) o contenido crudo (str/bytes ya serializados).
        :param client: ``httpx.AsyncClient`` a reutilizar, u ``None`` para uno efímero.
        :return: el cuerpo de la respuesta deserializado.
        """
        response = await self._send("POST", url, client=client, headers=headers, data=data)
        return self._parse_json(response)

    async def put(self, url, data=None, headers=None, client=None):
        """PUT que devuelve el cuerpo ya parseado como JSON (ver :meth:`post`)."""
        response = await self._send("PUT", url, client=client, headers=headers, data=data)
        return self._parse_json(response)

    async def delete(self, url, data=None, headers=None, client=None):
        """DELETE que devuelve el cuerpo ya parseado como JSON (ver :meth:`post`)."""
        response = await self._send("DELETE", url, client=client, headers=headers, data=data)
        return self._parse_json(response)

    async def patch(self, url, data=None, headers=None, client=None):
        """PATCH que devuelve el cuerpo ya parseado como JSON (ver :meth:`post`)."""
        response = await self._send("PATCH", url, client=client, headers=headers, data=data)
        return self._parse_json(response)

    async def _send(self, method, url, *, client=None, params=None, headers=None, data=None, verify=None):
        """Ejecuta la petición HTTP y valida el estado de la respuesta.

        Reutiliza el ``client`` provisto (para peticiones concurrentes del mismo
        request) o crea uno efímero aplicando ``verify``. Lanza
        ``raise_for_status`` para que ``source_guard`` traduzca los errores.
        """
        request_kwargs = {
            "params": params,
            "headers": headers,
            "timeout": self._timeout,
        }
        request_kwargs.update(self._body_kwargs(data))

        if client is not None:
            # Reutiliza el AsyncClient explícito del request. `verify` es una
            # opción a nivel de cliente en httpx, ya fijada al construirlo.
            response = await client.request(method, url, **request_kwargs)
        else:
            # httpx expone `verify` a nivel de cliente, no por request.
            verify_flag = True if verify is None else verify
            shared = self._shared_for(verify_flag)
            if shared is not None:
                # Cliente compartido de la app (keep-alive entre requests). No
                # se cierra aquí: lo gestiona el lifespan.
                response = await shared.request(method, url, **request_kwargs)
            else:
                # Sin cliente compartido configurado: efímero por llamada.
                async with httpx.AsyncClient(verify=verify_flag) as owned_client:
                    response = await owned_client.request(method, url, **request_kwargs)

        response.raise_for_status()
        return response

    @staticmethod
    def _parse_json(response):
        """Parsea el cuerpo como JSON tolerando caracteres de control crudos.

        Algunas fuentes P2P (p. ej. Bybit) devuelven anuncios cuyo texto libre
        incluye saltos de línea/tabs **sin escapar** dentro de las cadenas JSON.
        El parseo estricto de ``response.json()`` (json.loads con ``strict=True``)
        lanzaría ``JSONDecodeError`` ante esos caracteres, tumbando la fuente de
        forma intermitente. Con ``strict=False`` se permiten dentro de strings;
        el JSON bien formado se interpreta de forma idéntica.
        """
        return json.loads(response.text, strict=False)

    @staticmethod
    def _body_kwargs(data):
        """Traduce ``data`` a los kwargs de cuerpo que espera httpx.

        Devuelve ``{"content": ...}`` para str/bytes (JSON ya serializado) o
        ``{"data": ...}`` para form-data (dict); ``{}`` si no hay cuerpo.
        """
        # httpx distingue el form-data (dict) del contenido crudo (str/bytes,
        # p. ej. un JSON ya serializado con su propio Content-Type).
        if data is None:
            return {}
        if isinstance(data, (str, bytes)):
            return {"content": data}
        return {"data": data}
