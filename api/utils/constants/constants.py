class Constants:

    APP_NAME = "DolarTracker"
    
    APP_SUMMARY = "API RESTful de alto rendimiento para el monitoreo y centralización de tasas de cambio en Venezuela (BCV, Paralelo y Cripto) con procesamiento concurrente y persistencia histórica."

    APP_DESCRIPTION="""
## ¡Bienvenido a DolarTracker! 🚀
Esta API proporciona acceso en tiempo real a las tasas cambiarias de Venezuela, consolidando datos de múltiples fuentes confiables:
*   **Banco Central de Venezuela (BCV)**: Tasas oficiales.
*   **Yadio.io**: Tasas del mercado paralelo.
*   **Binance P2P**: Tasas del mercado cripto (USDT/USDC).
*   **Bybit P2P**: Tasas del mercado cripto (USDT/USDC).
*   **OKX P2P**: Tasas del mercado cripto (USDT/USDC).
*   **Bitget P2P**: Tasas del mercado cripto (USDT/USDC).
*   **Airtm**: Tasas de compra/venta del dólar (USD/VES).
*   **DolarAPI**: Agregador del dólar oficial y paralelo (USD/VES).
*   **Exchange Monitor**: Agregador de mercados (valor propio + promedio estimado + mercados que reporta).
### Características Principales:
*   **Caché inteligente**: Recuperación rápida de datos almacenados.
*   **Promediado automático**: Cálculo de valores medios en mercados volátiles.
*   **Persistencia**: Actualización masiva de la base de datos con un solo clic.
    """

    APP_LICENSE = {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }

    APP_CONTACT = {
        "name": "Teixeira49 Support",
        "url": "https://github.com/Teixeira49",
    }

    VERSION = "2.0.0"

    # Prefijo de versión del contrato de la API (versionado por path). Es
    # independiente de VERSION (versión semántica de la app / metadata OpenAPI):
    # un futuro `v2` convive con `v1` montando su propio router en paralelo.
    # Los endpoints de negocio cuelgan de aquí; la infraestructura (health,
    # docs, root) queda sin versionar.
    API_V1_STR = "/api/v1"

    EMPTY_STRING = ""

    EMPTY_SPACE = " "

    PAGE_LIMIT = 10

    F_HTML = 'html.parser'

    VERIFY = False

    HTTP_TIMEOUT = 10.0

    STATUS_OK = 200

    STATUS_OK_MSG = 'Success'

    STATUS_OK_DEATILS = 'Elemento retornado con exito'

    STATUS_NOT_FOUND = 404

    STATUS_NOT_FOUND_MSG = 'Not Found'

    STATUS_REQUEST_TIMEOUT = 408

    STATUS_REQUEST_TIMEOUT_MSG = 'Request Timeout'

    STATUS_BAD_GATEWAY = 502

    STATUS_BAD_GATEWAY_MSG = 'Bad Gateway'

    STATUS_INTERNAL_SERVER_ERROR = 500

    STATUS_INTERNAL_SERVER_ERROR_MSG = 'Internal Server Error'

    STATUS_ERROR_MSG = 'Error'

    # Mensaje genérico para errores internos no controlados (500). No expone
    # `str(exc)` al cliente para no filtrar detalles internos; el detalle real
    # se registra en el servidor.
    INTERNAL_ERROR_MSG = 'Ocurrió un error interno inesperado al procesar la solicitud.'

    # Mensajes de fallo de las fuentes externas de tasas (BCV, Yadio, Binance, Bybit, Airtm, Exchange Monitor).
    # {source} se rellena con el nombre de la plataforma afectada.
    SOURCE_TIMEOUT_MSG = 'Tiempo de espera agotado al consultar la fuente: {source}.'

    SOURCE_UNAVAILABLE_MSG = 'La fuente {source} no está disponible o respondió con un error.'

    SOURCE_PARSING_MSG = 'No se pudo interpretar la respuesta de la fuente: {source}.'

    SOURCE_EMPTY_MSG = 'La fuente {source} no devolvió ofertas disponibles.'

    BCV_NAME = 'Banco Central de Venezuela'
    
    BCV_LOGO_URL = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSOo4msUmPyGaYEjUT2wXmHvhFTAmM-5k9NbQ&s'

    YADIO_NAME = 'Yadio.io'

    YADIO_LOGO_URL = 'https://yadio.io/social/logo_sq.png'

    BINANCE_NAME = 'Binance'

    BINANCE_LOGO_URL = 'https://public.bnbstatic.com/20190405/eb2349c3-b2f8-4a93-a286-8f86a62ea9d8.png'

    BYBIT_NAME = 'Bybit'

    BYBIT_LOGO_URL = 'https://s2.coinmarketcap.com/static/img/exchanges/128x128/521.png'

    OKX_NAME = 'OKX'

    OKX_LOGO_URL = 'https://s2.coinmarketcap.com/static/img/exchanges/128x128/294.png'

    AIRTM_NAME = 'Airtm'

    AIRTM_LOGO_URL = 'https://www.google.com/s2/favicons?domain=airtm.com&sz=128'

    BITGET_NAME = 'Bitget'

    BITGET_LOGO_URL = 'https://s2.coinmarketcap.com/static/img/exchanges/128x128/513.png'

    # Bitget aplica un rate limit por ráfaga más estricto que las otras fuentes:
    # 4 requests concurrentes al mismo endpoint gatillan 429. Por eso sus pares se
    # piden en serie (no en ráfaga) y cada request reintenta ante 429 con backoff
    # exponencial (respetando `Retry-After` si viene). Ver fix DT-017.
    BITGET_MAX_RETRIES = 2

    BITGET_RETRY_BACKOFF = 0.5

    HTTP_TOO_MANY_REQUESTS = 429

    DOLARAPI_NAME = 'DolarAPI'

    DOLARAPI_LOGO_URL = 'https://www.google.com/s2/favicons?domain=dolarapi.com&sz=128'

    EXCHANGE_MONITOR_NAME = 'Exchange Monitor'

    EXCHANGE_MONITOR_LOGO_URL = 'https://exchangemonitor.net/assets/img/logo.png'

    # --- Exchange Monitor (scraping híbrido: token CSRF del HTML + JSON) -------
    # El sitio no expone API pública ni sirve las tasas en el HTML estático (los
    # contenedores llegan vacíos y se rellenan por JS). Se obtiene el token CSRF
    # del HTML y con él se pide el JSON de datos de Venezuela. Estas constantes
    # centralizan las claves del payload y los identificadores del sitio.
    EM_USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                     'AppleWebKit/537.36 (KHTML, like Gecko) '
                     'Chrome/120.0.0.0 Safari/537.36')

    EM_ACCEPT = 'application/json, text/javascript, */*; q=0.01'

    # El endpoint de datos espera la zona horaria del cliente en el body.
    EM_TIMEZONE = 'America/Caracas'

    EM_TIMEZONE_KEY = 'timezone'

    # Los ids del sitio vienen prefijados por país (ej. "ve-em"). Persistimos
    # solo el valor propio del sitio (EM) y el promedio estimado; el resto de
    # mercados se exponen solo en vivo.
    EM_ID_PREFIX = 've-'

    EM_ID_OWN = 've-em'

    EM_ID_AVERAGE = 've-average'

    # Códigos persistidos de las dos entradas propias de Exchange Monitor (el id
    # sin el prefijo de país). Se usan para filtrarlas de forma independiente en
    # saved-currencies: EM_CODE_OWN → "Exchange Monitor", EM_CODE_AVERAGE →
    # "Monitor Dólar".
    EM_CODE_OWN = 'em'

    EM_CODE_AVERAGE = 'average'

    # Claves del payload JSON de Exchange Monitor.
    EM_KEY_SUCCESS = 'success'

    EM_KEY_DATA = 'data'

    EM_KEY_SETTINGS = 'settings'

    EM_KEY_DATE = 'date'

    EM_KEY_ID = 'id'

    EM_KEY_NAME = 'name'

    EM_KEY_NAME_LARGE = 'name_large'

    EM_KEY_RATE = 'rate'
