from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ShiftTypeBase(BaseModel):
    shift_name: str
    start_time: str
    end_time: str
    work_hours: float
    color: str = "#409EFF"
    is_night: bool = False


class ShiftTypeCreate(ShiftTypeBase):
    pass


class ShiftTypeUpdate(BaseModel):
    shift_name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    work_hours: Optional[float] = None
    color: Optional[str] = None
    is_night: Optional[bool] = None
    is_active: Optional[bool] = None


class ShiftTypeResponse(ShiftTypeBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True