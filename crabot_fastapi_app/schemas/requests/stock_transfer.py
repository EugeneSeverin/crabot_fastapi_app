from pydantic import BaseModel
from uuid import UUID
from typing import Dict, Any, List, Union, Optional


class CreateFullTaskRequest(BaseModel):
    supplier_id: int
    region_from_id: Optional[int] = None
    warehouse_from_id: Optional[int] = None
    region_to_id: Optional[int] = None
    warehouse_to_id: Optional[int] = None

class CreateFullTaskResponse(BaseModel):
    task_id: int
    from_region: str
    to_region: str
    status: str

class UpdateTaskStatusRequest(BaseModel):
    task_id: int
    new_status: str

class TaskProductRequest(BaseModel):
    task_id: int
    supplier_id: int

class TaskProductUpdate(BaseModel):
    product_id: int
    size: str
    quantity: int

class TaskProductUpdateRequest(BaseModel):
    task_id: int
    products: List[TaskProductUpdate]

class SwitchUserModeRequest(BaseModel):
    supplier_id: int
    new_mode: str

class DistributionTargetRow(BaseModel):
    region_id: int
    warehouse_id: int
    article: str
    size: str
    target_percent: float

class DistributionImportRequest(BaseModel):
    supplier_id: int
    rows: List[DistributionTargetRow]
