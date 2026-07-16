import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@localhost:5432/schedule_test')

from fastapi.testclient import TestClient
from app.models.database import Base, engine, SessionLocal, init_db
from app.models.checkin import Checkin
from app.models.employee import Employee
from app.main import app
from app.core.security import get_current_user
from sqlalchemy import text
from datetime import datetime, date, timedelta

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
    for table in ["daily_reports", "workloads", "checkins", "schedules", "employees"]:
        db.execute(text(f"DELETE FROM {table}"))
    db.commit()


def _create_test_employees(db):
    from app.models.employee import Employee
    emps = [
        Employee(emp_no="E001", name="张三", team="热线一组", dept="服务部", status="在职"),
        Employee(emp_no="E002", name="李四", team="热线二组", dept="服务部", status="在职"),
        Employee(emp_no="E003", name="王五", team="热线一组", dept="服务部", status="在职"),
    ]
    for e in emps:
        db.add(e)
    db.commit()
    for e in emps:
        db.refresh(e)
    return {e.emp_no: e for e in emps}


def _create_test_daily_reports(db, emp_map):
    from app.models.daily_report import DailyReport
    today = date.today()
    reports = []
    for emp_no, emp in emp_map.items():
        for i in range(3):
            d = today - timedelta(days=i)
            reports.append(DailyReport(
                emp_id=emp.id,
                schedule_date=d,
                status="正常",
                scheduled_hours=8,
                actual_hours=8,
                overtime_hours=0,
                late_minutes=0,
                early_minutes=0,
            ))
    for r in reports:
        db.add(r)
    db.commit()


def _create_test_checkins(db, emp_map):
    from app.models.checkin import Checkin
    today = date.today()
    dept = "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表"
    for emp_no, emp in emp_map.items():
        for i in range(2):
            d = today - timedelta(days=i)
            checkin = Checkin(
                emp_no=emp_no,
                name=emp.name,
                dept=dept,
                checkin_time=datetime(d.year, d.month, d.day, 8, 0),
                checkout_time=datetime(d.year, d.month, d.day, 17, 0),
                import_batch="test-export",
            )
            db.add(checkin)
    db.commit()


def _create_test_workloads(db, emp_map):
    from app.models.workload import Workload
    today = date.today()
    for emp_no in emp_map:
        for i in range(2):
            d = today - timedelta(days=i)
            w = Workload(
                account=emp_no,
                date=d,
                metrics={
                    "呼入人工服务-人工服务-通话次数": 50,
                    "呼入人工服务-工单-生成总量": 10,
                    "呼出服务-人工呼出呼叫量": 5,
                    "总体-工作总时长(秒)": 28800,
                    "总体-工时利用率": 0.85,
                    "呼入人工服务-人工服务-通话总时长(秒)": 14400,
                    "呼入人工服务-人工服务-通话均长(秒)": 288,
                    "人工服务-满意度-满意率": 0.95,
                },
            )
            db.add(w)
    db.commit()


