from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.models.database import Base


class AppConfig(Base):
    """通用的键值配置表（如日志清理策略、智能体悬浮按钮自定义等）。"""

    __tablename__ = "app_configs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), nullable=False, unique=True, index=True)
    value = Column(String(2000), nullable=False, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
