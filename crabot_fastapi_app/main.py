# main.py
import logging
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI

from routers.stock_transfer.stock_transfer import router as stock_transfer_router
from routers.stock_transfer.healthcheck import router as heathcheck_routes
from utils.system_metrics import collect_system_metrics
from dependencies.dependencies import deps  

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # прогреваем пул соединений (создастся при первом обращении)
        deps.db.execute_scalar("SELECT 1")
        logging.info("MySQL pool warmed up.")
    except Exception as e:
        logging.exception("MySQL warmup failed: %s", e)

    # # системные метрики в отдельном потоке
    # threading.Thread(target=collect_system_metrics, daemon=True).start()

    try:
        yield
    finally:
        # --- shutdown ---
        try:
            deps.db.close()  # закрываем свободные подключения
            logging.info("MySQL pool closed.")
        except Exception as e:
            logging.warning("MySQL pool close failed: %s", e)

app = FastAPI(title="Stock Transfer",
                lifespan=lifespan,
                docs_url=None,
                redoc_url=None,
                openapi_url=None)

app.include_router(stock_transfer_router)
app.include_router(heathcheck_routes)

# from prometheus_fastapi_instrumentator import Instrumentator
# from prometheus_client import make_asgi_app
# Instrumentator().instrument(app).expose(app)
# app.mount("/metrics", make_asgi_app())
