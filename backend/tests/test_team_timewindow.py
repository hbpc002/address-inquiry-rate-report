import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@localhost:5432/schedule_test')

from fastapi.testclient import TestClient
from app.models.database import Base, engine, SessionLocal, init_db
from app.models.employee import Employee
from app.models.daily_report import DailyReport
from app.models.schedule import Schedule
from app.main import app
from app.core.security import get_current_user
from sqlalchemy import text
from datetime import date, datetime


_admin_user = {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "is_system": True,
    "permissions": "{}",
}


def override_get_current_user():
    return _admin_user


app.dependency_overrides[get_current_user] = override_get_current_user
client = TestClient(app)


def setup_module():
    Base.metadata.drop_all(bind=engine)
    init_db()


def teardown_module():
    app.dependency_overrides.clear()


def _clean_tables(db):
    for table in ["schedules", "daily_reports", "employees"]:
        db.execute(text(f"DELETE FROM {table}"))
    db.commit()


class TestTeamTimeWindow:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            # 全是"测试组"员工，验证时间裁剪规则
            # A 一直在职（无入职/离职时间）→ 计算
            # B 离职于 2026-05-20（早于6月）→ 6月不计
            # C 离职于 2026-06-10（当月中）→ 6月计入
            # D 入职于 2026-06-05（当月中）→ 6月计入
            data = [
                ("A001", "员工A", "在职", None, None),
                ("B001", "员工B", "离职", None, datetime(2026, 5, 20, 18, 0)),
                ("C001", "员工C", "离职", None, datetime(2026, 6, 10, 18, 0)),
                ("D001", "员工D", "在职", date(2026, 6, 5), None),
            ]
            emps = {}
            for emp_no, name, status, hire_date, deleted_at in data:
                e = Employee(emp_no=emp_no, name=name, team="测试组", dept="客服中心",
                             status=status, hire_date=hire_date, deleted_at=deleted_at)
                db.add(e)
                db.flush()
                emps[emp_no] = e.id

            self.emp_ids = emps
            # 6月工时数据
            june = {
                "A001": (8.0, 8.0),
                "B001": (8.0, 8.0),  # 不计算
                "C001": (4.0, 4.0),
                "D001": (4.0, 6.0),
            }
            for emp_no, (sched, actual) in june.items():
                db.add(DailyReport(emp_id=emps[emp_no], schedule_date=date(2026, 6, 15),
                                   scheduled_hours=sched, actual_hours=actual, status="正常"))
                db.add(Schedule(emp_id=emps[emp_no], schedule_date=date(2026, 6, 15),
                                work_hours=sched, schedule_type="正常"))
            db.commit()
        finally:
            db.close()

    def test_team_hours_headcount_uses_time_window(self):
        resp = client.get("/api/team-hours", params={"year_month": "2026-06"})
        assert resp.status_code == 200
        data = resp.json()
        row = next(d for d in data if d["team"] == "测试组")
        # 计入 A/C/D = 3 人
        assert row["emp_count"] == 3
        # 工时只统计在队人员：8 + 4 + 4 = 16 计划、8 + 4 + 6 = 18 实际
        assert row["scheduled_hours"] == 16
        assert row["actual_hours"] == 18

    def test_team_hours_excludes_employee_who_left_before_month(self):
        resp = client.get("/api/team-hours", params={"year_month": "2026-07"})
        assert resp.status_code == 200
        data = resp.json()
        row = next(d for d in data if d["team"] == "测试组")
        # 7月：A、D（C 6-10 已离职，B 5-20 已离职）
        assert row["emp_count"] == 2

    def test_team_ranking_uses_time_window(self):
        resp = client.get("/api/reports/team-ranking", params={"year_month": "2026-06"})
        assert resp.status_code == 200
        data = resp.json()
        row = next(d for d in data if d["team"] == "测试组")
        assert row["emp_count"] == 3
        assert row["total_scheduled"] == 16
        assert row["total_actual"] == 18

    def test_team_ranking_excludes_employee_hired_after_month(self):
        resp = client.get("/api/reports/team-ranking", params={"year_month": "2026-05"})
        assert resp.status_code == 200
        data = resp.json()
        row = next(d for d in data if d["team"] == "测试组")
        # 5月：A、B（5-20离职于5月内）、C（6月中旬才离职）都计入；D 6-5入职晚于5月末不计
        assert row["emp_count"] == 3
        # 5月无工时报表，但计划/实际仍按在队人员账单统计为0
        assert row["total_scheduled"] == 0
        assert row["total_actual"] == 0