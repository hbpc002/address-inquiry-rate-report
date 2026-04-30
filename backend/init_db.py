import sys
sys.path.insert(0, '.')

from app.models.database import Base, engine, SessionLocal
from app.models import User, ShiftType
from app.core.security import get_password_hash

def init_default_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.username == "admin").first()
        if not existing_user:
            admin = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                display_name="管理员",
                role="admin",
                is_active=True
            )
            db.add(admin)
            print("Created admin user")

        shift_types = [
            {"shift_name": "行政班", "time_segments": [{"start": "09:00", "end": "18:00"}], "work_hours": 8.0, "color": "#409EFF", "is_night": False},
            {"shift_name": "早班", "time_segments": [{"start": "08:00", "end": "16:00"}], "work_hours": 8.0, "color": "#67C23A", "is_night": False},
            {"shift_name": "中班", "time_segments": [{"start": "16:00", "end": "24:00"}], "work_hours": 8.0, "color": "#E6A23C", "is_night": False},
            {"shift_name": "晚班", "time_segments": [{"start": "24:00", "end": "08:00"}], "work_hours": 8.0, "color": "#909399", "is_night": True},
        ]

        for st in shift_types:
            existing = db.query(ShiftType).filter(ShiftType.shift_name == st["shift_name"]).first()
            if not existing:
                db.add(ShiftType(**st))

        db.commit()
        print("Initialized default data")
    finally:
        db.close()

if __name__ == "__main__":
    init_default_data()