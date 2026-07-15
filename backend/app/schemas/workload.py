from pydantic import BaseModel
from typing import Optional, Any
from datetime import date, datetime


class WorkloadBase(BaseModel):
    date: date
    province: Optional[str] = None
    account: str
    name: Optional[str] = None
    emp_no: Optional[str] = None
    team_desc: Optional[str] = None
    metrics: Optional[dict[str, Any]] = None


class WorkloadCreate(WorkloadBase):
    import_batch: str


class WorkloadResponse(WorkloadBase):
    id: int
    import_batch: str
    created_at: datetime

    class Config:
        from_attributes = True


class WorkloadListResponse(BaseModel):
    items: list[WorkloadResponse]
    total: int


class ImportWorkloadResponse(BaseModel):
    count: int
    batch: str


class WorkloadReportItem(BaseModel):
    account: str
    name: str
    emp_no: str
    team_desc: str
    province: str
    role: str = ""
    date_count: int
    aggregated_metrics: dict[str, Any]


class WorkloadReportResponse(BaseModel):
    stats: dict[str, Any]
    items: list[WorkloadReportItem]
    metrics_fields: list[str]
