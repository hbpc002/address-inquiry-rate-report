from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base


class DepartmentGroup(Base):
    __tablename__ = "department_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(200), default="")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    paths = relationship(
        "DepartmentGroupPath",
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="DepartmentGroupPath.id",
    )


class DepartmentGroupPath(Base):
    __tablename__ = "department_group_paths"
    __table_args__ = (UniqueConstraint("group_id", "path", name="uq_department_group_path"),)

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("department_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    path = Column(String(500), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    group = relationship("DepartmentGroup", back_populates="paths")
