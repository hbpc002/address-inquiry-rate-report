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
    db.execute(text("DELETE FROM workloads"))
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
            ["20260628", "广西", "STTR00001", "张三", "1001", "热线一组", 5, 5, 28800, 0.85, 30, 5400, 180, 600, 25, 98.5, 10, 8, 35, 3],
        ]
        resp = self._upload_xlsx(_make_xlsx(rows))
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert len(data["batch"]) == 8

    def test_import_multiple_rows(self):
        rows = [
            ["20260628", "广西", "STTR00001", "张三", "1001", "热线一组", 5, 5, 28800, 0.85, 30, 5400, 180, 600, 25, 98.5, 10, 8, 35, 3],
            ["20260628", "广西", "STTR00002", "李四", "1002", "热线二组", 3, 3, 25200, 0.75, 20, 3600, 180, 400, 18, 95.0, 5, 3, 23, 2],
            ["20260628", "广东", "STTR00003", "王五", "1003", "热线一组", 4, 4, 27000, 0.80, 25, 4500, 180, 500, 20, 96.0, 8, 5, 29, 4],
        ]
        resp = self._upload_xlsx(_make_xlsx(rows))
        assert resp.status_code == 200
        assert resp.json()["count"] == 3

    def test_import_skips_heji_row(self):
        rows = [
            ["20260628", "广西", "STTR00001", "张三", "1001", "热线一组", 5, 5, 28800, 0.85, 30, 5400, 180, 600, 25, 98.5, 10, 8, 35, 3],
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

    def test_import_replaces_old_records_on_same_date(self):
        rows1 = [
            ["20260628", "广西", "STTR00001", "张三", "1001", "热线一组", 5, 5, 28800, 0.85, 30, 5400, 180, 600, 25, 98.5, 10, 8, 35, 3],
        ]
        resp1 = self._upload_xlsx(_make_xlsx(rows1))
        assert resp1.status_code == 200
        assert resp1.json()["count"] == 1

        rows2 = [
            ["20260628", "广西", "STTR00001", "张三", "1001", "热线一组", 6, 6, 30000, 0.90, 35, 6000, 180, 700, 28, 99.0, 12, 10, 40, 5],
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


class TestWorkloadList:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
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

    def test_list_pagination(self):
        resp = client.get("/api/workloads", params={"page": 1, "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3


class TestWorkloadDelete:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
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
            records = [
                Workload(date=date(2026, 6, 28), province="广西", account="STTR00001", name="张三", emp_no="1001", team_desc="热线一组",
                         metrics={"总体-签入次数": 1, "总体-工作总时长(秒)": 28800, "呼入人工服务-人工服务-通话次数": 30,
                                  "呼入人工服务-工单-生成总量": 10, "人工服务-满意度-满意率": 98.5}, import_batch="batch001"),
                Workload(date=date(2026, 6, 28), province="广西", account="STTR00002", name="李四", emp_no="1002", team_desc="热线二组",
                         metrics={"总体-签入次数": 1, "总体-工作总时长(秒)": 25200, "呼入人工服务-人工服务-通话次数": 20,
                                  "呼入人工服务-工单-生成总量": 5, "人工服务-满意度-满意率": 95.0}, import_batch="batch001"),
                Workload(date=date(2026, 6, 28), province="广东", account="STTR00003", name="王五", emp_no="1003", team_desc="热线一组",
                         metrics={"总体-签入次数": 1, "总体-工作总时长(秒)": 27000, "呼入人工服务-人工服务-通话次数": 25,
                                  "呼入人工服务-工单-生成总量": 8, "人工服务-满意度-满意率": 96.0}, import_batch="batch001"),
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

    def test_report_filter_by_account(self):
        resp = client.get("/api/workloads/report", params={"start_date": "2026-06-28", "end_date": "2026-06-28", "account": "STTR00001"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 1


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
