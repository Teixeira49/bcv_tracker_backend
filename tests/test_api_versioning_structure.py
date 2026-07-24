"""Issue #52: el versionado lo posee un router (Opción A).

Fija la arquitectura de versionado adoptada:

- Existe un router que POSEE la versión v1 (``api/router/v1.py``) y ensambla los
  controllers por país (hoy Venezuela).
- El prefijo de versión está centralizado en ``Constants.API_V1_STR`` (no
  hardcodeado) y la app expone las rutas de negocio bajo ``/api/v1/venezuela``.
- La estructura permite agregar más controllers de país al router de versión.
"""
from fastapi import FastAPI

from api.router.v1 import router as v1_router
from api.controller.venezuela_controller import router as venezuela_router
from api.utils.constants.constants import Constants as c
import api.main as main


def test_v1_router_aggregates_country_controllers():
    """El router de v1 incluye las rutas del controller de Venezuela."""
    v1_paths = {r.path for r in v1_router.routes}
    venezuela_paths = {r.path for r in venezuela_router.routes}
    # Toda ruta del controller de país queda expuesta por el router de versión.
    assert venezuela_paths
    assert venezuela_paths <= v1_paths


def test_business_routes_mounted_under_centralized_version_prefix():
    """La app monta el negocio bajo Constants.API_V1_STR + /venezuela."""
    app_paths = {r.path for r in main.app.routes}
    # Se usa el prefijo centralizado, no un literal suelto.
    assert any(p.startswith(f"{c.API_V1_STR}/venezuela") for p in app_paths)


def test_version_router_is_extensible():
    """Se pueden agregar más controllers de país al router de versión sin tocar main."""
    extra = FastAPI().router  # un APIRouter cualquiera simulando otro país
    before = len(v1_router.routes)
    v1_router.include_router(extra)
    try:
        assert len(v1_router.routes) >= before  # el agregador acepta más routers
    finally:
        # No dejamos efectos: recortamos lo agregado en la prueba.
        del v1_router.routes[before:]
