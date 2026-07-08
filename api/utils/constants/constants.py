class Constants:

    APP_NAME = "DolarTracker"
    
    APP_SUMMARY = "API RESTful de alto rendimiento para el monitoreo y centralización de tasas de cambio en Venezuela (BCV, Paralelo y Cripto) con procesamiento concurrente y persistencia histórica."

    APP_DESCRIPTION="""
## ¡Bienvenido a DolarTracker! 🚀
Esta API proporciona acceso en tiempo real a las tasas cambiarias de Venezuela, consolidando datos de múltiples fuentes confiables:
*   **Banco Central de Venezuela (BCV)**: Tasas oficiales.
*   **Yadio.io**: Tasas del mercado paralelo.
*   **Binance P2P**: Tasas del mercado cripto (USDT/USDC).
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

    VERSION = "1.1.1"

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

    # Mensajes de fallo de las fuentes externas de tasas (BCV, Yadio, Binance).
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