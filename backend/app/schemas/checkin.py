from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CheckinBase(BaseModel):
    emp_no: str
    name: Optional[str] = None
    checkin_time: datetime
    checkout_time: Optional[datetime] = None
    device_no: Optional[str] = None
    dept: Optional[str] = None


class CheckinCreate(CheckinBase):
    import_batch: str


class CheckinResponse(CheckinBase):
    id: int
    import_batch: str
    created_at: datetime

    class Config:
        from_attributes = True


class CheckinListResponse(BaseModel):
    items: list[CheckinResponse]
    total: int


class ImportCheckinResponse(BaseModel):
    count: int
    batch: str