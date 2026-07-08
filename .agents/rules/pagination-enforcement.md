---
description: Obligatoriedad de implementar paginación en todos los endpoints de tipo lista (GET)
---
# Paginación Obligatoria en Listas

Para asegurar el rendimiento y la escalabilidad de la plataforma, todos los endpoints que retornen colecciones o listas de elementos deben implementar un sistema de paginación.

> **Estado actual del código:** hoy esta paginación **todavía no está implementada**. Los endpoints que devuelven listas (ej. los `BaseResponse[List[CurrencySchema]]` de `api/controller/dollar_controller.py`) retornan la colección completa, sin `page`/`size`. Además, **`PaginationMeta` no existe aún** y el envelope `BaseResponse` (`api/models/schemas.py`) **no tiene campo `meta`** (solo `status`, `message`, `data`). Esta regla es la norma a seguir cuando se construya el primer endpoint paginado; la sección "Piezas que hay que crear" indica exactamente qué falta.

## Reglas de Implementación

1.  **Parámetros de Entrada**: Todo endpoint que devuelva una lista debe aceptar los parámetros `page` (página actual) y `size` (cantidad de elementos por página).
2.  **Valores por Defecto**: Se recomienda usar `page=1` y `size=10` como valores predeterminados.
3.  **Metadatos de Paginación**: La respuesta debe incluir el objeto `meta` (basado en `PaginationMeta`) dentro del envelope `BaseResponse`.
4.  **Cálculos de Metadatos**: El objeto `meta` debe contener:
    *   `page`: Número de la página actual.
    *   `size`: Cantidad de elementos solicitados por página.
    *   `total`: Total de registros existentes en la base de datos para esa consulta (sin filtrar por paginación).
    *   `total_pages`: Cálculo de `(total + size - 1) // size`.

## Piezas que hay que crear (aún no existen en el código)

Antes de paginar el primer endpoint, hay que añadir estas tres piezas:

1.  **Schema `PaginationMeta`** en `api/models/schemas.py`:
    ```python
    class PaginationMeta(BaseModel):
        page: int
        size: int
        total: int
        total_pages: int
    ```

2.  **Campo `meta`** en el envelope `BaseResponse` (`api/models/schemas.py`):
    ```python
    class BaseResponse(BaseModel, Generic[T]):
        status: str = Field(..., description="Estado de la respuesta (ej. Success)")
        message: str = Field(..., description="Detalle o mensaje de la operación")
        data: Optional[T] = Field(None, description="Datos de la respuesta")
        meta: Optional[PaginationMeta] = Field(None, description="Metadatos de paginación")
    ```

3.  **Soporte de `meta` en el helper `api_response`** (`api/core/response/response_wrapper.py`), para que pueda incluir el objeto en la respuesta:
    ```python
    def api_response(data=None, detail=c.STATUS_OK_MSG, message=c.STATUS_OK_DEATILS,
                     status_code=c.STATUS_OK, meta=None):
        content = {"status": detail, "message": message}
        if data is not None:
            content["data"] = data
        if meta is not None:
            content["meta"] = meta
        return JSONResponse(status_code=status_code, content=content)
    ```

## Ejemplo de Implementación

Sigue el patrón de respuesta estándar del proyecto (ver `standard-response.md`): `response_model=BaseResponse[T]` en el decorador y el helper `api_response(...)` en el cuerpo.

```python
from fastapi import APIRouter, HTTPException, Query, status
from typing import List

from api.models.schemas import BaseResponse, CurrencySchema, PaginationMeta, ErrorResponse
from api.core.response.response_wrapper import api_response

@router.get(
    "/currencies/history",
    response_model=BaseResponse[List[CurrencySchema]],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": BaseResponse[List[CurrencySchema]], "description": "Histórico de tasas paginado"},
        500: {"model": ErrorResponse, "description": "Error al consultar el histórico"},
    },
)
async def list_currency_history(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(10, ge=1, le=100, description="Tamaño de página"),
):
    try:
        items, total = await dollar_service.get_history_page(page=page, size=size)
        meta = PaginationMeta(
            page=page,
            size=size,
            total=total,
            total_pages=(total + size - 1) // size,
        )
        return api_response(items, meta=meta.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

> Recordatorio (ver `standard-response.md`): como `api_response` devuelve un `JSONResponse`, FastAPI **no valida** el `response_model` en runtime. Asegúrate de que `data`, `meta` y sus tipos coincidan con lo declarado, y serializa a mano los tipos no-JSON (por eso arriba se usa `meta.model_dump()`).

## Excepciones
Esta regla no aplica a:
*   Endpoints que devuelven un único recurso (`GET /recurso/{id}`).
*   Endpoints de utilidades que devuelven listas estáticas o extremadamente pequeñas (ej: las tasas vigentes de una sola consulta en vivo).
*   Casos donde se justifique técnicamente la necesidad del dataset completo.
