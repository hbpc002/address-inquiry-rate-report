import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@localhost:5432/schedule_test')

from app.models.database import Base, engine, SessionLocal, init_db


def setup_module():
    Base.metadata.drop_all(bind=engine)
    init_db()


def test_migration_alters_decimal_precision():
    """测试迁移将 DECIMAL(5,2) 列改为 DECIMAL(7,4)"""
    from sqlalchemy import text
    from app.models.database import _migrate_db

    with engine.connect() as conn:
        for col in ('punctuality_rate', 'utilization_rate', 'attendance_rate'):
            conn.execute(text(f"ALTER TABLE schedules ALTER COLUMN {col} TYPE NUMERIC(5,2)"))
        conn.commit()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_name = 'schedules'
            AND column_name IN ('punctuality_rate', 'utilization_rate', 'attendance_rate')
        """))
        for row in result:
            assert row[1] == 5 and row[2] == 2, \
                f"{row[0]} should be NUMERIC(5,2), got NUMERIC({row[1]},{row[2]})"

    _migrate_db()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_name = 'schedules'
            AND column_name IN ('punctuality_rate', 'utilization_rate', 'attendance_rate')
        """))
        for row in result:
            assert row[1] == 7 and row[2] == 4, \
                f"{row[0]} should be NUMERIC(7,4), got NUMERIC({row[1]},{row[2]})"
