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
2. **Siempre** declara `response_model=BaseResponse[T]` en el decorador del router (donde `T` es el schema del payload, ej. `BcvResponseData`, `List[CurrencySchema]`). Esto alimenta la documentación de Swagger/OpenAPI **y** la validación/serialización en runtime.
3. **Siempre** construye el cuerpo con el helper `api_response(...)` de `api/core/response/response_wrapper.py`, que arma el envelope por ti, y **retórnalo directamente** (`return api_response(...)`). El `data` que le pasas es el payload (dict, lista o modelo) que quedará bajo la clave `data`.
4. **Nunca** devuelvas un `Response` crudo (`JSONResponse`, etc.) desde un endpoint que declare `response_model`: FastAPI **omite** la validación cuando recibe un `Response`, y el `response_model` quedaría como mera documentación (drift doc-vs-realidad). El helper `api_response` devuelve un **dict** justamente para evitarlo.
5. Para los **errores** usa `raise HTTPException(...)` y declara el modelo `ErrorResponse` en el `responses={...}` del decorador (ej. `408`, `500`). Los *exception handlers* globales (`api/main.py`) sí devuelven un `Response` vía `error_response`, porque Starlette lo exige a ese nivel; eso es correcto y no contradice la regla 4 (que aplica a los endpoints).

## El helper `api_response`

```python
def api_response(data=None, detail=c.STATUS_OK_MSG, message=c.STATUS_OK_DEATILS):
    ...  # retorna un dict {"status": detail, "message": message, "data": data}
```

- **Devuelve un `dict`, no un `Response`.** Al retornar ese dict desde el endpoint, FastAPI aplica el `response_model=BaseResponse[T]` declarado: lo valida, lo serializa y **filtra** los campos ajenos al schema. Así la salida real coincide con el contrato de OpenAPI.
- `data`: el payload. Si es `None`, la clave `data` se omite.
- `detail`: rellena el campo `status` del envelope (por defecto `"Success"`).
- `message`: mensaje de la operación.
- El **código HTTP** lo gobierna el decorador de la ruta (`status_code=...`), no este helper.

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

Como `api_response` devuelve un **dict** (no un `Response`), FastAPI **sí aplica el `response_model` en runtime**: valida el envelope contra `BaseResponse[T]`, lo serializa y filtra los campos ajenos al schema. La salida real queda garantizada y coincide con el contrato de OpenAPI (issue #18). Consecuencias prácticas:

- Si el `data` que pasas **no** cumple el `T` declarado, FastAPI lanza un `ResponseValidationError` (HTTP 500) en vez de servir silenciosamente una forma incorrecta. Es deseable: el drift se detecta en desarrollo/CI, no en producción.
- Los tipos deben ser serializables/coercibles por Pydantic. Sigue serializando los `datetime` como `str` antes de pasarlos (ver `serialize_with_image` y los `Optional[str]` `createDate`/`updateDate` de `CurrencySchema`): el schema los espera como texto.
- Los campos `Optional` del schema que no proveas aparecerán como `null` en la salida (p. ej. `id` en datos en vivo), porque ahora la respuesta se serializa contra el modelo.

### Guardrail (para no reintroducir el drift)

`tests/test_response_model_contract.py` fija este contrato y **fallará** si se rompe:

- `api_response` debe devolver un `dict` (no un `Response`).
- toda ruta de negocio debe declarar `response_model`.
- FastAPI debe filtrar los campos ajenos al schema y rechazar (500) los payloads que no lo cumplan.

Al agregar o modificar un endpoint, mantén verde ese archivo (corre `pytest`).

## Excepciones

Endpoints que sirven respuestas no-JSON o de otra naturaleza no usan este envelope. Por ejemplo, el health check devuelve su propio modelo `HealthCheckResponse` o un `HTMLResponse` directamente (ver `api/controller/health_controller.py`), y los docs sirven HTML de Swagger/ReDoc.
