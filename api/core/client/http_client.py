import httpx

from api.utils.constants.constants import Constants as c


class HttpClient:
    """Cliente HTTP asíncrono real basado en ``httpx.AsyncClient``.

    Todos los métodos son ``async`` y realizan I/O no bloqueante, de modo que
    los ``asyncio.gather(...)`` de la capa de servicios/controladores se
    resuelven realmente en paralelo (a diferencia de ``requests``, que bloquea
    el event loop).

    Cada método acepta un ``client: httpx.AsyncClient`` opcional para reutilizar
    un único cliente por request (patrón usado en los controladores). Si no se
    provee, se crea un cliente efímero por llamada.
    """

    def __init__(self, timeout: float = c.HTTP_TIMEOUT):
        self._timeout = httpx.Timeout(timeout)

    async def get(self, url, params=None, headers=None, client=None):
        response = await self._send("GET", url, client=client, params=params, headers=headers)
        return response.json()

    async def get_content(self, url, params=None, headers=None, verify=None, client=None):
        response = await self._send(
            "GET", url, client=client, params=params, headers=headers, verify=verify
        )
        return response.content

    async def post(self, url, data=None, headers=None, client=None):
        response = await self._send("POST", url, client=client, headers=headers, data=data)
        return response.json()

    async def put(self, url, data=None, headers=None, client=None):
        response = await self._send("PUT", url, client=client, headers=headers, data=data)
        return response.json()

    async def delete(self, url, data=None, headers=None, client=None):
        response = await self._send("DELETE", url, client=client, headers=headers, data=data)
        return response.json()

    async def patch(self, url, data=None, headers=None, client=None):
        response = await self._send("PATCH", url, client=client, headers=headers, data=data)
        return response.json()

    async def _send(self, method, url, *, client=None, params=None, headers=None, data=None, verify=None):
        request_kwargs = {
            "params": params,
            "headers": headers,
            "timeout": self._timeout,
        }
        request_kwargs.update(self._body_kwargs(data))

        if client is not None:
            # Reutiliza el AsyncClient compartido del request. `verify` es una
            # opción a nivel de cliente en httpx, ya fijada al construirlo.
            response = await client.request(method, url, **request_kwargs)
        else:
            # httpx expone `verify` a nivel de cliente, no por request.
            verify_flag = True if verify is None else verify
            async with httpx.AsyncClient(verify=verify_flag) as owned_client:
                response = await owned_client.request(method, url, **request_kwargs)

        response.raise_for_status()
        return response

    @staticmethod
    def _body_kwargs(data):
        # httpx distingue el form-data (dict) del contenido crudo (str/bytes,
        # p. ej. un JSON ya serializado con su propio Content-Type).
        if data is None:
            return {}
        if isinstance(data, (str, bytes)):
            return {"content": data}
        return {"data": data}
