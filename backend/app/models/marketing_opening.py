from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String
from sqlalchemy.sql import func

from app.models.database import Base


class MarketingOpeningRecord(Base):
    """大模型质检台开口明细。"""

    __tablename__ = "marketing_opening_records"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(String(64), nullable=False, index=True, comment="接触记录号")
    record_time = Column(DateTime, index=True, comment="录音时间")
    record_date = Column(Date, nullable=False, index=True, comment="录音日期")
    emp_no = Column(String(50), index=True, comment="员工工号")
    emp_name = Column(String(100), comment="员工姓名")
    source_team = Column(String(100), comment="源表班组")
    active_overlay = Column(Boolean, nullable=False, default=False, comment="主动开口营销叠加包")
    opened_overlay = Column(Boolean, nullable=False, default=False, comment="已开口营销叠加包")
    active_broadband = Column(Boolean, nullable=False, default=False, comment="主动开口营销宽带")
    opened_broadband = Column(Boolean, nullable=False, default=False, comment="已开口营销宽带")
    active_mobile_new = Column(Boolean, nullable=False, default=False, comment="主动开口营销移网新装")
    opened_mobile_new = Column(Boolean, nullable=False, default=False, comment="已开口营销移网新装")
    active_terminal = Column(Boolean, nullable=False, default=False, comment="主动开口营销终端")
    opened_terminal = Column(Boolean, nullable=False, default=False, comment="已开口营销终端")
    active_package = Column(Boolean, nullable=False, default=False, comment="主动开口营销套餐")
    opened_package = Column(Boolean, nullable=False, default=False, comment="已开口营销套餐")
    five_products_opened = Column(Boolean, nullable=False, default=False, comment="五大产品已开口")
    import_batch = Column(String(50), index=True)
    created_at = Column(DateTime, server_default=func.now())
