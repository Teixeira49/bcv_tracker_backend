from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, Response
import traceback
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
# Buscamos el archivo .env en la raíz del proyecto (un nivel arriba de /api)
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configura el logging estructurado del proyecto una sola vez, antes de montar
# la app, para que tanto el lifespan como los handlers registren con formato y
# niveles consistentes (ver api/core/logging/logger.py).
from api.core.logging.logger import configure_logging, get_logger
configure_logging()
logger = get_logger("main")

from api.openapi.redoc_theme import get_custom_redoc_html


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la app: inicializa el esquema de la BD UNA sola vez.

    ``init_db()`` (``create_all``) se ejecuta aquí, en el arranque, y ya no en
    cada operación de escritura (antes se llamaba por request en
    ``save_currencies_to_db`` / ``save_platform_date``). El esquema versionado lo
    gobierna Alembic (``alembic upgrade head``); este ``create_all`` es una
    garantía idempotente de que las tablas existan en entornos efímeros
    (serverless / cold start), sin sustituir a las migraciones.

    Un fallo de inicialización (p. ej. BD momentáneamente inaccesible) se registra
    pero NO aborta el arranque: los endpoints en vivo (scraping) siguen operativos
    y solo los que tocan BD degradarían de forma controlada.
    """
    try:
        from api.services.bd_service import init_db
        init_db()
    except Exception:
        logger.exception("Fallo al inicializar el esquema de la BD en el arranque")
    yield


# Configuramos la app desactivando las docs por defecto para personalizarlas
app = FastAPI(
    title="DolarTracker",
    redoc_url=None, # Desactivamos el ReDoc nativo para usar nuestra versión premium
    docs_url=None,  # Desactivamos el Swagger nativo para inyectar nuestro CSS oscuro
    lifespan=lifespan,
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        summary=app.summary,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
        contact=app.contact,
        license_info=app.license_info,
    )
    
    # Añadimos el logo de la marca para ReDoc
    openapi_schema["info"]["x-logo"] = {
        "url": "/logo_center.svg",
        "altText": "DolarTracker Logo"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

try:
    # Fail-fast: valida las variables de entorno requeridas antes de montar la
    # app, para abortar con un mensaje que nombre la variable faltante en lugar
    # del error críptico de httpx en cada request.
    from api.core.config.config import Config
    Config.validate()

    # Intenta importar tus módulos normalmente
    from api.utils.html.root_html import root_html
    from api.utils.constants.constants import Constants as c
    from api.controller.dollar_controller import router as controller_app
    from api.utils.constants.tags_metadata import tags_metadata
    from api.controller.docs_controller import router as docs_router
    from api.controller.health_controller import router as health_router

    app.title = c.APP_NAME
    app.summary = c.APP_SUMMARY
    app.description = c.APP_DESCRIPTION
    app.version = c.VERSION
    app.license_info = c.APP_LICENSE
    app.contact = c.APP_CONTACT
    app.openapi_tags = tags_metadata
    
    # Endpoints de negocio: versionados por path bajo `/api/v1` (ver
    # Constants.API_V1_STR). El router ya aporta el segmento de país
    # (`/venezuela`) → resultado `/api/v1/venezuela/...`.
    app.include_router(controller_app, prefix=c.API_V1_STR)
    # Infraestructura sin versionar: la documentación y el health/monitoreo
    # exponen URLs estables e independientes de la versión del contrato.
    app.include_router(docs_router)  # Inyectamos el router de documentación
    app.include_router(health_router) # Inyectamos el router de monitoreo

    from fastapi import Request
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from api.core.errors.exceptions import ExternalSourceError
    from api.core.response.response_wrapper import error_response

    @app.exception_handler(ExternalSourceError)
    async def external_source_error_handler(request: Request, exc: ExternalSourceError):
        # Traduce el fallo de una fuente externa (BCV, Yadio, Binance, Bybit,
        # Airtm, Exchange Monitor) al código
        # HTTP semántico (408 timeout / 502 fuente caída) usando el envelope de
        # error estándar, en lugar de un 200 con datos vacíos o un 500 confuso.
        return error_response(message=exc.message, status_code=exc.status_code)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # Renderiza CUALQUIER HTTPException (400, 404, el 500 de los controllers,
        # etc.) con el mismo envelope `ErrorResponse` {status, message} que el
        # resto de la API, en lugar del `{"detail": ...}` por defecto de FastAPI.
        # Así el shape documentado en `responses={}` coincide con el real y el
        # frontend consume errores y éxitos con el mismo esquema.
        return error_response(message=str(exc.detail), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Red de seguridad: cualquier excepción no controlada colapsa a un 500
        # uniforme. Se registra el traceback en el servidor (no se pierde la
        # información) pero al cliente solo se le devuelve un mensaje genérico,
        # sin filtrar detalles internos.
        logger.exception("Excepción no controlada en %s %s", request.method, request.url.path)
        return error_response(
            message=c.INTERNAL_ERROR_MSG,
            status_code=c.STATUS_INTERNAL_SERVER_ERROR,
        )

    @app.get("/", response_class=HTMLResponse, tags=["Root"], summary="Página de bienvenida", include_in_schema=False)
    def root():
        """Sirve la página de bienvenida (HTML) con el nombre y versión de la app."""
        # Pasamos dinámicamente el nombre y la versión desde las constantes
        html_content = root_html(c.APP_NAME, c.VERSION)
        return HTMLResponse(content=html_content, status_code=200)

except Exception as e:
    # Fallback en caso de error de inicialización.
    # Guardamos el mensaje en una variable propia: `e` se elimina al salir del
    # bloque `except` (semántica de Python 3) y no estaría disponible dentro de
    # los handlers definidos abajo.
    tb = traceback.format_exc()
    error_message = str(e)
    app.title = "DolarTracker - Import Error"

    @app.get("/", tags=["API - Error Handling"])
    async def root_error():
        """Root de respaldo: informa que la app falló al inicializar."""
        return {
            "status": "Critical Error during Initialization",
            "message": error_message,
            "details": "Check /__import_error for the full stack trace"
        }

    @app.get("/__import_error", tags=["API - Error Handling"])
    async def import_error():
        """Expone el traceback del fallo de importación para depuración."""
        return {"traceback": tb.splitlines()}