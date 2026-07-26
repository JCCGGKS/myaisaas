"""CSRF 防护中间件：对写请求校验 Origin（呼应 01_guest.md §8 第 1 步）。

仅做同源/受信源校验（最轻量、优先做），与 wa_auth 的 SameSite 互补：
- 安全方法（GET/HEAD/OPTIONS）跳过；
- 写方法：Origin 必须匹配「本站 Host 源」或 `csrf_trusted_origins` 之一，否则 403；
- Origin 缺失视为可疑（合法同站 fetch/XHR 均带 Origin），拒绝写请求；
- 配置由 settings 动态读取，便于测试关闭（`WA_CSRF_ENABLED=false`）。
"""
from config.settings import settings
from utils.logging import get_logger

logger = get_logger(__name__)

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class CSRFOriginMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] in _SAFE_METHODS:
            await self.app(scope, receive, send)
            return
        if not settings.csrf_enabled:
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        origin = headers.get("origin")
        if not origin:
            logger.warning("CSRF 校验失败：写请求缺少 Origin 头")
            await self._deny(scope, receive, send)
            return

        host = headers.get("host", "")
        proto = headers.get("x-forwarded-proto") or scope.get("scheme") or "http"
        same_origin = f"{proto}://{host}"
        trusted = set(settings.csrf_trusted_origins)
        if origin == same_origin or origin in trusted:
            await self.app(scope, receive, send)
            return

        logger.warning("CSRF 校验失败 origin=%s host=%s", origin, host)
        await self._deny(scope, receive, send)

    @staticmethod
    async def _deny(scope, receive, send) -> None:
        from starlette.responses import Response

        response = Response("CSRF Origin mismatch", status_code=403)
        await response(scope, receive, send)
