from fastapi import FastAPI
from contextlib import asynccontextmanager
# from infrastructure.db.postgres.base import postgres_db
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import make_asgi_app
from routers.stock_transfer.stock_transfer import router as stock_transfer_router
from utils.system_metrics import collect_system_metrics
import threading

### -------- Async

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     await db.connect()
#     threading.Thread(target=collect_system_metrics, daemon=True).start() 
#     try:
#         yield
#     finally:
#         await db.close()


### -------- Sync

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     postgres_db.connect()  # sync
#     collect_system_metrics()
#     try:
#         yield
#     finally:
#         postgres_db.close()  # sync


# app = FastAPI(title='Stock Transfer', lifespan=lifespan)

app = FastAPI(title='Stock Transfer')

# instrumentator = Instrumentator().instrument(app).expose(app)

# app.mount("/metrics", make_asgi_app())

app.include_router(stock_transfer_router)
