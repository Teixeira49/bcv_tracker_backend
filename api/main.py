from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, Response
import traceback
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
# Buscamos el archivo .env en la raíz del proyecto (un nivel arriba de /api)
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from api.openapi.redoc_theme import get_custom_redoc_html

# Configuramos la app desactivando las docs por defecto para personalizarlas
app = FastAPI(
    title="DolarTracker",
    redoc_url=None, # Desactivamos el ReDoc nativo para usar nuestra versión premium
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
    # Intenta importar tus módulos normalmente
    from api.utils.html.root_html import root_html
    from api.utils.constants.constants import Constants as c
    from api.controller.dollar_controller import router as controller_app
    from api.utils.constants.tags_metadata import tags_metadata

    app.title = c.APP_NAME
    app.summary = c.APP_SUMMARY
    app.description = c.APP_DESCRIPTION
    app.version = c.VERSION
    app.license_info = c.APP_LICENSE
    app.contact = c.APP_CONTACT
    app.openapi_tags = tags_metadata
    
    app.include_router(controller_app)

    @app.get("/", response_class=HTMLResponse, tags=["Root"], summary="Página de bienvenida", include_in_schema=False)
    def root():
        # Pasamos dinámicamente el nombre y la versión desde las constantes
        html_content = root_html(c.APP_NAME, c.VERSION)
        return HTMLResponse(content=html_content, status_code=200)

    @app.get("/redoc", include_in_schema=False)
    async def custom_redoc_ui_html():
        return get_custom_redoc_html(app)

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        file_path = Path(__file__).parent / "static" / "favicon.ico"
        return FileResponse(file_path) if file_path.exists() else Response(status_code=204)

    @app.get("/logo_center.svg", include_in_schema=False)
    async def logo_center():
        file_path = Path(__file__).parent / "static" / "logo_center.svg"
        return FileResponse(file_path, media_type="image/svg+xml") if file_path.exists() else Response(status_code=204)

except Exception as e:
    # Fallback en caso de error de inicialización
    tb = traceback.format_exc()
    app.title = "DolarTracker - Import Error"
    
    @app.get("/", tags=["API - Error Handling"])
    async def root_error():
        return {
            "status": "Critical Error during Initialization",
            "message": str(e),
            "details": "Check /__import_error for the full stack trace"
        }

    @app.get("/__import_error", tags=["API - Error Handling"])
    async def import_error():
        return {"traceback": tb.splitlines()}