class TestExportEndpoints:

    def test_export_checkin_report(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            emp_map = _create_test_employees(db)
            _create_test_checkins(db, emp_map)

            today = date.today().isoformat()

            # Test export with date
            resp = client.get(f"/api/checkins/report/export?date={today}")
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/csv")
            assert "filename=" in resp.headers["content-disposition"]
            body = resp.content.decode("utf-8")
            assert "账号" in body
            assert "E001" in body
            assert "张三" in body

            # Test export without perms - should use admin which has all perms
            resp = client.get("/api/checkins/report/export")
            assert resp.status_code == 200
        finally:
            db.close()

    def test_export_checkin_report_excludes_no_team(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            TARGET_DEPT = "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表"

            emp_with_team = Employee(emp_no="E001", name="张三", team="热线一组", dept="服务部", status="在职")
            emp_no_team = Employee(emp_no="E002", name="李四", team="", dept="服务部", status="在职")
            db.add_all([emp_with_team, emp_no_team])
            db.commit()

            today = date.today()
            for emp_no, name in [("E001", "张三"), ("E002", "李四")]:
                db.add(Checkin(
                    emp_no=emp_no, name=name, dept=TARGET_DEPT,
                    checkin_time=datetime(today.year, today.month, today.day, 8, 0),
                    checkout_time=datetime(today.year, today.month, today.day, 17, 0),
                    import_batch="test-export-no-team",
                ))
            db.commit()

            resp = client.get(f"/api/checkins/report/export?date={today.isoformat()}")
            assert resp.status_code == 200
            body = resp.content.decode("utf-8")
            assert "E001" in body
            assert "张三" in body
            assert "E002" not in body
            assert "李四" not in body
        finally:
            db.close()

    def test_export_workload_report(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            emp_map = _create_test_employees(db)
            _create_test_workloads(db, emp_map)

            today = date.today().isoformat()
            resp = client.get(f"/api/workloads/report/export?start_date={today}&end_date={today}")
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/csv")
            body = resp.content.decode("utf-8")
            assert "账号" in body
            assert "E001" in body
        finally:
            db.close()

    def test_export_dashboard(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            emp_map = _create_test_employees(db)
            _create_test_daily_reports(db, emp_map)
            _create_test_workloads(db, emp_map)

            ym = date.today().strftime("%Y-%m")
            resp = client.get(f"/api/reports/dashboard-export?year_month={ym}")
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/csv")
            body = resp.content.decode("utf-8")
            assert "== 月度统计 ==" in body
            assert "== 每日工时趋势 ==" in body
            assert "== 班组工时 ==" in body
            assert "E001" in body
        finally:
            db.close()

    def test_export_dashboard_without_month(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            emp_map = _create_test_employees(db)
            _create_test_daily_reports(db, emp_map)

            resp = client.get("/api/reports/dashboard-export")
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/csv")
        finally:
            db.close()

    def test_export_efficiency_employee(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            emp_map = _create_test_employees(db)
            _create_test_daily_reports(db, emp_map)

            ym = date.today().strftime("%Y-%m")
            resp = client.get(f"/api/reports/efficiency-export?type=employee&year_month={ym}")
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/csv")
            body = resp.content.decode("utf-8")
            assert "工号" in body
            assert "E001" in body
        finally:
            db.close()

    def test_export_efficiency_warning(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            emp_map = _create_test_employees(db)
            _create_test_daily_reports(db, emp_map)

            ym = date.today().strftime("%Y-%m")
            resp = client.get(f"/api/reports/efficiency-export?type=warning&year_month={ym}")
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/csv")
            body = resp.content.decode("utf-8")
            assert "预警类型" in body
        finally:
            db.close()

    def test_export_efficiency_ranking(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            emp_map = _create_test_employees(db)
            _create_test_daily_reports(db, emp_map)

            ym = date.today().strftime("%Y-%m")
            resp = client.get(f"/api/reports/efficiency-export?type=ranking&year_month={ym}")
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/csv")
            body = resp.content.decode("utf-8")
            assert "排名" in body
            assert "E001" in body
        finally:
            db.close()

    def test_export_efficiency_trend_no_emp(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            emp_map = _create_test_employees(db)
            _create_test_daily_reports(db, emp_map)

            resp = client.get("/api/reports/efficiency-export?type=trend")
            assert resp.status_code == 200
            body = resp.content.decode("utf-8")
            assert "请选择员工" in body
        finally:
            db.close()

    def test_export_efficiency_trend_with_emp(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            emp_map = _create_test_employees(db)
            _create_test_daily_reports(db, emp_map)

            ym = date.today().strftime("%Y-%m")
            resp = client.get(f"/api/reports/efficiency-export?type=trend&emp_no=E001&start_month={ym}&end_month={ym}")
            assert resp.status_code == 200
            body = resp.content.decode("utf-8")
            assert "月份" in body
            assert "E001" in body
        finally:
            db.close()

    def test_permission_denied_export(self):
        def no_perm_user():
            return {
                "id": 2,
                "username": "viewer",
                "role": "viewer",
                "is_system": False,
                "permissions": "{}",
            }

        app.dependency_overrides[get_current_user] = no_perm_user
        try:
            resp = client.get("/api/checkins/report/export?date=2024-01-01")
            assert resp.status_code == 403
        finally:
            app.dependency_overrides[get_current_user] = override_get_current_user
