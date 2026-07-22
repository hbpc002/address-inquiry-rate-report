from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.models.database import Base


class FieldAnnotation(Base):
    __tablename__ = "field_annotations"

    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String(50), nullable=False, index=True)
    field_path = Column(String(200), nullable=False)
    field_label = Column(String(100), nullable=False)
    source = Column(Text, default="")
    formula = Column(Text, default="")
    description = Column(Text, default="")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
