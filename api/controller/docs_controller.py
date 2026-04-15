from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, Response
from pathlib import Path

from api.openapi.swagger_theme import get_custom_swagger_html
from api.openapi.redoc_theme import get_custom_redoc_html

router = APIRouter()

@router.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(request: Request):
    # Accedemos a la instancia de FastAPI a través de request.app
    return get_custom_swagger_html(request.app)

@router.get("/redoc", include_in_schema=False)
async def custom_redoc_ui_html(request: Request):
    return get_custom_redoc_html(request.app)

@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    # Resolvemos la ruta a la carpeta static, que está un nivel arriba de controller
    file_path = Path(__file__).parent.parent / "static" / "favicon.ico"
    return FileResponse(file_path) if file_path.exists() else Response(status_code=204)

@router.get("/logo_center.svg", include_in_schema=False)
async def logo_center():
    file_path = Path(__file__).parent.parent / "static" / "logo_center.svg"
    return FileResponse(file_path, media_type="image/svg+xml") if file_path.exists() else Response(status_code=204)
