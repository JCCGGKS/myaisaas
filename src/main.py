"""FastAPI 入口：装配路由、中间件、异常处理；启动时建表。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware import log_requests, register_exception_handlers
from api.routes import auth, channels, ingest, radars, webhooks
from business.monitor.scheduler import scheduler
from config.settings import settings
from data.engine import init_db
from utils.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("启动 %s …", settings.app_name)
    init_db()
    if settings.monitor_autostart:
        scheduler.start()
    yield
    if settings.monitor_autostart:
        await scheduler.stop()
    logger.info("关闭 %s", settings.app_name)


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(log_requests)
register_exception_handlers(app)

app.include_router(radars.router)
app.include_router(channels.router)
app.include_router(auth.router)
app.include_router(webhooks.router)
app.include_router(ingest.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
