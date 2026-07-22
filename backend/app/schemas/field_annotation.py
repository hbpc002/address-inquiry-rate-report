from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class FieldAnnotationBase(BaseModel):
    report_type: str
    field_path: str
    field_label: str
    source: str = ""
    formula: str = ""
    description: str = ""
    sort_order: int = 0


class FieldAnnotationCreate(FieldAnnotationBase):
    pass


class FieldAnnotationUpdate(BaseModel):
    report_type: Optional[str] = None
    field_path: Optional[str] = None
    field_label: Optional[str] = None
    source: Optional[str] = None
    formula: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


class FieldAnnotationResponse(FieldAnnotationBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FieldAnnotationListResponse(BaseModel):
    items: list[FieldAnnotationResponse]
    total: int
