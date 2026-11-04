"""旧页面固定热线运营组范围，营销/员工页面仍按部门组隔离。"""
import os
from datetime import date, datetime, time
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'backend'
sys.path.insert(0, str(BASE))

from app.models.database import Base, get_db
from app.models.checkin import Checkin
from app.models.daily_report import DailyReport
from app.models.employee import Employee
from app.models.role import Role
from app.models.schedule import Schedule
from app.models.seamless_order import SeamlessOrder
from app.models.training_record import TrainingRecord
from app.models.user import User
from app.models.workload import Workload
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.main import app

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:admin123%40kf@localhost:5432/schedule_test",
)
engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

HOTLINE = settings.LEGACY_SCOPE_DEPT_PATH
DEPT_A = f"{HOTLINE}>>A部门"
DEPT_A2 = f"{DEPT_A}>>A2子部门"
DEPT_B = "广西分公司>>省中心>>客户服务营销中心>>市场部>>B部门"
DAY = date(2026, 11, 2)
TEAM_A = "热线一班"
TEAM_B = "市场一班"


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        role = Role(
            name="legacy_dept_role",
            data_scope="dept",
            employee_write_scope="dept",
            permissions=(
                '{"dashboard.view": true, "reports.view": true, "reports.export": true, '
                '"reports.dashboard_export": true, "reports.recalculate": true, '
                '"checkins.view": true, "checkins.delete": true, "checkin_report.view": true, '
                '"checkin_report.export": true, "schedules.view": true, "schedules.create": true, '
                '"schedules.edit": true, "schedules.delete": true, "workload.view": true, '
                '"workload.delete": true, "workload_report.view": true, '
                '"workload_report.export": true, "broadband.view": true, "broadband.delete": true, '
                '"broadband_report.view": true, "broadband_report.export": true, '
                '"training_records.view": true, "training_records.create": true, '
                '"training_records.delete": true, "employees.view": true}'
            ),
        )
        db.add(role)
        db.commit()

        dept_user = User(
            username="legacy_dept_user",
            password_hash=get_password_hash("pass"),
            display_name="市场部用户",
            dept=DEPT_B,
            role=role.name,
            role_id=role.id,
        )
        admin = User(
            username="legacy_admin",
            password_hash=get_password_hash("pass"),
            display_name="管理员",
            role="admin",
        )
        db.add_all([dept_user, admin])
        db.commit()

        emp_a = Employee(
            emp_no="HOT001", name="热线员工", team=TEAM_A, dept=DEPT_A,
            role="组员", status="在职",
        )
        emp_a2 = Employee(
            emp_no="HOT002", name="热线子部门员工", team=TEAM_A, dept=DEPT_A2,
            role="组员", status="在职",
        )
        emp_b = Employee(
            emp_no="MKT001", name="市场部员工", team=TEAM_B, dept=DEPT_B,
            role="组员", status="在职",
        )
        db.add_all([emp_a, emp_a2, emp_b])
        db.commit()

        db.add_all([
            DailyReport(
                emp_id=emp_a.id, schedule_date=DAY, schedule_type="正常",
                scheduled_start=time(9, 0), scheduled_end=time(18, 0),
                scheduled_hours=8.0, actual_hours=8.0, status="正常",
                late_minutes=0, early_minutes=0, overtime_hours=0,
            ),
            DailyReport(
                emp_id=emp_b.id, schedule_date=DAY, schedule_type="正常",
                scheduled_start=time(9, 0), scheduled_end=time(18, 0),
                scheduled_hours=8.0, actual_hours=8.0, status="正常",
                late_minutes=0, early_minutes=0, overtime_hours=0,
            ),
        ])
        schedule_a = Schedule(
            emp_id=emp_a.id, schedule_date=DAY, shift_name="行政班",
            time_segments=[], work_hours=8.0, schedule_type="正常",
        )
        schedule_b = Schedule(
            emp_id=emp_b.id, schedule_date=DAY, shift_name="行政班",
            time_segments=[], work_hours=8.0, schedule_type="正常",
        )
        db.add_all([schedule_a, schedule_b])
        db.add_all([
            Checkin(
                emp_no="HOT001", name="热线员工", dept=DEPT_A,
                checkin_time=datetime(2026, 11, 2, 9, 0),
                checkout_time=datetime(2026, 11, 2, 18, 0), import_batch="legacy",
            ),
            Checkin(
                emp_no="MKT001", name="市场部员工", dept=DEPT_B,
                checkin_time=datetime(2026, 11, 2, 9, 0),
                checkout_time=datetime(2026, 11, 2, 18, 0), import_batch="legacy",
            ),
        ])
        metrics = {
            "呼入人工服务-人工服务-通话次数": 10,
            "总体-工作总时长(秒)": 3600,
            "呼入人工服务-工单-生成总量": 2,
            "呼出服务-人工呼出呼叫量": 1,
            "操作次数及时长-示忙次数": 3,
            "操作次数及时长-示忙时长(秒)": 60,
            "操作次数及时长-休息次数": 2,
            "操作次数及时长-休息时长(秒)": 120,
        }
        db.add_all([
            Workload(
                date=DAY, account="HOT001", name="热线员工", emp_no="HOT001",
                team_desc=f"{DEPT_A}", metrics=metrics, import_batch="legacy",
            ),
            Workload(
                date=DAY, account="MKT001", name="市场部员工", emp_no="MKT001",
                team_desc=f"{DEPT_B}", metrics=metrics, import_batch="legacy",
            ),
        ])
        db.add_all([
            SeamlessOrder(
                order_no="ORDER-HOT", emp_no="HOT001", order_date=DAY,
                is_completed="是", is_excluded="否", is_duplicate="否",
                city="南宁", import_batch="legacy",
            ),
            SeamlessOrder(
                order_no="ORDER-MKT", emp_no="MKT001", order_date=DAY,
                is_completed="是", is_excluded="否", is_duplicate="否",
                city="南宁", import_batch="legacy",
            ),
        ])
        db.add_all([
            TrainingRecord(
                emp_no="HOT001", record_date=DAY, start_time="09:00",
                end_time="10:00", duration_minutes=60, type="培训",
            ),
            TrainingRecord(
                emp_no="MKT001", record_date=DAY, start_time="09:00",
                end_time="10:00", duration_minutes=60, type="培训",
            ),
        ])
        db.commit()

        global DEPT_TOKEN, ADMIN_TOKEN, EMP_B_ID, SCHEDULE_B_ID
        global CHECKIN_B_ID, WORKLOAD_B_ID, ORDER_B_ID, TRAINING_B_ID
        DEPT_TOKEN = create_access_token(data={"sub": str(dept_user.id)})
        ADMIN_TOKEN = create_access_token(data={"sub": str(admin.id)})
        EMP_B_ID = emp_b.id
        SCHEDULE_B_ID = schedule_b.id
        CHECKIN_B_ID = db.query(Checkin).filter(Checkin.emp_no == "MKT001").first().id
        WORKLOAD_B_ID = db.query(Workload).filter(Workload.account == "MKT001").first().id
        ORDER_B_ID = db.query(SeamlessOrder).filter(SeamlessOrder.order_no == "ORDER-MKT").first().id
        TRAINING_B_ID = db.query(TrainingRecord).filter(TrainingRecord.emp_no == "MKT001").first().id
    finally:
        db.close()
    yield


