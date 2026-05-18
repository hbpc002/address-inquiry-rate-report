import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
temp_db.close()
os.environ['DATABASE_URL'] = f'sqlite:///{temp_db.name}'

from app.models.database import Base, SessionLocal, init_db
from app.models.user import User
from app.models.employee import Employee
from app.models.checkin import Checkin
from app.models.work_hour_threshold import WorkHourThreshold
from datetime import datetime


def setup_module():
    Base.metadata.drop_all(bind=engine)
    init_db()


def teardown_module():
    os.unlink(temp_db.name)


engine = create_engine(os.environ['DATABASE_URL'])
Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_create_threshold():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        
        threshold = WorkHourThreshold(
            team="测试班组",
            overtime_ratio=1.3,
            undertime_ratio=0.7,
            created_by=admin.id
        )
        db.add(threshold)
        db.commit()
        db.refresh(threshold)
        
        assert threshold.id is not None
        assert threshold.team == "测试班组"
        assert threshold.overtime_ratio == 1.3
        assert threshold.undertime_ratio == 0.7
    finally:
        db.close()


def test_query_threshold_by_team():
    db = SessionLocal()
    try:
        result = db.query(WorkHourThreshold).filter(WorkHourThreshold.team == "测试班组").first()
        assert result is not None
        assert result.overtime_ratio == 1.3
    finally:
        db.close()


def test_update_threshold():
    db = SessionLocal()
    try:
        threshold = db.query(WorkHourThreshold).filter(WorkHourThreshold.team == "测试班组").first()
        threshold.overtime_ratio = 1.5
        db.commit()
        
        result = db.query(WorkHourThreshold).filter(WorkHourThreshold.team == "测试班组").first()
        assert result.overtime_ratio == 1.5
    finally:
        db.close()


def test_delete_threshold():
    db = SessionLocal()
    try:
        threshold = db.query(WorkHourThreshold).filter(WorkHourThreshold.team == "测试班组").first()
        db.delete(threshold)
        db.commit()
        
        result = db.query(WorkHourThreshold).filter(WorkHourThreshold.team == "测试班组").first()
        assert result is None
    finally:
        db.close()


def test_multiple_teams_threshold():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        
        teams = ["班组A", "班组B", "班组C"]
        for team in teams:
            t = WorkHourThreshold(team=team, overtime_ratio=1.2, undertime_ratio=0.8, created_by=admin.id)
            db.add(t)
        db.commit()
        
        all_thresholds = db.query(WorkHourThreshold).all()
        assert len(all_thresholds) >= 3
        
        team_names = [t.team for t in all_thresholds]
        for team in teams:
            assert team in team_names
    finally:
        db.close()


def test_default_threshold_values():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        
        threshold = WorkHourThreshold(team="默认测试", created_by=admin.id)
        db.add(threshold)
        db.commit()
        db.refresh(threshold)
        
        assert threshold.overtime_ratio == 1.2
        assert threshold.undertime_ratio == 0.8
    finally:
        db.close()


def test_employee_with_role():
    db = SessionLocal()
    try:
        emp = Employee(
            emp_no="E001",
            name="测试员工",
            team="测试班组",
            dept="测试部门",
            role="组长"
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)
        
        assert emp.role == "组长"
        
        emp2 = Employee(
            emp_no="E002",
            name="测试员工2",
            team="测试班组",
            dept="测试部门",
            role="组员"
        )
        db.add(emp2)
        db.commit()
        
        leader = db.query(Employee).filter(Employee.role == "组长").first()
        assert leader is not None
        
        member = db.query(Employee).filter(Employee.role == "组员").first()
        assert member is not None
    finally:
        db.close()


def test_checkin_with_hours():
    db = SessionLocal()
    try:
        emp = db.query(Employee).first()
        if not emp:
            emp = Employee(emp_no="E003", name="签到测试", team="测试班组", role="组员")
            db.add(emp)
            db.commit()
            db.refresh(emp)
        
        checkin = Checkin(
            emp_no=emp.emp_no,
            name=emp.name,
            checkin_time=datetime(2024, 1, 1, 9, 0, 0),
            checkout_time=datetime(2024, 1, 1, 18, 0, 0),
            dept="测试部门",
            import_batch="test"
        )
        db.add(checkin)
        db.commit()
        db.refresh(checkin)
        
        assert checkin.checkin_time is not None
        assert checkin.checkout_time is not None
        
        duration = (checkin.checkout_time - checkin.checkin_time).total_seconds() / 3600
        assert duration == 9.0
    finally:
        db.close()