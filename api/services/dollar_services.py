from bs4 import BeautifulSoup
import json
import httpx
import asyncio
from typing import Optional, List

from api.core.client.http_client import HttpClient
from api.core.errors.exceptions import source_guard, SourceEmptyError, SourceParsingError
from api.models.bd_currency import Currency
from api.services.bd_service import save_currencies_to_db, save_platform_date, get_platform_date, SessionLocal
from api.utils.constants.constants import Constants as c
from api.utils.constants.scrapping_tags import ScrappingTags as tag
from api.utils.helpers.helper import Helper

from api.services.dollar_endpoints import DollarEndpoints as endpoints

class DollarService:
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
        with source_guard(c.BCV_NAME):
            url = await self.client.get_content(endpoints.OFF_MKT, verify=c.VERIFY)
            elements = []
            soup = BeautifulSoup(url, c.F_HTML)
            date_elements = soup.findAll(class_=tag.CLASS_DATE)
            # Extraemos el string de la fecha de forma segura
            date_str = date_elements[0].attrs.get(tag.KEY_DATE) if date_elements else None

            currencies = soup.findAll(class_=tag.CLASS_CURRENCY)
            for item in currencies:
                getCode, getCurrency, getName = item.find(tag.CLASS_CODE), item.find(tag.CLASS_NAME), item.attrs.get(tag.KEY_NAME)
                elements.append(
                    self.createCurrency(
                        getCode.text,
                        getName,
                        self.helper.formatCuValue(getCurrency.text)
                    )
                )

            # Guardamos en base de datos
            #save_currencies_to_db(elements)

            # Convertimos los objetos Currency a diccionarios serializables para JSON
            serialized_currencies = [self.serialize_with_image(e) for e in elements]

            return {"date": date_str, "currencies": serialized_currencies}

    async def getCurrenciesByYadio(self):
        """Obtiene las tasas del mercado paralelo desde la API de Yadio.io.

        Consulta las tasas de cambio de VES y devuelve el dólar (USD), el euro
        (EUR) y el bitcoin (BTC) serializados. Los fallos de red/parseo se
        propagan tipados vía ``source_guard``.

        :return: lista de dicts serializados (USD, EUR, BTC) con su logo.
        """
        with source_guard(c.YADIO_NAME):
            response = await self.client.get(endpoints.getParMktExRate("VES"))
            currencies = [ self.createCurrency(
                    "USD",
                    "Dolar",
                    response["VES"]["VES"] / response["VES"]["USD"],
                    c.YADIO_NAME
                ),
                self.createCurrency(
                    "EUR",
                    "Euro",
                    response["VES"]["VES"] / response["VES"]["EUR"],
                    c.YADIO_NAME
                ),
                self.createCurrency(
                    "BTC",
                    "Bitcoin",
                    response["BTC"],
                    c.YADIO_NAME
                )
            ]
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
                c.BINANCE_NAME
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
                c.BYBIT_NAME
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
            async with httpx.AsyncClient() as client:
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
            averaged.append(self.createCurrency(code, name, sum(values) / len(values), platform))
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
            self.createCurrency("USD", "Dolar-Buy", float(buy), c.AIRTM_NAME),
            self.createCurrency("USD", "Dolar-Sell", float(sell), c.AIRTM_NAME),
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

        :param platforms: lista opcional de plataformas por las que filtrar
            (p. ej. ``[Constants.BCV_NAME]``). Si es ``None`` o vacía, devuelve
            las monedas de todas las plataformas.
        :return: lista de dicts serializados (con ``id`` y logo de plataforma);
            lista vacía si ocurre un error de lectura.
        """
        session = SessionLocal()
        try:
            query = session.query(Currency)

            # Si se proporciona una lista de plataformas y no está vacía, filtra por ellas.
            if platforms:
                query = query.filter(Currency.platform.in_(platforms))

            rows = query.order_by(Currency.id.desc()).all()

            result = []
            for r in rows:
                serialized_data = self.serialize_with_image(r)
                serialized_data['id'] = r.id  # Añadimos el ID que no está en to_dict()
                result.append(serialized_data)
            return result
        except Exception as e:
            print(f"An error occurred while fetching saved currencies: {e}")
            return []
        finally:
            session.close()

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

    async def get_raw_binance_currencies(self) -> List[Currency]:
        """Obtiene las 4 tasas de Binance (USDT/USDC Buy/Sell) y devuelve una lista de objetos Currency."""
        with source_guard(c.BINANCE_NAME):
            async with httpx.AsyncClient() as client:
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
        """Calcula el ROC para una lista de monedas en vivo comparando con la BD."""
        if not currencies:
            return []
        
        loop = asyncio.get_running_loop()
        def _calc():
            session = SessionLocal()
            try:
                for cur in currencies:
                    existing = session.query(Currency).filter(Currency.code == cur.code, Currency.platform == cur.platform).first()
                    if existing and existing.value and existing.value != 0:
                        cur.change = ((cur.value - existing.value) / existing.value) * 100
                    else:
                        cur.change = 0.0
                return currencies
            finally:
                session.close()
        return await loop.run_in_executor(None, _calc)

    def createCurrency(self, code: str = c.EMPTY_STRING, name: str = c.EMPTY_STRING, value:float = 0.0, platform: str = c.BCV_NAME, change: float = 0.0) -> Currency:
        """Construye una entidad ``Currency`` normalizando sus campos de texto.

        Recorta el ``code``, capitaliza el ``name`` y sella las fechas de
        creación/actualización con la hora de Caracas. Es la fábrica central de
        monedas usada por todas las fuentes.

        :param code: código de la moneda (p. ej. ``"USD"``, ``"USDT"``).
        :param name: nombre legible de la moneda.
        :param value: valor de la tasa en VES.
        :param platform: plataforma de origen (por defecto el BCV).
        :param change: variación porcentual (ROC); ``0.0`` si no aplica.
        :return: instancia ``Currency`` lista para serializar o persistir.
        """
        return Currency(
            code=code.strip(),
            name=name.strip().capitalize(),
            platform=platform,
            value=value,
            change=change,
            createDate=Helper().getZoneTime(),
            updateDate=Helper().getZoneTime()
        )

    def serialize_with_image(self, currency: Currency) -> dict:
        """Serializa el objeto Currency y añade el link de la imagen de la plataforma."""
        data = currency.to_dict()
        platform_images = {
            c.BCV_NAME: c.BCV_LOGO_URL,
            c.YADIO_NAME: c.YADIO_LOGO_URL,
            c.BINANCE_NAME: c.BINANCE_LOGO_URL,
            c.BYBIT_NAME: c.BYBIT_LOGO_URL,
            c.AIRTM_NAME: c.AIRTM_LOGO_URL,
            c.EXCHANGE_MONITOR_NAME: c.EXCHANGE_MONITOR_LOGO_URL
        }
        data['platform_img'] = platform_images.get(currency.platform, "")
        return data