def test_dashboard_and_reports_are_hotline_only():
    headers = auth_header(DEPT_TOKEN)

    stats = client.get("/api/stats", params={"year_month": "2026-11"}, headers=headers)
    assert stats.status_code == 200
    data = stats.json()
    assert data["employee_count"] == 2
    assert data["monthly_total_days"] == 1
    assert data["latest_data_date"] == DAY.isoformat()

    trend = client.get("/api/daily-trend", params={"year_month": "2026-11"}, headers=headers)
    assert trend.status_code == 200
    day = next(item for item in trend.json() if item["date"] == DAY.isoformat())
    assert day["total"] == 1

    assert {item["team"] for item in client.get("/api/teams", headers=headers).json()} == {TEAM_A}
    assert {item["dept"] for item in client.get("/api/departments", headers=headers).json()} == {DEPT_A, DEPT_A2}
    assert {item["team"] for item in client.get("/api/team-hours", params={"year_month": "2026-11"}, headers=headers).json()} == {TEAM_A}

    daily = client.get("/api/reports/daily", params={"schedule_date": DAY.isoformat()}, headers=headers).json()
    assert daily["total"] == 1
    assert daily["items"][0]["emp_no"] == "HOT001"

    monthly = client.get("/api/reports/month-summary", params={"year_month": "2026-11"}, headers=headers).json()
    assert monthly["total"] == 2
    assert {item["emp_no"] for item in monthly["items"]} == {"HOT001", "HOT002"}

    ranking = client.get("/api/reports/team-ranking", params={"year_month": "2026-11"}, headers=headers).json()
    assert {item["team"] for item in ranking} == {TEAM_A}

    export = client.get(
        "/api/reports/dashboard-export", params={"year_month": "2026-11"}, headers=headers
    )
    assert export.status_code == 200
    text = export.content.decode("utf-8")
    assert TEAM_A in text
    assert TEAM_B not in text

    admin_stats = client.get(
        "/api/stats", params={"year_month": "2026-11"}, headers=auth_header(ADMIN_TOKEN)
    ).json()
    assert admin_stats["employee_count"] == 3
    assert admin_stats["monthly_total_days"] == 2


