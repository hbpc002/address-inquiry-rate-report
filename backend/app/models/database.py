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
    from app.models.user import User
    from app.models.role import Role
    from app.models.employee import Employee
    from app.models.shift_type import ShiftType
    from app.models.schedule import Schedule
    from app.models.checkin import Checkin
    from app.models.daily_report import DailyReport
    from app.models.monthly_report import MonthlyReport
    from app.models.operation_log import OperationLog
    from app.models.work_hour_threshold import WorkHourThreshold
    from app.models.attendance_config import AttendanceConfig

    Base.metadata.create_all(bind=engine)
    _migrate_db()
    _init_default_data()


def _migrate_db():
    from sqlalchemy import inspect as sa_inspect, text
    from app.models.user import User
    from app.models.role import Role

    db = SessionLocal()
    try:
        inspector = sa_inspect(engine)
        tables = inspector.get_table_names()

        if 'users' in tables:
            existing_columns = [col['name'] for col in inspector.get_columns('users')]
            column_defaults = {
                'id': 'INTEGER',
                'username': 'VARCHAR(50)',
                'password_hash': 'VARCHAR(255)',
                'display_name': 'VARCHAR(50)',
                'role': "VARCHAR(20) DEFAULT 'user'",
                'role_id': 'INTEGER',
                'is_active': 'BOOLEAN DEFAULT TRUE',
                'created_at': 'TIMESTAMP',
                'updated_at': 'TIMESTAMP'
            }
            for col_name, col_def in column_defaults.items():
                if col_name not in existing_columns:
                    sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"
                    try:
                        db.execute(text(sql))
                        print(f"Added column {col_name} to users")
                    except Exception as e:
                        print(f"Failed to add column {col_name}: {e}")

        if 'schedules' in tables:
            schedule_cols = {col['name'] for col in inspector.get_columns('schedules')}
            schedule_migrations = [
                ('shift_name', 'VARCHAR(50)'),
                ('time_segments', 'JSON'),
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

        if 'daily_reports' in tables:
            report_cols = {col['name'] for col in inspector.get_columns('daily_reports')}
            if 'segment_details' not in report_cols:
                col_def = 'JSON'
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
    from app.models.role import Role
    from app.core.security import get_password_hash
    from app.core.permissions import get_default_permissions
    import json

    db = SessionLocal()
    try:
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(
                name="admin",
                description="超级管理员，拥有所有权限",
                permissions=json.dumps(get_default_permissions("admin"), ensure_ascii=False),
                is_system=True,
            )
            db.add(admin_role)
            db.flush()
            print("Created admin role")

        manager_role = db.query(Role).filter(Role.name == "manager").first()
        if not manager_role:
            manager_role = Role(
                name="manager",
                description="经理，可管理数据和上传",
                permissions=json.dumps(get_default_permissions("manager"), ensure_ascii=False),
                is_system=False,
            )
            db.add(manager_role)
            db.flush()
            print("Created manager role")

        user_role = db.query(Role).filter(Role.name == "user").first()
        if not user_role:
            user_role = Role(
                name="user",
                description="普通用户，只可查看数据",
                permissions=json.dumps(get_default_permissions("user"), ensure_ascii=False),
                is_system=False,
            )
            db.add(user_role)
            db.flush()
            print("Created user role")

        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                display_name="管理员",
                role="admin",
                role_id=admin_role.id,
                is_active=True,
            )
            db.add(admin_user)
            print("Created admin user")
        elif not admin_user.role_id:
            admin_user.role_id = admin_role.id

        existing_users = db.query(User).filter(User.username != "admin").all()
        for u in existing_users:
            if not u.role_id:
                if u.role == "manager" and manager_role:
                    u.role_id = manager_role.id
                elif user_role:
                    u.role_id = user_role.id

        db.commit()
    finally:
        db.close()