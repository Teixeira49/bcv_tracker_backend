"""Router que **posee** la versión v1 del contrato de la API.

Arquitectura de versionado (Opción A, ver la decisión documentada en
``docs/architecture/api-versioning.md``): la versión la posee un *router*, no un
prefijo suelto. Este módulo ensambla los controllers **por país** (hoy
Venezuela; mañana Argentina, etc.) bajo un único ``APIRouter`` de v1.

- **Agregar un país nuevo**: crear su controller (p. ej.
  ``argentina_controller.py``, neutro a la versión) e incluir su router aquí. No
  hay que tocar ``main.py`` ni el prefijo de versión.
- **Agregar una versión futura (v2)**: crear ``api/router/v2.py`` análogo que
  reuse los controllers que siguen válidos y solo redirija los que cambian, y
  montarlo en ``main.py`` con ``Constants.API_V2_STR``. El código de v1 no se
  toca.

El prefijo de versión (``/api/v1``) lo aplica ``main.py`` al montar este router
con ``Constants.API_V1_STR``; aquí no se hardcodea.
"""
from fastapi import APIRouter

from api.controller.venezuela_controller import router as venezuela_router

# APIRouter agregador de la versión 1: ensambla los controllers por país.
router = APIRouter()
router.include_router(venezuela_router)
