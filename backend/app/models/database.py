from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # 确保所有模型已导入并注册到 metadata
    from app.models.user import User
    from app.models.employee import Employee
    from app.models.shift_type import ShiftType
    from app.models.schedule import Schedule
    from app.models.checkin import Checkin
    from app.models.daily_report import DailyReport
    from app.models.monthly_report import MonthlyReport
    from app.models.operation_log import OperationLog

    Base.metadata.create_all(bind=engine)
    _init_default_data()


def _init_default_data():
    from app.models.user import User
    from app.core.security import get_password_hash

    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                display_name="管理员",
                role="admin",
                is_active=True
            )
            db.add(admin)
            db.commit()
            print("Created admin user")
    finally:
        db.close()