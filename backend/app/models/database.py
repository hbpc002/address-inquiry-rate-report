from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)
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
    _migrate_db()
    _init_default_data()


def _migrate_db():
    """迁移数据库结构，添加缺失的列"""
    from sqlalchemy import inspect as sa_inspect, text
    from app.models.user import User

    db = SessionLocal()
    try:
        inspector = sa_inspect(engine)
        tables = inspector.get_table_names()

        if 'users' not in tables:
            return

        existing_columns = [col['name'] for col in inspector.get_columns('users')]
        column_defaults = {
            'id': 'INTEGER',
            'username': 'VARCHAR(50)',
            'password_hash': 'VARCHAR(255)',
            'display_name': 'VARCHAR(50)',
            'role': "VARCHAR(20) DEFAULT 'user'",
            'permissions': "VARCHAR(500) DEFAULT '{}'",
            'is_active': 'BOOLEAN DEFAULT 1',
            'created_at': 'DATETIME',
            'updated_at': 'DATETIME'
        }
        for col_name, col_def in column_defaults.items():
            if col_name not in existing_columns:
                sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"
                try:
                    db.execute(text(sql))
                    print(f"Added column {col_name} to users")
                except Exception as e:
                    print(f"Failed to add column {col_name}: {e}")

        # 迁移 schedules 表：添加班次信息字段
        if 'schedules' in tables:
            schedule_cols = {col['name'] for col in inspector.get_columns('schedules')}
            schedule_migrations = [
                ('shift_name', 'VARCHAR(50)'),
                ('time_segments', 'JSON' if 'postgresql' in str(engine.url) else 'TEXT'),
                ('work_hours', 'DECIMAL(4,1)'),
                ('is_night', 'BOOLEAN DEFAULT FALSE'),
            ]
            for col_name, col_def in schedule_migrations:
                if col_name not in schedule_cols:
                    sql = f"ALTER TABLE schedules ADD COLUMN {col_name} {col_def}"
                    try:
                        db.execute(text(sql))
                        print(f"Added column {col_name} to schedules")
                    except Exception as e:
                        print(f"Failed to add column {col_name}: {e}")

        # 迁移 daily_reports 表：添加分段考勤详情字段
        if 'daily_reports' in tables:
            report_cols = {col['name'] for col in inspector.get_columns('daily_reports')}
            if 'segment_details' not in report_cols:
                col_def = 'JSON' if 'postgresql' in str(engine.url) else 'TEXT'
                try:
                    db.execute(text(f"ALTER TABLE daily_reports ADD COLUMN segment_details {col_def}"))
                    print("Added column segment_details to daily_reports")
                except Exception as e:
                    print(f"Failed to add column segment_details: {e}")

        db.commit()
    except Exception as e:
        print(f"Migration error: {e}")
        db.rollback()
    finally:
        db.close()


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