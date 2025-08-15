import logging
import traceback
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from typing import List

from schemas.requests.stock_transfer import (
    CreateFullTaskRequest, CreateFullTaskResponse, UpdateTaskStatusRequest,
    TaskProductRequest, TaskProductUpdate, TaskProductUpdateRequest,
    SwitchUserModeRequest, DistributionTargetRow, DistributionImportRequest,
    RegularTaskUpsertRequest, RegularTaskResponse)

from services.mysql_db_service.stock_transfer_service import DBController
from infrastructure.api.sync_controller import SyncAPIController
from dependencies.dependencies import deps
from core.base_request_processor import BaseRequestProcessor
# from infrastructure.db.postgres.base import postgres_db
from routers.stock_transfer.mock_responses import get_task_mock, cancel_task_mock, \
                                                    create_full_task_mock, get_task_products_mock, \
                                                    update_task_products_mock, get_transferrable_products_mock, \
                                                    get_regions_mock, get_transfer_mode_mock, get_warehouses_mock
from dependencies.auth import require_bearer

# Logging setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(tags=["Stock Transfer"],
                   dependencies=[Depends(require_bearer)])

# ------- SETTINGS
CACHE_LIFESPAN = 5
BASE_URL = ""
db_controller = DBController(db=deps.db)

class CreateFullTaskRequest(BaseModel):
    supplier_id: int
    warehouse_from_ids: List[int]
    warehouse_to_ids: List[int]


# region Задания

