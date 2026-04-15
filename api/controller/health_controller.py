from fastapi import APIRouter, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from api.utils.constants.constants import Constants as c
from api.utils.html.health_html import health_html

router = APIRouter(tags=["Health"])

class HealthCheckResponse(BaseModel):
    status: str
    version: str
    app_name: str

@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Verificar estado de la API",
    description="Endpoint de monitoreo (health-check) para confirmar que el servidor esté activo y respondiendo. Ideal para validaciones de Load Balancers o contenedores Docker.",
    responses={
        200: {
            "description": "La API está funcionando correctamente.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "version": "1.1.1",
                        "app_name": "DolarTracker"
                    }
                }
            }
        }
    }
)
async def health_check():
    return HealthCheckResponse(
        status="ok",
        version=c.VERSION,
        app_name=c.APP_NAME
    )

@router.get("/health/ui", include_in_schema=False)
async def health_check_ui():
    html_content = health_html(c.APP_NAME, c.VERSION)
    return HTMLResponse(content=html_content, status_code=200)

