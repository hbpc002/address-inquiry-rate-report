from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class ScheduleBase(BaseModel):
    emp_id: int
    schedule_date: date
    shift_type_id: Optional[int] = None


class ScheduleCreate(ScheduleBase):
    schedule_type: str = "正常"
    notes: Optional[str] = None


class ScheduleUpdate(BaseModel):
    shift_type_id: Optional[int] = None
    schedule_type: Optional[str] = None
    notes: Optional[str] = None


class ScheduleResponse(ScheduleBase):
    id: int
    schedule_type: str
    original_shift_id: Optional[int] = None
    notes: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScheduleListResponse(BaseModel):
    items: list[ScheduleResponse]
    total: int


class BatchScheduleRequest(BaseModel):
    emp_ids: list[int]
    shift_type_id: int
    schedule_date: date


class SwapScheduleRequest(BaseModel):
    schedule_a_id: int
    schedule_b_id: int