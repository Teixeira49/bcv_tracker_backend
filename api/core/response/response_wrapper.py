from fastapi.responses import JSONResponse
from api.utils.constants.constants import Constants as c

def api_response(data=None, detail=c.STATUS_OK_MSG, message=c.STATUS_OK_DEATILS, status_code=c.STATUS_OK):
    """Arma el envelope de éxito estándar: ``{status, message, data?}``.

    Es el envoltorio único de respuestas exitosas de la API, para que todos los
    endpoints devuelvan la misma forma que consume el frontend. La clave
    ``data`` solo se incluye cuando se provee (no se serializa ``None``).

    :param data: payload de la respuesta (dict/list/modelo); omitido si es ``None``.
    :param detail: valor del campo ``status`` (por defecto ``"Success"``).
    :param message: mensaje descriptivo de la operación.
    :param status_code: código HTTP de la respuesta (por defecto 200).
    :return: ``JSONResponse`` con el envelope estándar.
    """
    content={
            "status": detail,
            "message": message,
        }
    if data is not None:
        content["data"] = data
    return JSONResponse(
        status_code=status_code,
        content=content
    )

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