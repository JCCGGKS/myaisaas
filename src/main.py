"""FastAPI 入口：装配路由、中间件、异常处理；启动时建表。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware import log_requests, register_exception_handlers
from api.routes import auth, channels, ingest, radars, webhooks
from business.monitor.scheduler import scheduler
from config.settings import settings
from data.engine import init_db
from middleware.csrf import CSRFOriginMiddleware
from utils.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("启动 %s …", settings.app.name)
    init_db()
    if settings.monitor.autostart:
        scheduler.start()
    yield
    if settings.monitor.autostart:
        await scheduler.stop()
    logger.info("关闭 %s", settings.app.name)


app = FastAPI(title=settings.app.name, lifespan=lifespan)

# 中间件顺序（最后注册 = 最外层）：CORS 最外层（保证 403 也带 CORS 头），
# 其内为 CSRF Origin 校验，最内为请求日志。
app.middleware("http")(log_requests)
app.add_middleware(CSRFOriginMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)

app.include_router(radars.router)
app.include_router(channels.router)
app.include_router(auth.router)
app.include_router(webhooks.router)
app.include_router(ingest.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
