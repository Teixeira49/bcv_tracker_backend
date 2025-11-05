from fastapi import FastAPI
import traceback

try:
    # intenta importar tu router normalmente
    from api.controller.dollar_controller import router as controller_app

    app = FastAPI(title="DolarTracker")
    app.include_router(controller_app)

except Exception as e:
    # Si falla la importación, exponemos un app mínimo que muestre la traza para debugging
    tb = traceback.format_exc()
    app = FastAPI(title="DolarTracker - Import Error")

    @app.get("/")
    async def root():
        return {"error": "import_failed", "message": str(e)}

    @app.get("/__import_error")
    async def import_error():
        # endpoint temporal para ver la traza completa en los logs/response
        return {"traceback": tb}