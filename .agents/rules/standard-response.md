---
description: Obligatoriedad de usar el formato de respuesta estándar (BaseResponse + helper api_response)
---
# Respuesta Estándar Obligatoria

Para mantener la consistencia en el consumo de la API por parte del frontend, todos los endpoints deben envolver sus respuestas en el esquema base unificado `BaseResponse[T]`.

## El envelope

El esquema base vive en `api/models/schemas.py` y tiene tres campos:

```python
class BaseResponse(BaseModel, Generic[T]):
    status: str    # ej. "Success"
    message: str   # detalle de la operación
    data: Optional[T]  # el payload real
```

No se llama `APIResponse`: el nombre real y en uso en todo el proyecto es **`BaseResponse`**.

## Reglas

1. **Nunca** devuelvas datos "pelados" (un dict crudo, una lista, o una instancia de la BD) sin envolver. Siempre pasan por el envelope.
2. **Siempre** declara `response_model=BaseResponse[T]` en el decorador del router (donde `T` es el schema del payload, ej. `BcvResponseData`, `List[CurrencySchema]`). Esto alimenta la documentación de Swagger/OpenAPI.
3. **Siempre** construye el cuerpo con el helper `api_response(...)` de `api/core/response/response_wrapper.py`, que arma el envelope por ti. El `data` que le pasas es el payload (dict, lista o modelo) que quedará bajo la clave `data`.
4. Para los **errores** usa `raise HTTPException(...)` y declara el modelo `ErrorResponse` en el `responses={...}` del decorador (ej. `408`, `500`).

## El helper `api_response`

```python
def api_response(data=None, detail=c.STATUS_OK_MSG, message=c.STATUS_OK_DEATILS, status_code=c.STATUS_OK):
    ...  # retorna un JSONResponse con {"status": detail, "message": message, "data": data}
```

- `data`: el payload. Si es `None`, la clave `data` se omite.
- `detail`: rellena el campo `status` del envelope (por defecto `"Success"`).
- `message`: mensaje de la operación.
- `status_code`: código HTTP (por defecto `200`).

## Ejemplos

### Incorrecto
```python
@router.get("/bcv")
async def get_bcv_currencies():
    return await dollar_service.getCurrenciesByBCV()  # ❌ payload pelado, sin envelope ni response_model
```

### Correcto
```python
from fastapi import APIRouter, HTTPException, status
from api.models.schemas import BaseResponse, BcvResponseData, ErrorResponse
from api.core.response.response_wrapper import api_response

@router.get(
    "/bcv",
    response_model=BaseResponse[BcvResponseData],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": BaseResponse[BcvResponseData], "description": "Tasas del BCV obtenidas exitosamente"},
        500: {"model": ErrorResponse, "description": "Error al consultar la fuente"},
    },
)
async def get_bcv_currencies():
    try:
        exchange_rate = await dollar_service.getCurrenciesByBCV()
        return api_response(exchange_rate)  # ✅ envuelto por el helper
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Nota importante sobre la validación

Como `api_response` devuelve un `JSONResponse` directamente, FastAPI **no aplica el `response_model` en runtime**: solo lo usa para generar la documentación. Es decir, el `response_model` documenta la forma, pero **no la valida ni la serializa** automáticamente. Por eso:

- Eres tú quien debe asegurar que el `data` que pasas coincide exactamente con el `T` declarado en `response_model`. Si la forma se desvía, Swagger dirá una cosa y la API responderá otra, sin error.
- Serializa manualmente los tipos no-JSON antes de pasarlos (ej. `datetime` como `str`), ya que el `JSONResponse` no los convierte solo. Ver `serialize_with_image` en el servicio y los campos `Optional[str]` de `CurrencySchema` (`createDate`, `updateDate`) como referencia.

## Excepciones

Endpoints que sirven respuestas no-JSON o de otra naturaleza no usan este envelope. Por ejemplo, el health check devuelve su propio modelo `HealthCheckResponse` o un `HTMLResponse` directamente (ver `api/controller/health_controller.py`), y los docs sirven HTML de Swagger/ReDoc.
