import logging
import traceback
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from typing import List

from schemas.requests.stock_transfer import (
    CreateFullTaskRequest, CreateFullTaskResponse, UpdateTaskStatusRequest,
    TaskProductRequest, TaskProductUpdate, TaskProductUpdateRequest,
    SwitchUserModeRequest, DistributionTargetRow, DistributionImportRequest)

from services.mysql_db_service.stock_transfer_service import DBController
from infrastructure.api.sync_controller import SyncAPIController
from dependencies.dependencies import deps
from core.base_request_processor import BaseRequestProcessor


# Logging setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(tags=["Healthcheck"])

# region /healthcheck
@router.get("/healthcheck", tags=["Monitoring"])
def healthcheck():
    logger.info("Healthcheck called.")
    return {"status": "ok"}
# endregion

# region /sum
@router.get("/sumdata", tags=["Calculacting"])
def sumdata(first_num: str = Query(...), 
            second_num: str = Query(...)):
    logger.info("Sum called.")
    return {"result": int(first_num) + int(second_num)}
# endregion


