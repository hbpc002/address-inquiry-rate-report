from pydantic import BaseModel
from typing import Optional, Any
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
    name: Optional[str] = None
    emp_no: Optional[str] = None
    team: Optional[str] = None
    shift_name: Optional[str] = None
    shift_time: Optional[str] = None
    time_segments: Optional[Any] = None
    work_hours: Optional[float] = None
    punctuality_rate: Optional[float] = None
    call_duration: Optional[float] = None
    organize_duration: Optional[float] = None
    utilization_rate: Optional[float] = None
    attendance_rate: Optional[float] = None

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