"""自定义异常：统一在 API 层映射为 HTTP 响应。"""
from typing import Any


class AppError(Exception):
    """业务错误，携带 HTTP 状态码与可暴露给前端的 code。"""

    def __init__(self, message: str, status_code: int = 400, code: str | None = None, extra: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.extra = extra or {}


class LimitExceededError(AppError):
    """游客达到限额（雷达/渠道），前端据此引导登录。"""

    def __init__(self, message: str, code: str = "limit_exceeded"):
        super().__init__(message, status_code=402, code=code)
