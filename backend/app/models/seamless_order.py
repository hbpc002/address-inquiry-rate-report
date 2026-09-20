from sqlalchemy import Column, Integer, String, Date, DateTime
from sqlalchemy.sql import func
from app.models.database import Base


class SeamlessOrder(Base):
    __tablename__ = "seamless_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(50), nullable=False, index=True)
    emp_no = Column(String(50), index=True)
    order_date = Column(Date, nullable=False, index=True)
    is_completed = Column(String(10))
    city = Column(String(50))
    is_hour_short = Column(String(10))
    is_excluded = Column(String(10))
    is_duplicate = Column(String(10))
    cb_order_no = Column(String(50))
    cb_business_no = Column(String(50))
    cb_order_status = Column(String(50))
    product_name = Column(String(200))
    bandwidth_speed = Column(String(50))
    order_status = Column(String(50))
    month = Column(String(10))
    intention_emp_no = Column(String(50))
    import_batch = Column(String(50), index=True)
    created_at = Column(DateTime, server_default=func.now())