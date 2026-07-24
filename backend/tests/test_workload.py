import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@localhost:5432/schedule_test')

from fastapi.testclient import TestClient
from app.models.database import Base, engine, SessionLocal, init_db
from app.models.workload import Workload
from app.main import app
from app.core.security import get_current_user
from sqlalchemy import text
from datetime import datetime, date
import io
import pandas as pd
import openpyxl

TARGET_DEPT = "广西分公司>>省中心>>客户服务营销中心"
TEAM_DESC = f"{TARGET_DEPT}>>热线运营组>>10010热线客服代表"


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
    for table in ["workloads", "employees"]:
        db.execute(text(f"DELETE FROM {table}"))
    db.commit()

def _create_test_employees(db):
    from app.models.employee import Employee
    employees_data = [
        ("STTR00001", "张三", "热线一组"),
        ("STTR00002", "李四", "热线二组"),
        ("STTR00003", "王五", "热线一组"),
        ("STTR00004", "赵六", "热线二组"),
    ]
    for emp_no, name, team in employees_data:
        existing = db.query(Employee).filter(Employee.emp_no == emp_no).first()
        if not existing:
            db.add(Employee(emp_no=emp_no, name=name, team=team, dept="客服中心"))
    db.commit()


def _make_xlsx(rows: list[list], include_title=True) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet_0"

    if include_title:
        ws.append(["日期", "2026-06-28", "2026-06-28", "省份(基地)", "59"] + [""] * 108)
        ws.append(["03客服代表工作量和操作情况统计表-时间段_日"] + [""] * 112)

    header = ["日期", "省份/基地", "账号", "姓名", "工号", "班组描述",
              "总体-签入次数", "总体-签出次数", "总体-工作总时长(秒)", "总体-工时利用率",
              "呼入人工服务-人工服务-通话次数", "呼入人工服务-人工服务-通话总时长(秒)",
              "呼入人工服务-人工服务-通话均长(秒)", "呼入人工服务-人工服务-服务后整理总时长(秒)",
              "人工服务-满意度-非常满意量", "人工服务-满意度-满意率",
              "呼入人工服务-工单-生成总量", "呼出服务-人工呼出呼叫量",
              "服务量合计-通话量", "操作次数及时长-示忙次数"]
    total_cols = 113
    padded_header = header + [""] * (total_cols - len(header))
    ws.append(padded_header)

    for row in rows:
        padded = list(row) + [""] * (total_cols - len(row))
        ws.append(padded)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


