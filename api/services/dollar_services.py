from bs4 import BeautifulSoup
import json
import httpx
import asyncio
from typing import Optional, List

from api.core.client.http_client import HttpClient
from api.core.errors.exceptions import source_guard, SourceEmptyError, SourceParsingError
from api.models.bd_currency import Currency
from api.models.market_request import (
    MarketName, MarketMode, MarketSelection,
    PLATFORM_BY_MARKET, DB_MODES, LIVE_MODES, DOLLAR_ONLY_MODES,
)
from api.services.bd_service import save_currencies_to_db, save_platform_date, get_platform_date, SessionLocal
from api.utils.constants.constants import Constants as c
from api.utils.constants.scrapping_tags import ScrappingTags as tag
from api.utils.helpers.helper import Helper
from api.core.logging.logger import get_logger

from api.services.dollar_endpoints import DollarEndpoints as endpoints

# Código del dólar (USD) usado por los modos "solo-dólar".
_USD_CODE = "USD"

# Lado del libro P2P (``tradeType`` de Binance/Bybit/OKX/Bitget) -> variante con
# la que se persiste esa serie. El acceso es directo (no ``.get`` con default) a
# propósito: un lado desconocido debe fallar de forma visible, no caer en la
# variante ``na`` y volver a colapsar compra y venta en la misma fila (#73).
_VARIANT_BY_TRADE_TYPE = {"Buy": c.VARIANT_BUY, "Sell": c.VARIANT_SELL}

logger = get_logger("services.dollar")