@router.post("/stock_transfer/create_full_task")
async def create_full_task(request: CreateFullTaskRequest):
    logger.info("POST /stock_transfer/create_full_task | Request: %s", request.model_dump_json())

    try:
        task_data = {
            "supplier_id": request.supplier_id,
            "warehouse_from_ids": request.warehouse_from_ids,
            "warehouse_to_ids": request.warehouse_to_ids
        }

        result = db_controller.create_new_task(task_data)

        logger.info(f"Full task created successfully. task_id:{result}")
        return {"status": "success", "task_id": result}

    except Exception as e:
        logger.error("Error in create_full_task: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))
    
    

@router.get("/stock_transfer/get_tasks")
async def get_tasks(
    start_date: str = Query(...),  # ISO format: '2024-01-01'
    end_date: str = Query(...),
    only_active: bool = Query(...)):
    logger.info(
        "GET /stock_transfer/get_tasks | Params: start_date=%s, end_date=%s, only_active=%s",
        start_date, end_date, only_active)

    try:
        tasks = db_controller.get_tasks(start_date, end_date, only_active)

        logger.info("Tasks retrieved successfully.")
        return tasks

    except Exception as e:
        logger.error("Error in get_tasks: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/stock_transfer/update_task_status")
async def update_task_status(request: UpdateTaskStatusRequest):
    logger.info("PUT /stock_transfer/update_task_status | Request: %s", request.model_dump_json())
    try:
        # result = ...
        logger.info("Task status updated successfully.")
        
        result = {}
        
        return result
    except Exception as e:
        logger.error("Error in update_task_status: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stock_transfer/get_task_products")
async def get_task_products(task_id: int = Query(...)):
    logger.info("GET /stock_transfer/get_task_products | task_id: %s", task_id)
    try:
        result = db_controller.get_task_products_by_task_id(task_id)
        return result
    except Exception as e:
        logger.error("Error in get_task_products: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stock_transfer/update_task_products")
async def update_task_products(request: TaskProductUpdateRequest):
    logger.info("POST /stock_transfer/update_task_products | Request: %s", request.model_dump_json())
    try:
        db_controller.update_task_products(
            task_id=request.task_id,
            products=[p.model_dump() for p in request.products])
        logger.info("Task products updated successfully.")
        return {"status": "success", "message": "Task products updated."}

    except Exception as e:
        logger.error("Error in update_task_products: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))

# endregion

# region Доступные товары

@router.get("/stock_transfer/get_transferable_products")
async def get_transferable_products(
    warehouse_from_ids: Optional[list[int]] = Query(None)):
    logger.info("GET /stock_transfer/get_transferable_products | Params: %s", {
        "warehouse_from_ids": warehouse_from_ids})
    
    try:
        # result = ...
        # result = get_transferrable_products_mock

        result = db_controller.get_current_stocks(warehouse_from_ids)

        return result
    except Exception as e:
        logger.error("Error in get_transferable_products: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))

# endregion

# region Справочники

@router.get("/stock_transfer/get_warehouses")
async def get_warehouses():
    logger.info("GET /stock_transfer/get_warehouses")
    try:
        # result = ...
        logger.info("Warehouses retrieved successfully.")

        result = db_controller.get_all_warehouses()

        return result
    except Exception as e:
        logger.error("Error in get_warehouses: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stock_transfer/get_regions")
async def get_regions():
    logger.info("GET /stock_transfer/get_regions")
    try:
        # result = ...
        logger.info("Regions retrieved successfully.")
        
        # result = get_regions_mock

        result = db_controller.get_all_regions()

        return result
    except Exception as e:
        logger.error("Error in get_regions: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))

# endregion

# region Режим работы

@router.get("/stock_transfer/get_transfer_mode/{supplier_id}")
async def get_transfer_mode(supplier_id: int):
    logger.info("GET /stock_transfer/get_transfer_mode | Supplier ID: %d", supplier_id)
    try:
        # result = ...
        logger.info("Transfer mode retrieved successfully.")
        
        result = get_transfer_mode_mock
        
        return result
    except Exception as e:
        logger.error("Error in get_transfer_mode: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/stock_transfer/switch_store_mode")
async def switch_store_mode(request: SwitchUserModeRequest):
    logger.info("POST /stock_transfer/switch_store_mode | Request: %s", request.model_dump_json())
    try:
        # result = ...
        logger.info("Store mode switched successfully.")
        return {}
    except Exception as e:
        logger.error("Error in switch_store_mode: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))

# endregion

# region Распределение (автоматический режим)

@router.get("/stock_transfer/distribution_targets")
async def get_distribution_targets(supplier_id: int = Query(...)):
    logger.info("GET /stock_transfer/distribution_targets | Supplier ID: %d", supplier_id)
    try:
        # result = ...
        logger.info("Distribution targets retrieved successfully.")
        return {}
    except Exception as e:
        logger.error("Error in get_distribution_targets: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/stock_transfer/import_distribution_targets")
async def upload_distribution_targets(request: DistributionImportRequest):
    logger.info("POST /stock_transfer/import_distribution_targets | Request: %s", request.model_dump_json())
    try:
        # result = ...
        logger.info("Distribution targets imported successfully.")
        return {}
    except Exception as e:
        logger.error("Error in upload_distribution_targets: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))

# endregion


# ======== ЭНДПОЙНТЫ РЕГУЛЯРОК ========

@router.post("/stock_transfer/regular_tasks")
async def save_regular_task(request: RegularTaskUpsertRequest):
    """
    Архивирует старые регулярные задания и создаёт новое.
    Возвращает task_id.
    """
    logger.info("POST /stock_transfer/regular_tasks | Request: %s", request.model_dump_json())
    try:
        new_task_id = db_controller.save_regular_task(
            supplier_id=request.supplier_id,
            target=request.target,
            minimum=request.minimum
        )
        logger.info("Regular task saved successfully. task_id=%s", new_task_id)
        return {"status": "success", "task_id": new_task_id}
    except Exception as e:
        logger.error("Error in save_regular_task: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stock_transfer/regular_tasks", response_model=RegularTaskResponse)
async def get_active_regular_task():
    """
    Возвращает только одно активное (неархивированное) регулярное задание.
    """
    logger.info("GET /stock_transfer/regular_tasks")
    try:
        row = db_controller.get_active_regular_task()
        if not row:
            raise HTTPException(status_code=404, detail="No active regular task found")

        return RegularTaskResponse(
            task_id=row["task_id"],
            target=row["target"],
            minimum=row["minimum"],
            created_at=row.get("task_creation_date")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in get_active_regular_task: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))