class TestWorkloadImport:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
        finally:
            db.close()

    def _upload_xlsx(self, xlsx_bytes: io.BytesIO, filename="test.xlsx"):
        data = {"file": (filename, xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        return client.post("/api/workloads/import", files=data)

    def test_import_normal(self):
        rows = [
            ["20260628", "广西", "STTR00001", "张三", "1001", TEAM_DESC, 5, 5, 28800, 0.85, 30, 5400, 180, 600, 25, 98.5, 10, 8, 35, 3],
        ]
        resp = self._upload_xlsx(_make_xlsx(rows))
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert len(data["batch"]) == 8

    def test_import_multiple_rows(self):
        rows = [
            ["20260628", "广西", "STTR00001", "张三", "1001", TEAM_DESC, 5, 5, 28800, 0.85, 30, 5400, 180, 600, 25, 98.5, 10, 8, 35, 3],
            ["20260628", "广西", "STTR00002", "李四", "1002", TEAM_DESC, 3, 3, 25200, 0.75, 20, 3600, 180, 400, 18, 95.0, 5, 3, 23, 2],
            ["20260628", "广东", "STTR00003", "王五", "1003", TEAM_DESC, 4, 4, 27000, 0.80, 25, 4500, 180, 500, 20, 96.0, 8, 5, 29, 4],
        ]
        resp = self._upload_xlsx(_make_xlsx(rows))
        assert resp.status_code == 200
        assert resp.json()["count"] == 3

    def test_import_skips_heji_row(self):
        rows = [
            ["20260628", "广西", "STTR00001", "张三", "1001", TEAM_DESC, 5, 5, 28800, 0.85, 30, 5400, 180, 600, 25, 98.5, 10, 8, 35, 3],
            ["合计", "", "", "", "", "", 8, 8, 54000, 0.00, 50, 9000, 0, 0, 0, 0, 0, 0, 0, 0],
        ]
        resp = self._upload_xlsx(_make_xlsx(rows))
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_import_skips_empty_account(self):
        rows = [
            ["20260628", "广西", "", "", "", "", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ]
        resp = self._upload_xlsx(_make_xlsx(rows))
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_import_empty_file(self):
        data = {"file": ("empty.xlsx", io.BytesIO(b"not an excel"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = client.post("/api/workloads/import", files=data)
        assert resp.status_code == 400

    def test_import_skips_non_target_dept(self):
        rows = [
            ["20260628", "广西", "NOT_EXIST", "未知人", "9999", "其他部门>>其他组", 1, 1, 3600, 0.5, 5, 900, 180, 100, 2, 90.0, 1, 0, 5, 0],
        ]
        resp = self._upload_xlsx(_make_xlsx(rows))
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_import_replaces_old_records_on_same_date(self):
        rows1 = [
            ["20260628", "广西", "STTR00001", "张三", "1001", TEAM_DESC, 5, 5, 28800, 0.85, 30, 5400, 180, 600, 25, 98.5, 10, 8, 35, 3],
        ]
        resp1 = self._upload_xlsx(_make_xlsx(rows1))
        assert resp1.status_code == 200
        assert resp1.json()["count"] == 1

        rows2 = [
            ["20260628", "广西", "STTR00001", "张三", "1001", TEAM_DESC, 6, 6, 30000, 0.90, 35, 6000, 180, 700, 28, 99.0, 12, 10, 40, 5],
        ]
        resp2 = self._upload_xlsx(_make_xlsx(rows2))
        assert resp2.status_code == 200
        assert resp2.json()["count"] == 1

        db = SessionLocal()
        try:
            records = db.query(Workload).all()
            assert len(records) == 1
            assert records[0].metrics["总体-签入次数"] == 6
        finally:
            db.close()

    def test_import_keeps_excel_name(self):
        rows = [
            ["20260628", "广西", "STTR00001", "张**", "1001", TEAM_DESC, 5, 5, 28800, 0.85, 30, 5400, 180, 600, 25, 98.5, 10, 8, 35, 3],
        ]
        resp = self._upload_xlsx(_make_xlsx(rows))
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

        db = SessionLocal()
        try:
            record = db.query(Workload).first()
            assert record.name == "张**"
            assert TARGET_DEPT in record.team_desc
        finally:
            db.close()


class TestWorkloadList:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            _create_test_employees(db)
            records = [
                Workload(date=date(2026, 6, 28), province="广西", account="STTR00001", name="张三", emp_no="1001", team_desc="热线一组", metrics={"通话次数": 30}, import_batch="batch001"),
                Workload(date=date(2026, 6, 28), province="广东", account="STTR00002", name="李四", emp_no="1002", team_desc="热线二组", metrics={"通话次数": 20}, import_batch="batch001"),
                Workload(date=date(2026, 6, 29), province="广西", account="STTR00003", name="王五", emp_no="1003", team_desc="热线一组", metrics={"通话次数": 25}, import_batch="batch002"),
            ]
            for r in records:
                db.add(r)
            db.commit()
        finally:
            db.close()

    def test_list_all(self):
        resp = client.get("/api/workloads")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_list_filter_by_date(self):
        resp = client.get("/api/workloads", params={"workload_date": "2026-06-28"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_list_filter_by_account(self):
        resp = client.get("/api/workloads", params={"account": "STTR00001"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_filter_by_batch(self):
        resp = client.get("/api/workloads", params={"import_batch": "batch002"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_filter_by_name(self):
        resp = client.get("/api/workloads", params={"name": "张三"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_filter_by_name_masked_workload(self):
        """List name filter should match Employee.name even when Workload.name is masked"""
        db = SessionLocal()
        try:
            db.add(Workload(
                date=date(2026, 6, 29), province="广西", account="STTR00004",
                name="赵*", emp_no="1004", team_desc="热线二组",
                metrics={"通话次数": 15}, import_batch="batch002"
            ))
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/workloads", params={"name": "赵六"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["account"] == "STTR00004"

    def test_list_filter_by_name_partial(self):
        """List name filter should support partial match against Employee.name"""
        resp = client.get("/api/workloads", params={"name": "五"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["account"] == "STTR00003"

    def test_list_filter_by_name_no_match(self):
        """List name filter with non-existent name should return empty"""
        resp = client.get("/api/workloads", params={"name": "不存在"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    def test_list_pagination(self):
        resp = client.get("/api/workloads", params={"page": 1, "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3

    def test_list_excludes_resigned_employee(self):
        db = SessionLocal()
        try:
            from app.models.employee import Employee
            resigned = Employee(emp_no="STTR0099", name="离职员工", team="热线一组", status="离职")
            db.add(resigned)
            db.add(Workload(
                date=date(2026, 6, 28), province="广西", account="STTR0099",
                name="离职员工", emp_no="1099", team_desc="热线一组",
                metrics={"通话次数": 10}, import_batch="batch_resigned"
            ))
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/workloads")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        accounts = [item["account"] for item in data["items"]]
        assert "STTR0099" not in accounts


class TestWorkloadDelete:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            from app.models.employee import Employee
            for i in range(3):
                existing = db.query(Employee).filter(Employee.emp_no == f"STTR{i:05d}").first()
                if not existing:
                    db.add(Employee(emp_no=f"STTR{i:05d}", name=f"员工{i+1}", team="热线一组", dept="客服中心"))
            db.commit()
            for i, day in enumerate([28, 29, 30]):
                w = Workload(
                    date=date(2026, 6, day),
                    province="广西",
                    account=f"STTR{i:05d}",
                    name=f"员工{i+1}",
                    emp_no=str(1000 + i),
                    team_desc="热线一组",
                    metrics={"通话次数": 10 + i},
                    import_batch=f"batch-{day}",
                )
                db.add(w)
            db.commit()
        finally:
            db.close()

    def test_delete_by_id(self):
        db = SessionLocal()
        try:
            w = db.query(Workload).first()
            wid = w.id
            resp = client.delete(f"/api/workloads/{wid}")
            assert resp.status_code == 200
            remaining = db.query(Workload).count()
            assert remaining == 2
        finally:
            db.close()

    def test_delete_by_date(self):
        resp = client.delete("/api/workloads/by-date", params={"date": "2026-06-28"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

        db = SessionLocal()
        try:
            remaining = db.query(Workload).count()
            assert remaining == 2
        finally:
            db.close()

    def test_delete_by_date_no_records(self):
        resp = client.delete("/api/workloads/by-date", params={"date": "2026-07-01"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_delete_by_date_invalid_format(self):
        resp = client.delete("/api/workloads/by-date", params={"date": "not-a-date"})
        assert resp.status_code == 400

    def test_delete_by_batch(self):
        resp = client.delete("/api/workloads/import/batch-28")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

        db = SessionLocal()
        try:
            remaining = db.query(Workload).count()
            assert remaining == 2
        finally:
            db.close()

    def test_delete_not_found(self):
        resp = client.delete("/api/workloads/99999")
        assert resp.status_code == 404


class TestWorkloadReport:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            _create_test_employees(db)
            ORG_PREFIX = "广西分公司>>省中心>>客户服务营销中心>>"
            records = [
                Workload(date=date(2026, 6, 28), province="广西", account="STTR00001", name="张三", emp_no="1001",
                         team_desc=f"{ORG_PREFIX}热线一组",
                         metrics={"总体-签入次数": 1, "总体-工作总时长(秒)": 28800, "呼入人工服务-人工服务-通话次数": 30,
                                  "呼入人工服务-工单-生成总量": 10, "人工服务-满意度-满意率": 98.5,
                                  "呼入人工服务-满意度-非常满意量": 10, "呼入人工服务-满意度-满意量": 15,
                                  "呼入人工服务-满意度-一般量": 2, "呼入人工服务-满意度-不满意量": 1,
                                  "呼入人工服务-满意度-非常不满意量": 0}, import_batch="batch001"),
                Workload(date=date(2026, 6, 28), province="广西", account="STTR00002", name="李四", emp_no="1002",
                         team_desc=f"{ORG_PREFIX}热线二组",
                         metrics={"总体-签入次数": 1, "总体-工作总时长(秒)": 25200, "呼入人工服务-人工服务-通话次数": 20,
                                  "呼入人工服务-工单-生成总量": 5, "人工服务-满意度-满意率": 95.0,
                                  "呼入人工服务-满意度-非常满意量": 8, "呼入人工服务-满意度-满意量": 8,
                                  "呼入人工服务-满意度-一般量": 2, "呼入人工服务-满意度-不满意量": 1,
                                  "呼入人工服务-满意度-非常不满意量": 1}, import_batch="batch001"),
                Workload(date=date(2026, 6, 28), province="广东", account="STTR00003", name="王五", emp_no="1003",
                         team_desc=f"{ORG_PREFIX}热线一组",
                         metrics={"总体-签入次数": 1, "总体-工作总时长(秒)": 27000, "呼入人工服务-人工服务-通话次数": 25,
                                  "呼入人工服务-工单-生成总量": 8, "人工服务-满意度-满意率": 96.0,
                                  "呼入人工服务-满意度-非常满意量": 12, "呼入人工服务-满意度-满意量": 10,
                                  "呼入人工服务-满意度-一般量": 2, "呼入人工服务-满意度-不满意量": 1,
                                  "呼入人工服务-满意度-非常不满意量": 0}, import_batch="batch001"),
            ]
            for r in records:
                db.add(r)
            db.commit()
        finally:
            db.close()

    def test_report_all(self):
        resp = client.get("/api/workloads/report", params={"start_date": "2026-06-28", "end_date": "2026-06-28"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 3
        assert data["stats"]["total_records"] == 3
        assert data["stats"]["total_call_count"] == 75
        assert data["stats"]["total_ticket_count"] == 23
        assert len(data["items"]) == 3

    def test_report_empty_range(self):
        resp = client.get("/api/workloads/report", params={"start_date": "2025-01-01", "end_date": "2025-01-31"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 0
        assert data["stats"]["total_records"] == 0
        assert len(data["items"]) == 0

    def test_report_metrics_fields(self):
        resp = client.get("/api/workloads/report", params={"start_date": "2026-06-28", "end_date": "2026-06-28"})
        assert resp.status_code == 200
        data = resp.json()
        assert "metrics_fields" in data
        assert len(data["metrics_fields"]) > 0

    def test_report_filter_by_name(self):
        resp = client.get("/api/workloads/report", params={"start_date": "2026-06-28", "end_date": "2026-06-28", "name": "张三"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 1

    def test_report_filter_by_name_masked_workload(self):
        """Name filter should match Employee.name even when Workload.name is masked"""
        db = SessionLocal()
        try:
            ORG_PREFIX = "广西分公司>>省中心>>客户服务营销中心>>"
            db.add(Workload(
                date=date(2026, 6, 28), province="广西", account="STTR00004",
                name="赵*", emp_no="1004",
                team_desc=f"{ORG_PREFIX}热线二组",
                metrics={"总体-签入次数": 1, "总体-工作总时长(秒)": 10000,
                         "呼入人工服务-人工服务-通话次数": 5},
                import_batch="batch001"
            ))
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/workloads/report", params={
            "start_date": "2026-06-28", "end_date": "2026-06-28", "name": "赵六"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 1
        assert data["items"][0]["account"] == "STTR00004"

    def test_report_filter_by_name_partial(self):
        """Name filter should support partial match against Employee.name"""
        resp = client.get("/api/workloads/report", params={
            "start_date": "2026-06-28", "end_date": "2026-06-28", "name": "张"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 1
        assert data["items"][0]["account"] == "STTR00001"

    def test_report_filter_by_name_ignore_workload_name(self):
        """Name filter should NOT match Workload.name when Employee.name differs"""
        db = SessionLocal()
        try:
            ORG_PREFIX = "广西分公司>>省中心>>客户服务营销中心>>"
            db.add(Workload(
                date=date(2026, 6, 28), province="广西", account="STTR00004",
                name="TEST_MASKED_NAME", emp_no="1004",
                team_desc=f"{ORG_PREFIX}热线二组",
                metrics={"总体-签入次数": 1, "总体-工作总时长(秒)": 10000,
                         "呼入人工服务-人工服务-通话次数": 5},
                import_batch="batch001"
            ))
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/workloads/report", params={
            "start_date": "2026-06-28", "end_date": "2026-06-28", "name": "TEST_MASKED_NAME"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 0

    def test_report_filter_by_name_no_match(self):
        """Name filter with non-existent name should return empty"""
        resp = client.get("/api/workloads/report", params={
            "start_date": "2026-06-28", "end_date": "2026-06-28", "name": "不存在"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 0

    def test_report_filter_by_account(self):
        resp = client.get("/api/workloads/report", params={"start_date": "2026-06-28", "end_date": "2026-06-28", "account": "STTR00001"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 1

    def test_report_filter_by_team(self):
        """Filter by Employee.team (not Workload.team_desc org path)"""
        resp = client.get("/api/workloads/report", params={
            "start_date": "2026-06-28", "end_date": "2026-06-28", "team_desc": "热线一组"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 2

    def test_report_teams_from_employee(self):
        """teams list should come from Employee.team, not Workload.team_desc"""
        resp = client.get("/api/workloads/report", params={"start_date": "2026-06-28", "end_date": "2026-06-28"})
        assert resp.status_code == 200
        data = resp.json()
        teams = data["stats"].get("teams", [])
        assert "热线一组" in teams
        assert "热线二组" in teams

    def test_report_satisfaction_rate_from_raw_counts(self):
        resp = client.get("/api/workloads/report", params={"start_date": "2026-06-28", "end_date": "2026-06-28"})
        assert resp.status_code == 200
        data = resp.json()
        items = {i["account"]: i["aggregated_metrics"] for i in data["items"]}

        zs = items["STTR00001"]
        assert zs["呼入人工服务-满意度-非常满意量"] == 10
        assert zs["呼入人工服务-满意度-满意量"] == 15
        assert zs["呼入人工服务-满意度-一般量"] == 2
        assert zs["呼入人工服务-满意度-不满意量"] == 1
        assert zs["呼入人工服务-满意度-非常不满意量"] == 0
        assert zs["人工服务-满意度-满意率"] == round((10 + 15) / (10 + 15 + 2 + 1 + 0), 4)

        ls = items["STTR00002"]
        assert ls["呼入人工服务-满意度-非常满意量"] == 8
        assert ls["呼入人工服务-满意度-满意量"] == 8
        assert ls["呼入人工服务-满意度-一般量"] == 2
        assert ls["呼入人工服务-满意度-不满意量"] == 1
        assert ls["呼入人工服务-满意度-非常不满意量"] == 1
        assert ls["人工服务-满意度-满意率"] == round((8 + 8) / (8 + 8 + 2 + 1 + 1), 4)

    def test_report_satisfaction_rate_aggregated_across_days(self):
        db = SessionLocal()
        try:
            db.add(Workload(
                date=date(2026, 6, 29), province="广西", account="STTR00001", name="张三", emp_no="1001",
                team_desc="广西分公司>>省中心>>客户服务营销中心>>热线一组",
                metrics={"总体-签入次数": 1, "总体-工作总时长(秒)": 30000, "呼入人工服务-人工服务-通话次数": 35,
                         "呼入人工服务-工单-生成总量": 12, "人工服务-满意度-满意率": 99.0,
                         "呼入人工服务-满意度-非常满意量": 20, "呼入人工服务-满意度-满意量": 10,
                         "呼入人工服务-满意度-一般量": 1, "呼入人工服务-满意度-不满意量": 0,
                         "呼入人工服务-满意度-非常不满意量": 0}, import_batch="batch002"),
            )
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/workloads/report", params={"start_date": "2026-06-28", "end_date": "2026-06-29"})
        assert resp.status_code == 200
        data = resp.json()
        zs = next(i for i in data["items"] if i["account"] == "STTR00001")

        total_very_sat = 10 + 20
        total_sat = 15 + 10
        total_general = 2 + 1
        total_dis = 1 + 0
        total_very_dis = 0 + 0
        expected_rate = round((total_very_sat + total_sat) / (total_very_sat + total_sat + total_general + total_dis + total_very_dis), 4)
        assert zs["aggregated_metrics"]["人工服务-满意度-满意率"] == expected_rate

    def test_report_satisfaction_rate_fallback_when_raw_counts_missing(self):
        db = SessionLocal()
        try:
            db.add(Workload(
                date=date(2026, 6, 28), province="广西", account="STTR00004", name="赵六", emp_no="1004",
                team_desc="广西分公司>>省中心>>客户服务营销中心>>热线二组",
                metrics={"总体-签入次数": 1, "人工服务-满意度-满意率": 92.0}, import_batch="batch003"),
            )
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/workloads/report", params={"start_date": "2026-06-28", "end_date": "2026-06-28"})
        assert resp.status_code == 200
        data = resp.json()
        zl = next(i for i in data["items"] if i["account"] == "STTR00004")
        assert zl["aggregated_metrics"]["人工服务-满意度-满意率"] == 92.0

    def test_report_satisfaction_rate_zero_denominator(self):
        db = SessionLocal()
        try:
            db.add(Workload(
                date=date(2026, 6, 28), province="广西", account="STTR00004", name="赵六", emp_no="1004",
                team_desc="广西分公司>>省中心>>客户服务营销中心>>热线二组",
                metrics={"总体-签入次数": 1, "人工服务-满意度-满意率": 0.0,
                         "呼入人工服务-满意度-非常满意量": 0, "呼入人工服务-满意度-满意量": 0,
                         "呼入人工服务-满意度-一般量": 0, "呼入人工服务-满意度-不满意量": 0,
                         "呼入人工服务-满意度-非常不满意量": 0}, import_batch="batch004"),
            )
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/workloads/report", params={"start_date": "2026-06-28", "end_date": "2026-06-28"})
        assert resp.status_code == 200
        data = resp.json()
        zl = next(i for i in data["items"] if i["account"] == "STTR00004")
        assert zl["aggregated_metrics"]["人工服务-满意度-满意率"] is None

    def test_report_excludes_resigned_employee(self):
        db = SessionLocal()
        try:
            from app.models.employee import Employee
            resigned = Employee(emp_no="STTR0099", name="离职员工", team="热线一组", status="离职")
            db.add(resigned)
            db.add(Workload(
                date=date(2026, 6, 28), province="广西", account="STTR0099",
                name="离职员工", emp_no="1099", team_desc="热线一组",
                metrics={"总体-签入次数": 1, "总体-工作总时长(秒)": 28800,
                         "呼入人工服务-人工服务-通话次数": 30}, import_batch="batch_resigned"
            ))
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/workloads/report", params={"start_date": "2026-06-28", "end_date": "2026-06-28"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 3
        assert data["stats"]["total_records"] == 3
        accounts = [item["account"] for item in data["items"]]
        assert "STTR0099" not in accounts

    def test_report_tenure_mode_le(self):
        from datetime import timedelta
        from app.models.employee import Employee

        today = date.today()
        db = SessionLocal()
        try:
            emp1 = db.query(Employee).filter(Employee.emp_no == "STTR00001").first()
            emp1.hire_date = today - timedelta(days=30)
            emp2 = db.query(Employee).filter(Employee.emp_no == "STTR00002").first()
            emp2.hire_date = today - timedelta(days=200)
            emp3 = db.query(Employee).filter(Employee.emp_no == "STTR00003").first()
            emp3.hire_date = None
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/workloads/report", params={
            "start_date": "2026-06-28", "end_date": "2026-06-28",
            "tenure_mode": "le", "tenure_months": 3
        })
        assert resp.status_code == 200
        data = resp.json()
        accounts = [item["account"] for item in data["items"]]
        assert "STTR00001" in accounts
        assert "STTR00002" not in accounts
        assert "STTR00003" not in accounts
        assert data["stats"]["total_people"] == 1

    def test_report_tenure_mode_gt(self):
        from datetime import timedelta
        from app.models.employee import Employee

        today = date.today()
        db = SessionLocal()
        try:
            emp1 = db.query(Employee).filter(Employee.emp_no == "STTR00001").first()
            emp1.hire_date = today - timedelta(days=30)
            emp2 = db.query(Employee).filter(Employee.emp_no == "STTR00002").first()
            emp2.hire_date = today - timedelta(days=200)
            emp3 = db.query(Employee).filter(Employee.emp_no == "STTR00003").first()
            emp3.hire_date = None
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/workloads/report", params={
            "start_date": "2026-06-28", "end_date": "2026-06-28",
            "tenure_mode": "gt", "tenure_months": 3
        })
        assert resp.status_code == 200
        data = resp.json()
        accounts = [item["account"] for item in data["items"]]
        assert "STTR00001" not in accounts
        assert "STTR00002" in accounts
        assert "STTR00003" in accounts
        assert data["stats"]["total_people"] == 2

    def test_report_tenure_mode_all(self):
        from datetime import timedelta
        from app.models.employee import Employee

        today = date.today()
        db = SessionLocal()
        try:
            emp1 = db.query(Employee).filter(Employee.emp_no == "STTR00001").first()
            emp1.hire_date = today - timedelta(days=30)
            emp2 = db.query(Employee).filter(Employee.emp_no == "STTR00002").first()
            emp2.hire_date = today - timedelta(days=200)
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/workloads/report", params={
            "start_date": "2026-06-28", "end_date": "2026-06-28"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 3

    def test_report_tenure_mode_custom_months(self):
        from datetime import timedelta
        from app.models.employee import Employee

        today = date.today()
        db = SessionLocal()
        try:
            emp1 = db.query(Employee).filter(Employee.emp_no == "STTR00001").first()
            emp1.hire_date = today - timedelta(days=60)
            emp2 = db.query(Employee).filter(Employee.emp_no == "STTR00002").first()
            emp2.hire_date = today - timedelta(days=150)
            db.commit()
        finally:
            db.close()

        # 1 month cutoff: only STTR00001 (60 days < 30*1=30? No, 60 > 30, so not le)
        resp = client.get("/api/workloads/report", params={
            "start_date": "2026-06-28", "end_date": "2026-06-28",
            "tenure_mode": "le", "tenure_months": 1
        })
        assert resp.status_code == 200
        data = resp.json()
        accounts = [item["account"] for item in data["items"]]
        assert "STTR00001" not in accounts
        assert "STTR00002" not in accounts

        # 3 month cutoff: both are within 120 days? No, 60 < 90, 150 > 90. le=3 months => days <= 90
        # STTR00001: 60 days -> hire_date > cutoff (today-90): 60 < 90 so True -> is new
        # STTR00002: 150 days -> hire_date > cutoff: 150 > 90 so False -> not new
        resp = client.get("/api/workloads/report", params={
            "start_date": "2026-06-28", "end_date": "2026-06-28",
            "tenure_mode": "le", "tenure_months": 3
        })
        assert resp.status_code == 200
        data = resp.json()
        accounts = [item["account"] for item in data["items"]]
        assert "STTR00001" in accounts
        assert "STTR00002" not in accounts

        # 6 month cutoff: both are within 180 days, so both are "le"
        resp = client.get("/api/workloads/report", params={
            "start_date": "2026-06-28", "end_date": "2026-06-28",
            "tenure_mode": "le", "tenure_months": 6
        })
        assert resp.status_code == 200
        data = resp.json()
        accounts = [item["account"] for item in data["items"]]
        assert "STTR00001" in accounts
        assert "STTR00002" in accounts


class TestWorkloadMetricsFields:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
        finally:
            db.close()

    def test_metrics_fields_returns_defaults_when_no_data(self):
        resp = client.get("/api/workloads/metrics-fields")
        assert resp.status_code == 200
        fields = resp.json()
        assert len(fields) > 0


class TestWorkloadDailyProduction:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            _create_test_employees(db)
            ORG_PREFIX = "广西分公司>>省中心>>客户服务营销中心>>"
            records = [
                Workload(date=date(2026, 6, 28), province="广西", account="STTR00001", name="张三", emp_no="1001",
                         team_desc=f"{ORG_PREFIX}热线一组",
                         metrics={"呼入人工服务-人工服务-通话次数": 30, "呼入人工服务-工单-生成总量": 10,
                                  "呼出服务-人工呼出呼叫量": 8}, import_batch="batch001"),
                Workload(date=date(2026, 6, 28), province="广西", account="STTR00002", name="李四", emp_no="1002",
                         team_desc=f"{ORG_PREFIX}热线二组",
                         metrics={"呼入人工服务-人工服务-通话次数": 20, "呼入人工服务-工单-生成总量": 5,
                                  "呼出服务-人工呼出呼叫量": 3}, import_batch="batch001"),
                Workload(date=date(2026, 6, 29), province="广西", account="STTR00001", name="张三", emp_no="1001",
                         team_desc=f"{ORG_PREFIX}热线一组",
                         metrics={"呼入人工服务-人工服务-通话次数": 35, "呼入人工服务-工单-生成总量": 12,
                                  "呼出服务-人工呼出呼叫量": 10}, import_batch="batch002"),
            ]
            for r in records:
                db.add(r)
            db.commit()
        finally:
            db.close()

    def test_daily_production_returns_all_dates_in_month(self):
        resp = client.get("/api/workloads/daily-production", params={"year_month": "2026-06"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 30

    def test_daily_production_aggregates_correctly(self):
        resp = client.get("/api/workloads/daily-production", params={"year_month": "2026-06"})
        assert resp.status_code == 200
        data = resp.json()
        day28 = next(d for d in data if d["date"] == "2026-06-28")
        assert day28["call_count"] == 50
        assert day28["ticket_count"] == 15
        assert day28["outbound_count"] == 11
        assert day28["people_count"] == 2
        day29 = next(d for d in data if d["date"] == "2026-06-29")
        assert day29["call_count"] == 35
        assert day29["ticket_count"] == 12
        assert day29["outbound_count"] == 10
        assert day29["people_count"] == 1
        day01 = next(d for d in data if d["date"] == "2026-06-01")
        assert day01["call_count"] == 0

    def test_daily_production_no_data(self):
        resp = client.get("/api/workloads/daily-production", params={"year_month": "2025-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 31
        assert all(d["call_count"] == 0 for d in data)

    def test_daily_production_no_year_month_defaults_to_current(self):
        resp = client.get("/api/workloads/daily-production")
        assert resp.status_code == 200


class TestWorkloadTeamProduction:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            _create_test_employees(db)
            ORG_PREFIX = "广西分公司>>省中心>>客户服务营销中心>>"
            records = [
                Workload(date=date(2026, 6, 28), province="广西", account="STTR00001", name="张三", emp_no="1001",
                         team_desc=f"{ORG_PREFIX}热线一组",
                         metrics={"呼入人工服务-人工服务-通话次数": 30, "呼入人工服务-工单-生成总量": 10,
                                  "呼出服务-人工呼出呼叫量": 8}, import_batch="batch001"),
                Workload(date=date(2026, 6, 28), province="广西", account="STTR00002", name="李四", emp_no="1002",
                         team_desc=f"{ORG_PREFIX}热线二组",
                         metrics={"呼入人工服务-人工服务-通话次数": 20, "呼入人工服务-工单-生成总量": 5,
                                  "呼出服务-人工呼出呼叫量": 3}, import_batch="batch001"),
                Workload(date=date(2026, 6, 28), province="广西", account="STTR00003", name="王五", emp_no="1003",
                         team_desc=f"{ORG_PREFIX}热线一组",
                         metrics={"呼入人工服务-人工服务-通话次数": 25, "呼入人工服务-工单-生成总量": 8,
                                  "呼出服务-人工呼出呼叫量": 5}, import_batch="batch001"),
            ]
            for r in records:
                db.add(r)
            db.commit()
        finally:
            db.close()

    def test_team_production_returns_teams(self):
        resp = client.get("/api/workloads/team-production", params={"year_month": "2026-06"})
        assert resp.status_code == 200
        data = resp.json()
        teams = [d["team"] for d in data]
        assert "热线一组" in teams
        assert "热线二组" in teams

    def test_team_production_aggregates_correctly(self):
        resp = client.get("/api/workloads/team-production", params={"year_month": "2026-06"})
        assert resp.status_code == 200
        data = resp.json()
        team1 = next(d for d in data if d["team"] == "热线一组")
        assert team1["call_count"] == 55
        assert team1["ticket_count"] == 18
        assert team1["outbound_count"] == 13
        assert team1["emp_count"] == 2
        team2 = next(d for d in data if d["team"] == "热线二组")
        assert team2["call_count"] == 20
        assert team2["emp_count"] == 1

    def test_team_production_excludes_resigned_employee(self):
        db = SessionLocal()
        try:
            from app.models.employee import Employee
            resigned = Employee(emp_no="STTR0099", name="离职员工", team="热线三组", status="离职")
            db.add(resigned)
            db.add(Workload(
                date=date(2026, 6, 28), province="广西", account="STTR0099",
                name="离职员工", emp_no="1099", team_desc="热线三组",
                metrics={"呼入人工服务-人工服务-通话次数": 50}, import_batch="batch_resigned"
            ))
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/workloads/team-production", params={"year_month": "2026-06"})
        assert resp.status_code == 200
        data = resp.json()
        teams = [d["team"] for d in data]
        assert "热线三组" not in teams

    def test_team_production_no_data(self):
        resp = client.get("/api/workloads/team-production", params={"year_month": "2025-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert data == []

    def test_team_production_no_year_month_defaults_to_current(self):
        resp = client.get("/api/workloads/team-production")
        assert resp.status_code == 200


class TestWorkloadExport:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            _create_test_employees(db)
            records = [
                Workload(
                    date=date(2026, 6, 28), province="广西", account="STTR00001",
                    name="张三", emp_no="1001", team_desc="热线一组",
                    metrics={
                        "呼入人工服务-人工服务-通话次数": 30,
                        "呼入人工服务-人工服务-通话总时长(秒)": 5400,
                        "呼入人工服务-工单-生成总量": 10,
                    },
                    import_batch="batch001"
                ),
                Workload(
                    date=date(2026, 6, 28), province="广东", account="STTR00002",
                    name="李四", emp_no="1002", team_desc="热线二组",
                    metrics={
                        "呼入人工服务-人工服务-通话次数": 20,
                        "呼入人工服务-人工服务-通话总时长(秒)": 3600,
                        "呼入人工服务-工单-生成总量": 5,
                    },
                    import_batch="batch001"
                ),
            ]
            for r in records:
                db.add(r)
            db.commit()
        finally:
            db.close()

    def test_export_csv_headers(self):
        resp = client.get("/api/workloads/report/export", params={"start_date": "2026-06-28", "end_date": "2026-06-28"})
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "Content-Disposition" in resp.headers
        assert "filename=workload_report_" in resp.headers["Content-Disposition"]
        lines = content.strip().split("\n")
        assert len(lines) > 1
        headers = lines[0].split(",")
        assert "账号" in headers
        assert "姓名" in headers
        assert "工号" in headers
        assert "班组" in headers
        assert "日期" in headers

    def test_export_csv_data(self):
        resp = client.get("/api/workloads/report/export", params={"start_date": "2026-06-28", "end_date": "2026-06-28"})
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        lines = content.strip().split("\n")
        assert len(lines) == 3  # header + 2 records
        assert "STTR00001" in lines[1]
        assert "STTR00002" in lines[2]
        assert "张三" in lines[1]
        assert "李四" in lines[2]

    def test_export_csv_no_data(self):
        resp = client.get("/api/workloads/report/export", params={"start_date": "2025-01-01", "end_date": "2025-01-31"})
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        lines = content.strip().split("\n")
        assert len(lines) == 1  # header only

    def test_export_csv_tenure_mode_le(self):
        from datetime import timedelta
        from app.models.employee import Employee

        today = date.today()
        db = SessionLocal()
        try:
            emp1 = db.query(Employee).filter(Employee.emp_no == "STTR00001").first()
            emp1.hire_date = today - timedelta(days=30)
            emp2 = db.query(Employee).filter(Employee.emp_no == "STTR00002").first()
            emp2.hire_date = today - timedelta(days=200)
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/workloads/report/export", params={
            "start_date": "2026-06-28", "end_date": "2026-06-28",
            "tenure_mode": "le", "tenure_months": 3
        })
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        lines = content.strip().split("\n")
        assert len(lines) == 2  # header + 1 new employee
        assert "STTR00001" in lines[1]
        assert "STTR00002" not in lines[1]

    def test_export_csv_tenure_mode_gt(self):
        from datetime import timedelta
        from app.models.employee import Employee

        today = date.today()
        db = SessionLocal()
        try:
            emp1 = db.query(Employee).filter(Employee.emp_no == "STTR00001").first()
            emp1.hire_date = today - timedelta(days=30)
            emp2 = db.query(Employee).filter(Employee.emp_no == "STTR00002").first()
            emp2.hire_date = today - timedelta(days=200)
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/workloads/report/export", params={
            "start_date": "2026-06-28", "end_date": "2026-06-28",
            "tenure_mode": "gt", "tenure_months": 3
        })
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        lines = content.strip().split("\n")
        assert len(lines) == 2  # header + 1 experienced employee
        assert "STTR00002" in lines[1]
        assert "STTR00001" not in lines[1]

    def test_export_csv_tenure_mode_custom_months(self):
        from datetime import timedelta
        from app.models.employee import Employee

        today = date.today()
        db = SessionLocal()
        try:
            emp1 = db.query(Employee).filter(Employee.emp_no == "STTR00001").first()
            emp1.hire_date = today - timedelta(days=60)
            emp2 = db.query(Employee).filter(Employee.emp_no == "STTR00002").first()
            emp2.hire_date = today - timedelta(days=150)
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/workloads/report/export", params={
            "start_date": "2026-06-28", "end_date": "2026-06-28",
            "tenure_mode": "le", "tenure_months": 1
        })
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        lines = content.strip().split("\n")
        assert len(lines) == 1  # header only, no records match 1 month

        resp = client.get("/api/workloads/report/export", params={
            "start_date": "2026-06-28", "end_date": "2026-06-28",
            "tenure_mode": "le", "tenure_months": 6
        })
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        lines = content.strip().split("\n")
        assert len(lines) == 3  # header + both records