class DollarService:
    # Mapa plataforma -> logo. Se define una sola vez a nivel de clase (no se
    # reconstruye en cada llamada a ``serialize_with_image``, que corre por cada
    # moneda del path caliente de serialización).
    PLATFORM_IMAGES = {
        c.BCV_NAME: c.BCV_LOGO_URL,
        c.YADIO_NAME: c.YADIO_LOGO_URL,
        c.BINANCE_NAME: c.BINANCE_LOGO_URL,
        c.BYBIT_NAME: c.BYBIT_LOGO_URL,
        c.OKX_NAME: c.OKX_LOGO_URL,
        c.AIRTM_NAME: c.AIRTM_LOGO_URL,
        c.BITGET_NAME: c.BITGET_LOGO_URL,
        c.DOLARAPI_NAME: c.DOLARAPI_LOGO_URL,
        c.EXCHANGE_MONITOR_NAME: c.EXCHANGE_MONITOR_LOGO_URL,
    }

    def __init__(self):
        self.client = HttpClient()
        self.helper = Helper()

    async def getDollarValueByBCV(self):
        """Obtiene por scraping el valor oficial del dólar (USD) del BCV.

        Descarga el portal del BCV, ubica el bloque del dólar y devuelve un dict
        serializado de la moneda (con su logo). Cualquier fallo de red o de
        parseo se propaga como ``ExternalSourceError`` vía ``source_guard``.

        :return: dict serializado del dólar oficial (``serialize_with_image``).
        """
        with source_guard(c.BCV_NAME):
            content = await self.client.get_content(endpoints.OFF_MKT, verify=c.VERIFY)
            soup = BeautifulSoup(content, c.F_HTML)
            soup_target=soup.findAll(id=tag.ID_DOLAR)
            item = soup_target[0]
            getCode, getCurrency, getName  = item.find(tag.CLASS_CODE), item.find(tag.CLASS_NAME), item.attrs.get(tag.KEY_NAME)
            currency = self.createCurrency(getCode.text, getName, self.helper.formatCuValue(getCurrency.text))
            return self.serialize_with_image(currency)

    async def getCurrenciesByBCV(self):
        """Obtiene por scraping todas las tasas oficiales del BCV.

        Descarga el portal del BCV, extrae la fecha de vigencia y cada divisa
        publicada (USD, EUR, CNY, TRY, RUB) y las serializa para la respuesta
        JSON. Los fallos de red/parseo se propagan tipados vía ``source_guard``.

        :return: dict ``{"date": str | None, "currencies": list[dict]}`` con las
            monedas serializadas (incluyen su logo de plataforma).
        """
        # Reutiliza el fetch+parseo único (``get_raw_bcv_currencies``) y solo
        # añade la serialización, para no duplicar el scraping del portal.
        raw = await self.get_raw_bcv_currencies()
        return {
            "date": raw["date"],
            "currencies": [self.serialize_with_image(e) for e in raw["currencies"]],
        }

    async def getCurrenciesByYadio(self):
        """Obtiene las tasas del mercado paralelo desde la API de Yadio.io.

        Consulta las tasas de cambio de VES y devuelve el dólar (USD), el euro
        (EUR) y el bitcoin (BTC) serializados. Los fallos de red/parseo se
        propagan tipados vía ``source_guard``.

        :return: lista de dicts serializados (USD, EUR, BTC) con su logo.
        """
        # Reutiliza el fetch+mapeo único (``get_raw_yadio_currencies``) y solo
        # añade la serialización, para no duplicar la lógica de mapeo del JSON.
        currencies = await self.get_raw_yadio_currencies()
        return [self.serialize_with_image(cur) for cur in currencies]

    async def getDollarByYadio(self):
        """Obtiene solo la tasa del dólar paralelo (USD/VES) desde Yadio.io.

        Los fallos de red/parseo se propagan tipados vía ``source_guard``.

        :return: dict serializado del dólar paralelo (con su logo).
        """
        with source_guard(c.YADIO_NAME):
            response = await self.client.get(endpoints.getParMktRate("VES", "USD"))
            currency = self.createCurrency(
                    "USD",
                    "Dolar",
                    response["rate"],
                    c.YADIO_NAME
                )
            return self.serialize_with_image(currency)
    
    async def getCurrenciesByBinance(self, client: httpx.AsyncClient, asset: str = "USDT", fiat: str = "VES", tradeType: str = "Buy"):
        """Obtiene el precio promedio de un par en el mercado P2P de Binance.

        Consulta las ofertas del par ``asset``/``fiat`` para el lado indicado y
        promedia sus precios. Si no hay ofertas (lista vacía / rate-limit)
        propaga ``SourceEmptyError`` (502) en vez de dividir por cero.

        :param client: ``httpx.AsyncClient`` compartido del request (para
            resolver las peticiones realmente en paralelo).
        :param asset: activo cripto (``"USDT"`` o ``"USDC"``).
        :param fiat: moneda fiat (por defecto ``"VES"``).
        :param tradeType: lado del libro, ``"Buy"`` (compra) o ``"Sell"`` (venta).
        :return: ``Currency`` sin serializar con el precio promedio del par.
        :raises SourceEmptyError: si el par no devuelve ofertas.
        """
        dataPayload = {
            "asset": asset,
            "fiat": fiat,
            "page": 1,
            "rows": 10,
            "payTypes": [],
            "tradeType": tradeType,
            "publisherType": None
        } # "merchantCheck": False,
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json"
        }
        with source_guard(c.BINANCE_NAME):
            response = await self.client.post(endpoints.getParMktP2P(), data=json.dumps(dataPayload), headers=headers, client=client)
            advisors = response.get("data") or []
            prices = []
            for advisor in advisors:
                prices.append(float(advisor["adv"]["price"]))
            # Validamos que haya precios antes de promediar: si Binance no
            # devuelve ofertas (lista vacía, rate-limit) evitamos el
            # ZeroDivisionError y propagamos un error tipado (502) con mensaje claro.
            if not prices:
                raise SourceEmptyError(c.BINANCE_NAME)
            average = sum(prices) / len(prices)

            return self.createCurrency(
                asset,
                "{}-{}".format("Tether" if asset == "USDT" else "USD Coin", tradeType),
                average,
                c.BINANCE_NAME,
                variant=_VARIANT_BY_TRADE_TYPE[tradeType]
            )
        
    async def getCurrenciesByBybit(self, client: httpx.AsyncClient, asset: str = "USDT", fiat: str = "VES", tradeType: str = "Buy"):
        """Obtiene el precio promedio de un par en el mercado P2P de Bybit.

        Análogo a Binance: consulta las ofertas del par ``asset``/``fiat`` para
        el lado indicado y promedia sus precios. Mapea el ``tradeType``
        (``"Buy"``/``"Sell"``) al campo ``side`` de Bybit. Sin ofertas propaga
        ``SourceEmptyError`` (la degradación por par se decide más arriba, en
        ``get_raw_bybit_currencies``).

        :param client: ``httpx.AsyncClient`` compartido del request.
        :param asset: activo cripto (``"USDT"`` o ``"USDC"``).
        :param fiat: moneda fiat (por defecto ``"VES"``).
        :param tradeType: ``"Buy"`` (asks) o ``"Sell"`` (bids).
        :return: ``Currency`` sin serializar con el precio promedio del par.
        :raises SourceEmptyError: si el par no devuelve ofertas.
        """
        # Bybit expone su P2P público con `side`: "1" = Buy (asks, precio mayor),
        # "0" = Sell (bids, precio menor). Aceptamos el mismo `tradeType`
        # ("Buy"/"Sell") que Binance para mantener la simetría del controlador.
        side = "1" if tradeType == "Buy" else "0"
        dataPayload = {
            "tokenId": asset,
            "currencyId": fiat,
            "payment": [],
            "side": side,
            "size": str(c.PAGE_LIMIT),
            "page": "1",
            "amount": ""
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json"
        }
        with source_guard(c.BYBIT_NAME):
            response = await self.client.post(endpoints.getParMktBybitP2P(), data=json.dumps(dataPayload), headers=headers, client=client)
            items = (response.get("result") or {}).get("items") or []
            prices = []
            for item in items:
                prices.append(float(item["price"]))
            # Igual que Binance: sin ofertas no hay nada que promediar. Propagamos
            # un error tipado por par; la degradación (omitir pares vacíos) se
            # decide arriba, en get_raw_bybit_currencies.
            if not prices:
                raise SourceEmptyError(c.BYBIT_NAME)
            average = sum(prices) / len(prices)

            return self.createCurrency(
                asset,
                "{}-{}".format("Tether" if asset == "USDT" else "USD Coin", tradeType),
                average,
                c.BYBIT_NAME,
                variant=_VARIANT_BY_TRADE_TYPE[tradeType]
            )

    async def get_raw_bybit_currencies(self) -> List[Currency]:
        """Obtiene las tasas de Bybit (USDT/USDC Buy/Sell) con degradación elegante.

        A diferencia de Binance (todo-o-nada), el mercado P2P de Bybit en VES
        puede tener pares sin liquidez (p. ej. USDC/Buy). Omitimos los pares que
        vengan vacíos (``SourceEmptyError``) y devolvemos los que sí tienen
        ofertas; solo si **ningún** par tiene datos propagamos
        ``SourceEmptyError`` (502). Cualquier otro fallo (red, parseo) sí se
        propaga tal cual, para no enmascarar caídas reales de la fuente.
        """
        with source_guard(c.BYBIT_NAME):
            async with self.client.acquire() as client:
                tasks = [
                    self.getCurrenciesByBybit(client, "USDT", "VES", "Buy"),
                    self.getCurrenciesByBybit(client, "USDC", "VES", "Buy"),
                    self.getCurrenciesByBybit(client, "USDT", "VES", "Sell"),
                    self.getCurrenciesByBybit(client, "USDC", "VES", "Sell")
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

            currencies = []
            for res in results:
                if isinstance(res, SourceEmptyError):
                    continue  # par sin ofertas: se omite, no tumba la fuente
                if isinstance(res, BaseException):
                    raise res  # fallo real (red/parseo/timeout): se propaga
                currencies.append(res)

            if not currencies:
                raise SourceEmptyError(c.BYBIT_NAME)
            return currencies

    async def getCurrenciesByOkx(self, client: httpx.AsyncClient, asset: str = "USDT", fiat: str = "VES", tradeType: str = "Buy"):
        # OKX expone su P2P público (C2C) sin auth. El parámetro `side` es la
        # postura del anunciante: "sell" = comerciantes vendiendo cripto (el
        # usuario COMPRA) y "buy" = comerciantes comprando (el usuario VENDE).
        # Mapeamos el mismo `tradeType` ("Buy"/"Sell") que Binance/Bybit para
        # mantener la simetría del controlador.
        side = "sell" if tradeType == "Buy" else "buy"
        params = {
            "quoteCurrency": fiat,
            "baseCurrency": asset,
            "side": side,
            "paymentMethod": "all",
            "userType": "all",
            "receivingAds": "false",
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        with source_guard(c.OKX_NAME):
            response = await self.client.get(endpoints.getOkxP2P(), params=params, headers=headers, client=client)
            offers = (response.get("data") or {}).get(side) or []
            # OKX devuelve el libro completo (no acepta un `rows`/`size` como
            # Binance/Bybit); nos quedamos con las primeras PAGE_LIMIT ofertas
            # —las mejores, el libro viene ordenado— para un promedio
            # representativo del top del mercado y no de la cola.
            prices = [float(offer["price"]) for offer in offers[:c.PAGE_LIMIT]]
            # Igual que Bybit: sin ofertas no hay nada que promediar. La degradación
            # (omitir pares vacíos) se decide arriba, en get_raw_okx_currencies.
            if not prices:
                raise SourceEmptyError(c.OKX_NAME)
            average = sum(prices) / len(prices)

            return self.createCurrency(
                asset,
                "{}-{}".format("Tether" if asset == "USDT" else "USD Coin", tradeType),
                average,
                c.OKX_NAME,
                variant=_VARIANT_BY_TRADE_TYPE[tradeType]
            )

    async def get_raw_okx_currencies(self) -> List[Currency]:
        """Obtiene las tasas de OKX (USDT/USDC Buy/Sell) con degradación elegante.

        Como Bybit, el P2P de OKX en VES puede tener pares sin liquidez (p. ej.
        USDC/Buy vacío en el momento de escribir esto). Omitimos los pares que
        vengan vacíos (``SourceEmptyError``) y devolvemos los que sí tienen
        ofertas; solo si **ningún** par tiene datos propagamos
        ``SourceEmptyError`` (502). Cualquier otro fallo (red, parseo) se propaga.
        """
        with source_guard(c.OKX_NAME):
            async with self.client.acquire() as client:
                tasks = [
                    self.getCurrenciesByOkx(client, "USDT", "VES", "Buy"),
                    self.getCurrenciesByOkx(client, "USDC", "VES", "Buy"),
                    self.getCurrenciesByOkx(client, "USDT", "VES", "Sell"),
                    self.getCurrenciesByOkx(client, "USDC", "VES", "Sell")
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

            currencies = []
            for res in results:
                if isinstance(res, SourceEmptyError):
                    continue  # par sin ofertas: se omite, no tumba la fuente
                if isinstance(res, BaseException):
                    raise res  # fallo real (red/parseo/timeout): se propaga
                currencies.append(res)

            if not currencies:
                raise SourceEmptyError(c.OKX_NAME)
            return currencies

    async def getCurrenciesByBitget(self, client: httpx.AsyncClient, asset: str = "USDT", fiat: str = "VES", tradeType: str = "Buy"):
        # Bitget expone su P2P público vía POST. `side`: 1 = el usuario COMPRA
        # (precio mayor, asks) y 2 = el usuario VENDE (precio menor, bids).
        # Aceptamos el mismo `tradeType` ("Buy"/"Sell") que Binance/Bybit/OKX
        # para mantener la simetría del controlador.
        side = 1 if tradeType == "Buy" else 2
        dataPayload = {
            "side": side,
            "pageNo": 1,
            "pageSize": c.PAGE_LIMIT,
            "coinCode": asset,
            "fiatCode": fiat,
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json"
        }
        with source_guard(c.BITGET_NAME):
            response = await self._bitget_post_with_retry(dataPayload, headers, client)
            items = (response.get("data") or {}).get("dataList") or []
            prices = [float(item["price"]) for item in items]
            # Igual que Bybit/OKX: sin ofertas no hay nada que promediar. La
            # degradación (omitir pares vacíos) se decide en get_raw_bitget_currencies.
            if not prices:
                raise SourceEmptyError(c.BITGET_NAME)
            average = sum(prices) / len(prices)

            return self.createCurrency(
                asset,
                "{}-{}".format("Tether" if asset == "USDT" else "USD Coin", tradeType),
                average,
                c.BITGET_NAME,
                variant=_VARIANT_BY_TRADE_TYPE[tradeType]
            )

    async def _bitget_post_with_retry(self, dataPayload, headers, client):
        """POST al P2P de Bitget reintentando ante 429 (rate limit por ráfaga).

        Bitget devuelve ``429 Too Many Requests`` con facilidad. Reintenta hasta
        ``BITGET_MAX_RETRIES`` veces con backoff exponencial, respetando la
        cabecera ``Retry-After`` si el servidor la envía. Si el 429 persiste tras
        los reintentos, deja propagar el ``HTTPStatusError`` para que
        ``source_guard`` lo traduzca a un 502 tipado.
        """
        for attempt in range(c.BITGET_MAX_RETRIES + 1):
            try:
                return await self.client.post(
                    endpoints.getBitgetP2P(), data=json.dumps(dataPayload), headers=headers, client=client
                )
            except httpx.HTTPStatusError as e:
                is_429 = e.response.status_code == c.HTTP_TOO_MANY_REQUESTS
                if not is_429 or attempt == c.BITGET_MAX_RETRIES:
                    raise
                retry_after = e.response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else c.BITGET_RETRY_BACKOFF * (2 ** attempt)
                except (TypeError, ValueError):
                    delay = c.BITGET_RETRY_BACKOFF * (2 ** attempt)
                await asyncio.sleep(delay)

    async def get_raw_bitget_currencies(self) -> List[Currency]:
        """Obtiene las tasas de Bitget (USDT/USDC Buy/Sell) con degradación elegante.

        A diferencia de las otras fuentes cripto, los 4 pares de Bitget se piden
        **en serie** (no en ráfaga concurrente): su rate limit devuelve 429 ante
        4 requests simultáneos al mismo endpoint. Cada request, además, reintenta
        ante 429 (ver ``_bitget_post_with_retry``). Como Bybit/OKX, el P2P puede
        tener pares sin liquidez: omitimos los vacíos (``SourceEmptyError``) y solo
        si **ningún** par tiene datos propagamos ``SourceEmptyError`` (502).
        Cualquier otro fallo (red, parseo, 429 persistente) se propaga.
        """
        pairs = [("USDT", "Buy"), ("USDC", "Buy"), ("USDT", "Sell"), ("USDC", "Sell")]
        with source_guard(c.BITGET_NAME):
            currencies = []
            async with self.client.acquire() as client:
                for asset, tradeType in pairs:
                    try:
                        currencies.append(
                            await self.getCurrenciesByBitget(client, asset, "VES", tradeType)
                        )
                    except SourceEmptyError:
                        continue  # par sin ofertas: se omite, no tumba la fuente

            if not currencies:
                raise SourceEmptyError(c.BITGET_NAME)
            return currencies

    def average_by_asset(self, currencies: List[Currency], platform: str) -> List[Currency]:
        """Promedia por activo las tasas disponibles de una plataforma cripto.

        Agrupa por ``code`` (USDT, USDC) y promedia los valores presentes. Con
        ambos lados (Buy/Sell) equivale a (compra+venta)/2; si solo hay un lado
        (par vacío en Bybit), usa el disponible. Devuelve entidades limpias.
        """
        groups = {}
        for cur in currencies:
            groups.setdefault(cur.code, []).append(cur.value)

        averaged = []
        for code, values in groups.items():
            name = "Tether" if code == "USDT" else "USD Coin" if code == "USDC" else "Dolar" if code == "USD" else code
            # El promedio es su propia serie: no es la compra ni la venta, así
            # que se persiste aparte de ellas y no las sobreescribe.
            averaged.append(self.createCurrency(code, name, sum(values) / len(values), platform, variant=c.VARIANT_AVERAGE))
        return averaged

    def _airtm_currencies_from_response(self, response) -> List[Currency]:
        """Extrae las tasas USD/VES del JSON público de Airtm (rates.airtm.io).

        La respuesta es ``{"data": {"ves/usd": {"addValue": .., "withdrawValue": ..}}}``.
        ``addValue`` es la tasa para *agregar* fondos (comprar USD pagando VES →
        Buy) y ``withdrawValue`` la de *retirar* (vender USD → VES → Sell). Si el
        par ``ves/usd`` falta o viene incompleto, propagamos ``SourceEmptyError``
        (502) igual que el resto de fuentes, en vez de romper con KeyError/None.
        """
        pair = ((response or {}).get("data") or {}).get("ves/usd") or {}
        buy, sell = pair.get("addValue"), pair.get("withdrawValue")
        if buy is None or sell is None:
            raise SourceEmptyError(c.AIRTM_NAME)
        return [
            self.createCurrency("USD", "Dolar-Buy", float(buy), c.AIRTM_NAME, variant=c.VARIANT_BUY),
            self.createCurrency("USD", "Dolar-Sell", float(sell), c.AIRTM_NAME, variant=c.VARIANT_SELL),
        ]

    async def getCurrenciesByAirtm(self):
        """Tasas de compra/venta del dólar (USD/VES) según Airtm, serializadas."""
        with source_guard(c.AIRTM_NAME):
            response = await self.client.get(endpoints.getAirtmRates())
            return [self.serialize_with_image(cur) for cur in self._airtm_currencies_from_response(response)]

    async def get_raw_airtm_currencies(self) -> List[Currency]:
        """Obtiene las tasas USD/VES de Airtm como lista de Currency sin serializar."""
        with source_guard(c.AIRTM_NAME):
            response = await self.client.get(endpoints.getAirtmRates())
            return self._airtm_currencies_from_response(response)

    async def _fetch_exchange_monitor_payload(self) -> dict:
        """Obtiene el JSON de tasas de Exchange Monitor (scraping híbrido).

        El sitio no expone API pública ni sirve las tasas en el HTML estático
        (los contenedores llegan vacíos y se rellenan por JavaScript). El flujo,
        que replica lo que hace el navegador, es:

        1. GET a la página: entrega la cookie de sesión (PHPSESSID) y, en un
           ``<meta name="csrf-token">``, el token CSRF. El token se extrae con
           BeautifulSoup usando selectores centralizados en ``ScrappingTags``.
        2. POST al endpoint de datos con ese token (header ``X-CSRF-Token``),
           reutilizando el **mismo** ``httpx.AsyncClient`` para conservar la
           cookie, más ``Referer``/``Origin`` (el backend rechaza con 403 sin
           ellos). Devuelve el JSON con la lista de mercados.

        No abre ``source_guard`` aquí: lo hacen los métodos públicos que lo
        invocan. Los fallos de red/HTTP los traduce ese guard; aquí solo se
        lanzan errores tipados de parseo/vacío cuando la estructura no cuadra.
        """
        # Exchange Monitor usa su PROPIO cliente efímero (no el compartido de la
        # app): el flujo CSRF depende de la cookie de sesión PHPSESSID emitida en
        # el paso 1 y consumida en el paso 2; un cliente compartido acumularía
        # cookies entre requests y podría corromper el handshake CSRF.
        async with httpx.AsyncClient(
            headers={"User-Agent": c.EM_USER_AGENT},
            follow_redirects=True,
        ) as client:
            html = await self.client.get_content(endpoints.EXCHANGE_MONITOR_PAGE, client=client)
            soup = BeautifulSoup(html, c.F_HTML)
            meta = soup.find(tag.META_TAG, attrs={tag.KEY_META_NAME: tag.CSRF_META_NAME})
            token = meta.attrs.get(tag.KEY_CONTENT) if meta else None
            if not token:
                raise SourceParsingError(c.EXCHANGE_MONITOR_NAME, detail="token CSRF ausente en el HTML")

            headers = {
                "X-CSRF-Token": token,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": endpoints.EXCHANGE_MONITOR_PAGE,
                "Origin": endpoints.EXCHANGE_MONITOR_ORIGIN,
                "Accept": c.EM_ACCEPT,
            }
            payload = await self.client.post(
                endpoints.getExchangeMonitorData(),
                data={c.EM_TIMEZONE_KEY: c.EM_TIMEZONE},
                headers=headers,
                client=client,
            )

        if not payload.get(c.EM_KEY_SUCCESS) or not payload.get(c.EM_KEY_DATA):
            # Respuesta 200 pero sin datos utilizables (403 lógico, sin mercados).
            raise SourceEmptyError(c.EXCHANGE_MONITOR_NAME)
        return payload

    def _build_exchange_monitor_currency(self, item: dict) -> Currency:
        """Convierte una entrada del JSON de Exchange Monitor en un ``Currency``.

        El ``code`` se deriva del id del sitio sin su prefijo de país
        (``ve-em`` → ``em``); el nombre usa la variante larga si existe.
        """
        raw_id = item.get(c.EM_KEY_ID) or c.EMPTY_STRING
        code = raw_id[len(c.EM_ID_PREFIX):] if raw_id.startswith(c.EM_ID_PREFIX) else raw_id
        name = item.get(c.EM_KEY_NAME_LARGE) or item.get(c.EM_KEY_NAME) or code
        value = self.helper.formatCuValue(item.get(c.EM_KEY_RATE, "0"))
        return self.createCurrency(code, name, value, c.EXCHANGE_MONITOR_NAME)

    async def getCurrenciesByExchangeMonitor(self):
        """Tasas en vivo de Exchange Monitor: valor propio + promedio + mercados.

        Devuelve todas las entradas que reporta el sitio (incluidos el valor
        propio ``em`` y el ``promedio`` estimado) serializadas, junto con la
        fecha de actualización del sitio. Es el análogo a ``getCurrenciesByBCV``.
        """
        with source_guard(c.EXCHANGE_MONITOR_NAME):
            payload = await self._fetch_exchange_monitor_payload()
            date_str = (payload.get(c.EM_KEY_SETTINGS) or {}).get(c.EM_KEY_DATE)
            currencies = [self._build_exchange_monitor_currency(item) for item in payload[c.EM_KEY_DATA]]
            serialized = [self.serialize_with_image(cur) for cur in currencies]
            return {"date": date_str, "currencies": serialized}

    async def get_raw_exchange_monitor_currencies(self) -> dict:
        """Tasas de Exchange Monitor para persistir: solo valor propio + promedio.

        A diferencia del endpoint en vivo (que devuelve todos los mercados), la
        persistencia guarda únicamente las dos señales propias de la plataforma:
        el valor propio del sitio (``em``) y el promedio estimado (``average``).
        Devuelve ``{date, currencies}`` como BCV para que el controlador guarde
        también la fecha de la plataforma.
        """
        with source_guard(c.EXCHANGE_MONITOR_NAME):
            payload = await self._fetch_exchange_monitor_payload()
            date_str = (payload.get(c.EM_KEY_SETTINGS) or {}).get(c.EM_KEY_DATE)
            wanted = {c.EM_ID_OWN, c.EM_ID_AVERAGE}
            currencies = [
                self._build_exchange_monitor_currency(item)
                for item in payload[c.EM_KEY_DATA]
                if item.get(c.EM_KEY_ID) in wanted
            ]
            if not currencies:
                raise SourceEmptyError(c.EXCHANGE_MONITOR_NAME)
            return {"date": date_str, "currencies": currencies}

    async def getSavedCurrencies(self, platforms: Optional[List[str]] = None):
        """Recupera de la base de datos las últimas tasas guardadas.

        La lectura de la BD es síncrona/bloqueante (SQLAlchemy ORM), por lo que
        se delega a un hilo con ``run_in_executor`` para no bloquear el event
        loop, en consonancia con el resto de accesos a BD del service
        (``save_currencies_to_db_async``, ``calculate_live_changes``).

        :param platforms: lista opcional de plataformas por las que filtrar
            (p. ej. ``[Constants.BCV_NAME]``). Si es ``None`` o vacía, devuelve
            las monedas de todas las plataformas.
        :return: lista de dicts serializados (con ``id`` y logo de plataforma);
            lista vacía si ocurre un error de lectura.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._fetch_saved_currencies, platforms)

    def _fetch_saved_currencies(self, platforms: Optional[List[str]] = None) -> List[dict]:
        """Lee de forma bloqueante las últimas tasas guardadas (para ``run_in_executor``).

        Toda la interacción con la sesión de SQLAlchemy —consulta, filtrado y
        serialización de las filas— ocurre dentro de este método para que se
        ejecute íntegramente en el hilo del executor y antes de cerrar la
        sesión (evita lazy-loads sobre objetos ya desligados).

        :param platforms: mismas semánticas que ``getSavedCurrencies``.
        :return: lista de dicts serializados; lista vacía ante un error de lectura.
        """
        session = SessionLocal()
        try:
            rows = self._query_latest_rows(session, platforms=platforms)
            return self._serialize_rows(rows)
        except Exception:
            logger.exception("Error al obtener las monedas guardadas de la BD")
            return []
        finally:
            session.close()

    def _query_latest_rows(self, session, platforms=None, dollar_only=False):
        """Consulta la fila viva de cada ``(code, platform, variant)``, filtrando en SQL.

        Empuja a la consulta (issue #46) el filtro por plataforma y el de
        solo-dólar, para no traer toda la tabla ni filtrar en Python.

        Ya no hace falta la subconsulta ``max(id)`` que antes resolvía "la última
        por ``(code, platform)``": desde #73 la identidad de negocio incluye la
        variante y el ``UNIQUE (code, platform, variant)`` garantiza **una sola**
        fila viva por clave. Aquella subconsulta, además, elegía el ``id`` más
        alto mientras el upsert escribía en el más bajo, así que ante filas
        gemelas devolvía justamente la que nadie estaba actualizando.

        :param session: sesión SQLAlchemy activa.
        :param platforms: lista de plataformas por las que filtrar (o ``None``).
        :param dollar_only: si ``True``, solo filas del dólar (``code == "USD"``).
        :return: filas ``Currency`` (una por code+platform+variant).
        """
        query = session.query(Currency)
        if platforms:
            query = query.filter(Currency.platform.in_(platforms))
        if dollar_only:
            query = query.filter(Currency.code == _USD_CODE)
        return query.order_by(Currency.id.desc()).all()

    def _serialize_rows(self, rows) -> List[dict]:
        """Serializa filas ``Currency`` de BD añadiendo su ``id`` y logo."""
        result = []
        for r in rows:
            serialized_data = self.serialize_with_image(r)
            serialized_data['id'] = r.id  # Añadimos el ID que no está en to_dict()
            result.append(serialized_data)
        return result

    def _fetch_saved_for_platform(self, platform: str, dollar_only: bool = False) -> List[dict]:
        """Lee de BD la última tasa por code de UNA plataforma (filtros en SQL).

        Usado por la máquina de estados de ``saved-currencies`` (#71): los modos
        ``bd-todas`` / ``bd-solo-dolar`` mapean a ``dollar_only`` False/True.
        """
        session = SessionLocal()
        try:
            rows = self._query_latest_rows(session, platforms=[platform], dollar_only=dollar_only)
            return self._serialize_rows(rows)
        except Exception:
            logger.exception("Error al leer de BD la plataforma %s", platform)
            return []
        finally:
            session.close()

    # ------------------------------------------------------------------
    #  Máquina de estados por mercado (Body de update/saved) — issue #71
    # ------------------------------------------------------------------
    def _raw_fetcher_for(self, market: MarketName):
        """Devuelve la corrutina de fetch en vivo (``get_raw_*``) de un mercado."""
        return {
            MarketName.BCV: self.get_raw_bcv_currencies,
            MarketName.YADIO: self.get_raw_yadio_currencies,
            MarketName.BINANCE: self.get_raw_binance_currencies,
            MarketName.BYBIT: self.get_raw_bybit_currencies,
            MarketName.OKX: self.get_raw_okx_currencies,
            MarketName.BITGET: self.get_raw_bitget_currencies,
            MarketName.AIRTM: self.get_raw_airtm_currencies,
            MarketName.DOLARAPI: self.get_raw_dolarapi_currencies,
            MarketName.EXCHANGE_MONITOR: self.get_raw_exchange_monitor_currencies,
        }[market]

    async def _live_market(self, market: MarketName, mode: MarketMode):
        """Fetch en vivo de un mercado y filtrado según su modo.

        :return: tupla ``(currencies, date)`` — ``Currency`` ya filtradas según el
            modo y la fecha de plataforma (solo BCV/EM la traen; el resto ``None``).
        """
        raw = await self._raw_fetcher_for(market)()
        # BCV y Exchange Monitor devuelven {date, currencies}; el resto, lista.
        if isinstance(raw, dict):
            currencies = raw.get("currencies", [])
            date = raw.get("date")
        else:
            currencies = raw
            date = None

        platform = PLATFORM_BY_MARKET[market]
        if mode == MarketMode.AVERAGE:
            currencies = self.average_by_asset(currencies, platform)
        elif mode == MarketMode.LIVE_DOLLAR:
            currencies = [cur for cur in currencies if cur.code == _USD_CODE]
        elif mode == MarketMode.EM_OWN:
            currencies = [cur for cur in currencies if cur.code == c.EM_CODE_OWN]
        # LIVE_ALL / BOTH / EM_OWN_MONITOR: se usan tal cual (el raw de EM ya
        # acota a valor propio + promedio).
        return currencies, date

    async def update_from_selection(self, selection: MarketSelection) -> dict:
        """Persiste en BD lo que indica el Body por mercado (modos en vivo).

        Solo los modos en vivo aplican a la actualización (persistir datos
        frescos); los modos de BD no tienen sentido aquí (el controlador los
        rechaza antes). Ejecuta los fetch en paralelo, persiste las monedas y las
        fechas de plataforma (BCV/EM), y devuelve el conteo persistido.
        """
        live = [(m, mode) for m, mode in selection.active().items() if mode in LIVE_MODES]
        if not live:
            return {"message": "No se seleccionó ninguna fuente en vivo para actualizar.", "updated_count": 0}

        results = await asyncio.gather(*(self._live_market(m, mode) for m, mode in live))

        all_currencies = []
        for (market, _mode), (currencies, date) in zip(live, results):
            all_currencies.extend(currencies)
            if date:
                await self.save_platform_date_async(PLATFORM_BY_MARKET[market], date)

        if not all_currencies:
            return {"message": "No se obtuvieron datos de las fuentes seleccionadas.", "updated_count": 0}

        return await self.save_currencies_to_db_async(all_currencies)

    async def read_from_selection(self, selection: MarketSelection) -> List[dict]:
        """Lee/devuelve lo que indica el Body por mercado (BD y/o en vivo).

        - Modos ``bd-*``: leen de BD (última fila por code+platform, filtros en SQL).
        - Modos en vivo: hacen fetch, calculan el ROC vs BD y serializan.
        Concatena ambos orígenes en una sola lista serializada.
        """
        active = selection.active()
        results = []

        # 1) Lecturas de BD (una consulta acotada por mercado, filtros en SQL).
        loop = asyncio.get_running_loop()
        for market, mode in active.items():
            if mode in DB_MODES:
                dollar_only = mode in DOLLAR_ONLY_MODES
                rows = await loop.run_in_executor(
                    None, self._fetch_saved_for_platform, PLATFORM_BY_MARKET[market], dollar_only
                )
                results.extend(rows)

        # 2) Lecturas en vivo (fetch + ROC vs BD + serialización).
        live = [(m, mode) for m, mode in active.items() if mode in LIVE_MODES]
        if live:
            fetched = await asyncio.gather(*(self._live_market(m, mode) for m, mode in live))
            live_currencies = []
            for currencies, _date in fetched:
                live_currencies.extend(currencies)
            if live_currencies:
                processed = await self.calculate_live_changes(live_currencies)
                results.extend(self.serialize_with_image(cur) for cur in processed)

        return results

    async def get_stored_bcv_data(self):
        """Retorna las monedas guardadas del BCV junto con la fecha almacenada."""
        loop = asyncio.get_running_loop()
        
        currencies = await self.getSavedCurrencies(platforms=[c.BCV_NAME])
        date_str = await loop.run_in_executor(None, get_platform_date, c.BCV_NAME)
        
        return {"date": date_str, "currencies": currencies}
         
    
    async def get_raw_bcv_currencies(self) -> List[Currency]:
        """Obtiene las tasas del BCV y devuelve una lista de objetos Currency sin serializar."""
        with source_guard(c.BCV_NAME):
            url = await self.client.get_content(endpoints.OFF_MKT, verify=c.VERIFY)
            elements = []
            soup = BeautifulSoup(url, c.F_HTML)

            date_elements = soup.findAll(class_=tag.CLASS_DATE)
            date_str = date_elements[0].attrs.get(tag.KEY_DATE) if date_elements else None

            currencies_soup = soup.findAll(class_=tag.CLASS_CURRENCY)
            for item in currencies_soup:
                getCode, getCurrency, getName = item.find(tag.CLASS_CODE), item.find(tag.CLASS_NAME), item.attrs.get(tag.KEY_NAME)
                elements.append(
                    self.createCurrency(
                        getCode.text,
                        getName,
                        self.helper.formatCuValue(getCurrency.text)
                    )
                )
            return {"date": date_str, "currencies": elements}

    async def get_raw_yadio_currencies(self) -> List[Currency]:
        """Obtiene las tasas de Yadio y devuelve una lista de objetos Currency sin serializar."""
        with source_guard(c.YADIO_NAME):
            response = await self.client.get(endpoints.getParMktExRate("VES"))
            currencies = [
                self.createCurrency("USD", "Dolar", response["VES"]["VES"] / response["VES"]["USD"], c.YADIO_NAME),
                self.createCurrency("EUR", "Euro", response["VES"]["VES"] / response["VES"]["EUR"], c.YADIO_NAME),
                self.createCurrency("BTC", "Bitcoin", response["BTC"], c.YADIO_NAME)
            ]
            return currencies

    def _dolarapi_currencies_from_response(self, response) -> List[Currency]:
        """Construye las tasas USD/VES desde el JSON de DolarAPI (ve.dolarapi.com).

        La respuesta es una lista de entradas por fuente (``oficial``,
        ``paralelo``, ...). Usamos ``promedio`` como valor; si viniera nulo,
        promediamos ``compra``/``venta`` disponibles. El nombre distingue la
        fuente (Oficial/Paralelo). Si ninguna entrada trae un valor usable,
        propagamos ``SourceEmptyError`` (502), igual que el resto de fuentes.
        """
        currencies = []
        for entry in (response or []):
            value = entry.get("promedio")
            if value is None:
                sides = [v for v in (entry.get("compra"), entry.get("venta")) if v is not None]
                value = sum(sides) / len(sides) if sides else None
            if value is None:
                continue
            name = entry.get("fuente") or entry.get("nombre") or "USD"
            # DolarAPI publica varias fuentes (oficial, paralelo, ...) bajo el
            # mismo `moneda` ("USD"), así que la fuente ES la variante: sin ella
            # todas colapsarían en la misma fila. Se deriva del payload en vez de
            # mapearla contra una lista cerrada, para que una fuente nueva de
            # DolarAPI estrene su propia fila en lugar de pisar a otra.
            variant = (entry.get("fuente") or c.EMPTY_STRING).strip().lower() or c.VARIANT_NA
            currencies.append(
                self.createCurrency(entry.get("moneda") or "USD", name, float(value), c.DOLARAPI_NAME, variant=variant)
            )
        if not currencies:
            raise SourceEmptyError(c.DOLARAPI_NAME)
        return currencies

    async def getCurrenciesByDolarApi(self):
        """Tasas del dólar oficial y paralelo (USD/VES) de DolarAPI, serializadas."""
        with source_guard(c.DOLARAPI_NAME):
            response = await self.client.get(endpoints.getDolarApiRates())
            return [self.serialize_with_image(cur) for cur in self._dolarapi_currencies_from_response(response)]

    async def get_raw_dolarapi_currencies(self) -> List[Currency]:
        """Obtiene las tasas de DolarAPI como lista de Currency sin serializar."""
        with source_guard(c.DOLARAPI_NAME):
            response = await self.client.get(endpoints.getDolarApiRates())
            return self._dolarapi_currencies_from_response(response)

    async def get_raw_binance_currencies(self) -> List[Currency]:
        """Obtiene las 4 tasas de Binance (USDT/USDC Buy/Sell) y devuelve una lista de objetos Currency."""
        with source_guard(c.BINANCE_NAME):
            async with self.client.acquire() as client:
                tasks = [
                    self.getCurrenciesByBinance(client, "USDT", "VES", "Buy"),
                    self.getCurrenciesByBinance(client, "USDC", "VES", "Buy"),
                    self.getCurrenciesByBinance(client, "USDT", "VES", "Sell"),
                    self.getCurrenciesByBinance(client, "USDC", "VES", "Sell")
                ]
                binance_currencies = await asyncio.gather(*tasks)
                return list(binance_currencies)

    async def save_currencies_to_db_async(self, currencies: List[Currency]):
        """Guarda una lista de monedas en la base de datos de forma asíncrona."""
        if not currencies:
            return {"message": "No currencies provided to save.", "updated_count": 0}
        
        loop = asyncio.get_running_loop()
        # save_currencies_to_db es una función síncrona bloqueante
        await loop.run_in_executor(None, save_currencies_to_db, currencies)
        
        return {"message": f"Successfully processed {len(currencies)} currencies for DB update.", "updated_count": len(currencies)}

    async def save_platform_date_async(self, platform: str, date_value: str):
        """Guarda la fecha de la plataforma en la base de datos de forma asíncrona."""
        if not date_value:
            return
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, save_platform_date, platform, date_value)

    async def calculate_live_changes(self, currencies: List[Currency]) -> List[Currency]:
        """Calcula el ROC para una lista de monedas en vivo comparando con la BD.

        Precarga los valores previos almacenados en **una sola** consulta
        (``IN`` sobre ``code`` y ``platform``) antes del bucle, en lugar de una
        consulta por moneda (patrón N+1). El número de queries es constante e
        independiente de la cantidad de monedas. El ROC se calcula reutilizando
        el helper único ``Helper.rate_of_change``.
        """
        if not currencies:
            return []

        loop = asyncio.get_running_loop()
        def _calc():
            session = SessionLocal()
            try:
                # Códigos y plataformas del lote en vivo. Se filtran ambos en
                # SQL (una sola consulta, portable entre SQLite y PostgreSQL);
                # la clave exacta se resuelve luego con el dict.
                codes = {cur.code for cur in currencies}
                platforms = {cur.platform for cur in currencies}
                rows = (
                    session.query(Currency.code, Currency.platform, Currency.variant, Currency.value)
                    .filter(Currency.code.in_(codes), Currency.platform.in_(platforms))
                    .order_by(Currency.id.asc())
                    .all()
                )
                # Mapa (code, platform, variant) -> valor previo. La variante entra
                # en la clave para que cada serie compare contra la suya: sin ella,
                # la compra de un P2P calculaba su ROC contra la venta guardada.
                previous_by_key = {
                    (code, platform, variant): value for code, platform, variant, value in rows
                }

                for cur in currencies:
                    previous = previous_by_key.get((cur.code, cur.platform, cur.variant))
                    cur.change = self.helper.rate_of_change(previous, cur.value)
                return currencies
            finally:
                session.close()
        return await loop.run_in_executor(None, _calc)

    def createCurrency(self, code: str = c.EMPTY_STRING, name: str = c.EMPTY_STRING, value:float = 0.0, platform: str = c.BCV_NAME, change: float = 0.0, variant: str = c.VARIANT_NA) -> Currency:
        """Construye una entidad ``Currency`` normalizando sus campos de texto.

        Recorta el ``code``, capitaliza el ``name`` y sella las fechas de
        creación/actualización con la hora de Caracas. Es la fábrica central de
        monedas usada por todas las fuentes.

        :param code: código de la moneda (p. ej. ``"USD"``, ``"USDT"``).
        :param name: nombre legible de la moneda.
        :param value: valor de la tasa en VES.
        :param platform: plataforma de origen (por defecto el BCV).
        :param change: variación porcentual (ROC); ``0.0`` si no aplica.
        :param variant: serie de la cotización dentro de ``(code, platform)``
            (``buy``, ``sell``, ``average``, ``oficial``, ``paralelo``). El
            default ``na`` corresponde a las fuentes que publican una sola serie
            por moneda (BCV, Yadio, Exchange Monitor).
        :return: instancia ``Currency`` lista para serializar o persistir.
        """
        # Una única fuente de tiempo (self.helper), reutilizada para ambas
        # fechas, en lugar de instanciar Helper() dos veces por moneda.
        now = self.helper.getZoneTime()
        return Currency(
            code=code.strip(),
            name=name.strip().capitalize(),
            platform=platform,
            variant=variant,
            value=value,
            change=change,
            createDate=now,
            updateDate=now
        )

    def serialize_with_image(self, currency: Currency) -> dict:
        """Serializa el objeto Currency y añade el link de la imagen de la plataforma."""
        data = currency.to_dict()
        data['platform_img'] = self.PLATFORM_IMAGES.get(currency.platform, "")
        return data