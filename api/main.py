from fastapi import FastAPI
import traceback
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
# Esto debe hacerse ANTES de que se importe cualquier otro módulo que las necesite.
load_dotenv()

try:
    # intenta importar tu router normalmente
    from api.controller.dollar_controller import router as controller_app

    app = FastAPI(title="DolarTracker")
    app.include_router(controller_app)

except Exception as e:
    # Si falla la importación, exponemos un app mínimo que muestre la traza para debugging
    tb = traceback.format_exc()
    app = FastAPI(title="DolarTracker - Import Error")
    exception = Exception.with_traceback

    @app.get("/")
    async def root():
        return {"error": "import_failed", "message": str(exception)}

    @app.get("/__import_error")
    async def import_error():
        # endpoint temporal para ver la traza completa en los logs/response
        return {"traceback": tb}