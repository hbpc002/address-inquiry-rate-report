from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class DailyReportBase(BaseModel):
    emp_id: int
    schedule_date: date


class DailyReportResponse(BaseModel):
    id: int
    emp_id: int
    emp_no: Optional[str] = None
    name: Optional[str] = None
    team: Optional[str] = None
    dept: Optional[str] = None
    schedule_date: date
    shift_type_id: Optional[int]
    schedule_type: Optional[str]
    scheduled_start: Optional[str]
    scheduled_end: Optional[str]
    scheduled_hours: Optional[float]
    actual_checkin: Optional[datetime]
    actual_checkout: Optional[datetime]
    actual_hours: Optional[float]
    status: Optional[str]
    late_minutes: int
    early_minutes: int
    overtime_hours: float
    calculated_at: datetime

    class Config:
        from_attributes = True


class DailyReportListResponse(BaseModel):
    items: list[DailyReportResponse]
    total: int