from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware_metrics import MetricsMiddleware
from app.redis_client import close_redis
from app.routes.health import router as health_router
from app.routes.metrics import router as metrics_router
from app.routes.v1 import router as v1_router

@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await close_redis()

app = FastAPI(title="LimitLab", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MetricsMiddleware)
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(v1_router)
