from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def _error_payload(code: str, message: str) -> dict[str, object]:
    return {
        'error': {'code': code, 'message': message},
        'data': None,
        'meta': None,
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        request_id = request.headers.get('x-request-id', 'generated-placeholder-id')
        return JSONResponse(
            status_code=422,
            content={
                'error': {'code': 'VALIDATION_ERROR', 'message': 'Request validation failed'},
                'data': {'details': exc.errors()},
                'meta': {'request_id': request_id},
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(code='http_error', message=str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception('Unhandled exception', exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=_error_payload(code='internal_server_error', message='Internal server error'),
        )
