from fastapi.responses import JSONResponse
from api.utils.constants.constants import Constants as c

def api_response(data=None, detail=c.STATUS_OK_MSG, message=c.STATUS_OK_DEATILS):
    """Arma el envelope de éxito estándar: ``{status, message, data?}``.

    Es el envoltorio único de respuestas exitosas de la API, para que todos los
    endpoints devuelvan la misma forma que consume el frontend. La clave
    ``data`` solo se incluye cuando se provee (no se serializa ``None``).

    Devuelve un **dict plano** (no un ``Response``) a propósito: al retornar el
    dict, FastAPI **sí aplica el ``response_model=BaseResponse[T]`` declarado en
    el decorador** (lo valida, serializa y filtra), de modo que la salida real
    coincide con el contrato documentado en OpenAPI. Si en su lugar se devolviera
    un ``JSONResponse``, FastAPI omitiría esa validación y el ``response_model``
    quedaría como mera documentación (drift doc-vs-realidad; ver issue #18).

    El código HTTP lo gobierna el decorador de la ruta (``status_code=...``), no
    este helper; para errores se usa ``raise HTTPException`` + ``error_response``.

    :param data: payload de la respuesta (dict/list/modelo); omitido si es ``None``.
    :param detail: valor del campo ``status`` (por defecto ``"Success"``).
    :param message: mensaje descriptivo de la operación.
    :return: ``dict`` con el envelope estándar, listo para que FastAPI lo valide
        contra el ``response_model`` de la ruta.
    """
    content = {
        "status": detail,
        "message": message,
    }
    if data is not None:
        content["data"] = data
    return content

def error_response(message, status=c.STATUS_ERROR_MSG, status_code=c.STATUS_INTERNAL_SERVER_ERROR):
    """Arma el envelope de error estándar (`ErrorResponse`): {status, message}.

    Mantiene la forma consistente con `api_response` para que el frontend
    consuma errores y éxitos con el mismo esquema base.
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "message": message,
        }
    )