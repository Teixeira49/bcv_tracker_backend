from fastapi import FastAPI
# importa la app existente desde el controller
from controller.dollar_controller import router as controller_app

app = FastAPI(title="DolarTracker")

app.include_router(controller_app)