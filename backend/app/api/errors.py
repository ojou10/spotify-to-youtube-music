from fastapi import Request
from fastapi.responses import JSONResponse

from app.connectors.base import ConnectorError


def error_body(code: str, message: str, action: str | None = None, field_errors: dict | None = None):
    return {"error": {"code": code, "message": message, "action": action, "field_errors": field_errors}}


def connector_error_response(_: Request, exc: ConnectorError) -> JSONResponse:
    return JSONResponse(status_code=400, content=error_body(exc.code, exc.summary))
