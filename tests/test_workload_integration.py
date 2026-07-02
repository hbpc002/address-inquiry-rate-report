"""Integration tests for workload import via API"""
import sys
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'backend'
sys.path.insert(0, str(BASE))

import pytest
from app.models.database import SessionLocal, engine, Base
from app.models.workload import Workload
from app.models.employee import Employee
from app.models.employee import Employee
from datetime import date
import openpyxl


def _build_xlsx(rows: list[list]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet_0"

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
    return buf.getvalue()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(Workload).delete()
        db.query(Employee).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(Workload).delete()
        db.query(Employee).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def patch_permissions(monkeypatch):
    monkeypatch.setattr('app.api.workloads.require_permission', lambda user, perm: None)


def test_import_single_employee(db):
    from app.api.workloads import import_workloads
    from fastapi import UploadFile

    rows = [
        ["20260628", "广西", "STTR00001", "张三", "1001", "热线一组",
         5, 5, 28800, 0.85, 30, 5400, 180, 600, 25, 98.5, 10, 8, 35, 3],
    ]
    xlsx = _build_xlsx(rows)
    file = UploadFile(filename="test.xlsx", file=io.BytesIO(xlsx))
    result = import_workloads(file=file, db=db, current_user={"id": 1})

    assert result.count == 1
    assert len(result.batch) == 8

    record = db.query(Workload).first()
    assert record is not None
    assert record.account == "STTR00001"
    assert record.name == "张三"
    assert record.province == "广西"
    assert record.date == date(2026, 6, 28)
    assert record.metrics["总体-签入次数"] == 5
    assert record.metrics["呼入人工服务-人工服务-通话次数"] == 30


def test_import_multiple_employees(db):
    from app.api.workloads import import_workloads
    from fastapi import UploadFile

    rows = [
        ["20260628", "广西", "STTR00001", "张三", "1001", "热线一组",
         5, 5, 28800, 0.85, 30, 5400, 180, 600, 25, 98.5, 10, 8, 35, 3],
        ["20260628", "广西", "STTR00002", "李四", "1002", "热线二组",
         3, 3, 25200, 0.75, 20, 3600, 180, 400, 18, 95.0, 5, 3, 23, 2],
        ["20260628", "广东", "STTR00003", "王五", "1003", "热线一组",
         4, 4, 27000, 0.80, 25, 4500, 180, 500, 20, 96.0, 8, 5, 29, 4],
    ]
    xlsx = _build_xlsx(rows)
    file = UploadFile(filename="test.xlsx", file=io.BytesIO(xlsx))
    result = import_workloads(file=file, db=db, current_user={"id": 1})

    assert result.count == 3
    assert db.query(Workload).count() == 3


def test_import_replaces_old_records(db):
    from app.api.workloads import import_workloads
    from fastapi import UploadFile

    old = Workload(date=date(2026, 6, 28), province="广西", account="STTR00001",
                   name="张三", emp_no="1001", team_desc="热线一组",
                   metrics={"签入次数": 3}, import_batch="old_batch")
    db.add(old)
    db.commit()

    rows = [
        ["20260628", "广西", "STTR00001", "张三", "1001", "热线一组",
         5, 5, 28800, 0.85, 30, 5400, 180, 600, 25, 98.5, 10, 8, 35, 3],
    ]
    xlsx = _build_xlsx(rows)
    file = UploadFile(filename="test.xlsx", file=io.BytesIO(xlsx))
    result = import_workloads(file=file, db=db, current_user={"id": 1})

    assert result.count == 1
    records = db.query(Workload).all()
    assert len(records) == 1
    assert records[0].import_batch != "old_batch"
    assert records[0].metrics["总体-签入次数"] == 5


def test_import_skips_heji_row(db):
    from app.api.workloads import import_workloads
    from fastapi import UploadFile

    rows = [
        ["20260628", "广西", "STTR00001", "张三", "1001", "热线一组",
         5, 5, 28800, 0.85, 30, 5400, 180, 600, 25, 98.5, 10, 8, 35, 3],
        ["合计", "", "", "", "", "", 8, 8, 54000, 0, 50, 9000, 0, 0, 0, 0, 0, 0, 0, 0],
    ]
    xlsx = _build_xlsx(rows)
    file = UploadFile(filename="test.xlsx", file=io.BytesIO(xlsx))
    result = import_workloads(file=file, db=db, current_user={"id": 1})
    assert result.count == 1


def test_import_multiple_dates_preserves_other_dates(db):
    from app.api.workloads import import_workloads
    from fastapi import UploadFile

    existing = Workload(date=date(2026, 6, 27), province="广西", account="STTR00099",
                        name="旧员工", emp_no="1999", team_desc="热线一组",
                        metrics={"通话次数": 10}, import_batch="preserve_me")
    db.add(existing)
    db.commit()

    rows = [
        ["20260628", "广西", "STTR00001", "张三", "1001", "热线一组",
         5, 5, 28800, 0.85, 30, 5400, 180, 600, 25, 98.5, 10, 8, 35, 3],
    ]
    xlsx = _build_xlsx(rows)
    file = UploadFile(filename="test.xlsx", file=io.BytesIO(xlsx))
    result = import_workloads(file=file, db=db, current_user={"id": 1})

    assert result.count == 1
    assert db.query(Workload).count() == 2
    assert db.query(Workload).filter(Workload.account == "STTR00099").count() == 1


def test_import_overrides_name_from_employee(db):
    from app.api.workloads import import_workloads
    from app.models.employee import Employee
    from fastapi import UploadFile

    emp = Employee(emp_no="STTR00001", name="张真实姓名", team="热线一组", dept="客服中心")
    db.add(emp)
    db.commit()

    rows = [
        ["20260628", "广西", "STTR00001", "张***", "1001", "热线一组",
         5, 5, 28800, 0.85, 30, 5400, 180, 600, 25, 98.5, 10, 8, 35, 3],
    ]
    xlsx = _build_xlsx(rows)
    file = UploadFile(filename="test.xlsx", file=io.BytesIO(xlsx))
    result = import_workloads(file=file, db=db, current_user={"id": 1})

    assert result.count == 1
    record = db.query(Workload).first()
    assert record.name == "张真实姓名"


@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])