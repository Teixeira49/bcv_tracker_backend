import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, Response
from api.utils.html.root_html import root_html
from api.utils.constants.constants import Constants as c
import traceback
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
# Buscamos el archivo .env en la raíz del proyecto (un nivel arriba de /api)
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

try:
    # intenta importar tu router normalmente
    from api.controller.dollar_controller import router as controller_app

    app = FastAPI(title=c.APP_NAME, version=c.VERSION)
    app.include_router(controller_app)

    @app.get("/", response_class=HTMLResponse, tags=["Root"])
    def root():
        html_content = root_html()
        return HTMLResponse(content=html_content, status_code=200)

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        file_path = Path(__file__).parent / "static" / "favicon.ico"
        if file_path.exists():
            return FileResponse(file_path)
        return Response(status_code=204)

except Exception as e:
    # Si falla la importación, exponemos un app mínimo que muestre la traza para debugging
    tb = traceback.format_exc()
    app = FastAPI(title="DolarTracker - Import Error")
    error_msg = str(e)
    error_type = type(e).__name__

    @app.get("/", tags=["API - Error Handling"])
    async def root():
        return {
            "status": "Critical Error during Initialization",
            "error_type": error_type,
            "message": error_msg,
            "details": "Check /__import_error for the full stack trace."
        }

    @app.get("/__import_error", tags=["API - Error Handling"])
    async def import_error():
        # Retornamos la traza como una lista de líneas para que sea legible en el navegador
        return {"traceback": tb.splitlines()}