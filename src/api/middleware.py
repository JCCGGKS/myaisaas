"""中间件与统一异常处理。"""
import time

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from utils.exceptions import AppError
from utils.logging import get_logger

logger = get_logger(__name__)


async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    cost = (time.time() - start) * 1000
    # API 入口/返回日志（高频轮询内用 INFO 即可，细节用 DEBUG）
    logger.info(
        "%s %s -> %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        cost,
    )
    return response


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError):
        logger.warning("业务错误 %s: %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, **exc.extra},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception):
        logger.error("未处理异常: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"code": "internal_error", "message": "服务器内部错误"},
        )