def test_checkins_and_schedules_reject_other_departments():
    headers = auth_header(DEPT_TOKEN)

    checkins = client.get("/api/checkins", headers=headers).json()
    assert checkins["total"] == 1
    assert checkins["items"][0]["emp_no"] == "HOT001"
    assert {item["dept"] for item in client.get("/api/checkins/departments", headers=headers).json()} == {DEPT_A}

    report = client.get("/api/checkins/report", params={"date": DAY.isoformat()}, headers=headers)
    assert report.status_code == 200
    assert {item["emp_no"] for item in report.json()["items"]} == {"HOT001"}

    personal = client.get(
        "/api/checkins/personal-report",
        params={"emp_no": "MKT001", "start_date": DAY.isoformat(), "end_date": DAY.isoformat()},
        headers=headers,
    )
    assert personal.status_code == 404

    schedules = client.get(
        "/api/schedules", params={"schedule_date": DAY.isoformat()}, headers=headers
    ).json()
    assert schedules["total"] == 1
    assert schedules["items"][0]["emp_no"] == "HOT001"

    update_other = client.put(
        f"/api/schedules/{SCHEDULE_B_ID}", json={"notes": "越权"}, headers=headers
    )
    assert update_other.status_code == 404
    delete_other = client.delete(f"/api/schedules/{SCHEDULE_B_ID}", headers=headers)
    assert delete_other.status_code == 404

    delete_checkin = client.delete(f"/api/checkins/{CHECKIN_B_ID}", headers=headers)
    assert delete_checkin.status_code == 404


def test_workload_broadband_and_training_are_hotline_only():
    headers = auth_header(DEPT_TOKEN)

    report = client.get(
        "/api/workloads/report",
        params={"start_date": DAY.isoformat(), "end_date": DAY.isoformat()},
        headers=headers,
    )
    assert report.status_code == 200
    items = report.json()["items"]
    assert [item["account"] for item in items] == ["HOT001"]

    production = client.get(
        "/api/workloads/daily-production",
        params={"year_month": "2026-11"},
        headers=headers,
    ).json()
    day = next(item for item in production if item["date"] == DAY.isoformat())
    assert day["people_count"] == 1
    assert day["call_count"] == 10

    team_prod = client.get(
        "/api/workloads/team-production", params={"year_month": "2026-11"}, headers=headers
    ).json()
    assert {item["team"] for item in team_prod} == {TEAM_A}

    export = client.get(
        "/api/workloads/report/export",
        params={"start_date": DAY.isoformat(), "end_date": DAY.isoformat()},
        headers=headers,
    )
    assert export.status_code == 200
    text = export.content.decode("utf-8")
    assert "HOT001" in text
    assert "MKT001" not in text

    orders = client.get("/api/broadband/orders", headers=headers).json()
    assert orders["total"] == 1
    assert orders["items"][0]["emp_no"] == "HOT001"
    broadband_report = client.get(
        "/api/broadband/report",
        params={"start_date": DAY.isoformat(), "end_date": DAY.isoformat()},
        headers=headers,
    ).json()
    assert {item["emp_no"] for item in broadband_report["items"]} == {"HOT001"}

    training = client.get("/api/training-records", headers=headers).json()
    assert training["total"] == 1
    assert training["items"][0]["emp_no"] == "HOT001"

    assert client.delete(f"/api/workloads/{WORKLOAD_B_ID}", headers=headers).status_code == 404
    assert client.delete(f"/api/broadband/orders/{ORDER_B_ID}", headers=headers).status_code == 404
    assert client.delete(f"/api/training-records/{TRAINING_B_ID}", headers=headers).status_code == 404


def test_employee_page_keeps_department_scope_and_supports_legacy_lookup():
    headers = auth_header(DEPT_TOKEN)

    legacy = client.get("/api/employees", params={"scope": "legacy"}, headers=headers).json()
    assert legacy["total"] == 2
    assert {item["emp_no"] for item in legacy["items"]} == {"HOT001", "HOT002"}

    dept = client.get("/api/employees", params={"scope": "dept"}, headers=headers).json()
    assert dept["total"] == 1
    assert dept["items"][0]["emp_no"] == "MKT001"

    legacy_teams = client.get(
        "/api/employees/teams", params={"scope": "legacy"}, headers=headers
    ).json()
    assert {item["team"] for item in legacy_teams} == {TEAM_A}

    admin_legacy = client.get(
        "/api/employees", params={"scope": "legacy"}, headers=auth_header(ADMIN_TOKEN)
    ).json()
    assert admin_legacy["total"] == 3
