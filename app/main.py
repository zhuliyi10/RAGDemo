"""FastAPI 应用入口。"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.deps import init_vector_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_vector_store()
    logger.info(
        "向量库已初始化: provider=%s model=%s",
        get_settings().embedding_provider,
        get_settings().embedding_model,
    )
    yield


app = FastAPI(
    title="RAGDemo",
    description="自研轻量 RAG 服务：文档入库 + 语义检索 + 增强生成",
    version="0.1.0",
    lifespan=lifespan,
)
# 允许本地前端开发服务器（任意端口）跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
