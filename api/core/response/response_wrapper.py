from fastapi.responses import JSONResponse
from api.utils.constants.constants import Constants as c

def api_response(data=None, detail=c.STATUS_OK_MSG, message=c.STATUS_OK_DEATILS, status_code=c.STATUS_OK):
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