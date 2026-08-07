import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@localhost:5432/schedule_test')

from fastapi.testclient import TestClient
from app.models.database import Base, engine, SessionLocal, init_db
from app.models.checkin import Checkin
from app.models.employee import Employee
from app.models.schedule import Schedule
from app.models.daily_report import DailyReport
from app.main import app
from app.core.security import get_current_user
from sqlalchemy import text
from datetime import datetime, date, time

TARGET_DEPT = "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表"

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
    for table in ["schedules", "daily_reports", "checkins", "employees"]:
        db.execute(text(f"DELETE FROM {table}"))
    db.commit()


class TestTimeAnalysis:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            e1 = Employee(emp_no="T001", name="甲", team="班组一", dept=TARGET_DEPT)
            e2 = Employee(emp_no="T002", name="乙", team="班组二", dept=TARGET_DEPT)
            other = Employee(emp_no="OTHER", name="丙", team="外组", dept="其他部门")
            db.add_all([e1, e2, other])
            db.flush()
            self.emp1 = e1.id
            self.emp2 = e2.id
            # 签入/签出分布：甲 8:30 签入 16:30 签出；乙 12:05 签入 20:05 签出
            db.add(Checkin(emp_no="T001", name="甲", checkin_time=datetime(2026, 6, 10, 8, 30), checkout_time=datetime(2026, 6, 10, 16, 30), dept=TARGET_DEPT, import_batch="b1"))
            db.add(Checkin(emp_no="T002", name="乙", checkin_time=datetime(2026, 6, 10, 12, 5), checkout_time=datetime(2026, 6, 10, 20, 5), dept=TARGET_DEPT, import_batch="b1"))
            # 班次分布：甲=早班，乙=晚班
            db.add(Schedule(emp_id=e1.id, schedule_date=date(2026, 6, 10), shift_name="早班", schedule_type="正常", work_hours=8))
            db.add(Schedule(emp_id=e2.id, schedule_date=date(2026, 6, 10), shift_name="晚班", schedule_type="正常", work_hours=8, is_night=True))
            db.commit()
        finally:
            db.close()

    def test_hourly_peak_distribution(self):
        resp = client.get("/api/checkins/time-analysis", params={"year_month": "2026-06"})
        assert resp.status_code == 200
        data = resp.json()
        by_hour = {h["hour"]: h for h in data["hourly"]}
        # 8 点和 12 点各一次签入
        assert by_hour[8]["checkin_count"] == 1
        assert by_hour[12]["checkin_count"] == 1
        # 16 点和 20 点各一次签出
        assert by_hour[16]["checkout_count"] == 1
        assert by_hour[20]["checkout_count"] == 1
        # 其它小时无记录
        assert by_hour[0]["checkin_count"] == 0
        assert sum(h["checkin_count"] for h in data["hourly"]) == 2

    def test_shift_distribution_overall_and_by_team(self):
        resp = client.get("/api/checkins/time-analysis", params={"year_month": "2026-06"})
        assert resp.status_code == 200
        data = resp.json()
        overall = {s["shift_name"]: s["count"] for s in data["shifts"]["overall"]}
        assert overall.get("早班") == 1
        assert overall.get("晚班") == 1
        by_team = data["shifts"]["by_team"]
        two_maps = {(t["team"], t["shift_name"]): t["count"] for t in by_team}
        assert two_maps.get(("班组一", "早班")) == 1
        assert two_maps.get(("班组二", "晚班")) == 1
        # 其它部门的员工('OTHER')不进入统计
        assert len(by_team) == 2

    def test_night_shift_hourly_utilization(self):
        db = SessionLocal()
        try:
            db.add(DailyReport(
                emp_id=self.emp2, schedule_date=date(2026, 6, 10),
                scheduled_start=time(20, 0), scheduled_end=time(4, 0),
                actual_checkin=datetime(2026, 6, 10, 20, 0),
                actual_checkout=datetime(2026, 6, 11, 4, 0),
                scheduled_hours=8, actual_hours=8, status="正常"
            ))
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/checkins/time-analysis", params={"date": "2026-06-10"})
        assert resp.status_code == 200
        util = {u["hour"]: u for u in resp.json()["hourly_utilization"]}
        # 晚班 20:00-04:00：覆盖 20,21,22,23 与次日 0,1,2,3
        for h in [20, 21, 22, 23, 0, 1, 2, 3]:
            assert util[h]["scheduled_count"] >= 1
            assert util[h]["utilization"] == 100.0
        # 中间白天时段不应计入
        assert util[12]["scheduled_count"] == 0