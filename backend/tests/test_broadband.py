import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@localhost:5432/schedule_test')

from fastapi.testclient import TestClient
from app.models.database import Base, engine, SessionLocal, init_db
from app.models.seamless_order import SeamlessOrder
from app.models.employee import Employee
from app.main import app
from app.core.security import get_current_user
from sqlalchemy import text
from datetime import date
import io


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
    app.dependency_overrides[get_current_user] = override_get_current_user
    Base.metadata.drop_all(bind=engine)
    init_db()
    db = SessionLocal()
    try:
        db.execute(text("INSERT INTO users (id, username, password_hash, role, is_active) VALUES (1, 'test_admin', 'x', 'admin', true)"))
        db.commit()
    finally:
        db.close()


def teardown_module():
    app.dependency_overrides.clear()


def _clean_tables(db):
    for table in ["seamless_orders", "employees"]:
        db.execute(text(f"DELETE FROM {table}"))
    db.commit()


def _create_test_employees(db):
    employees_data = [
        ("KF770001", "张三", "云网一组"),
        ("KF770002", "李四", "云网二组"),
        ("KF770003", "王五", "云网一组"),
        ("KF770004", "赵六", "宽带一组"),
        ("KF770005", "离职员工", "宽带一组"),
    ]
    for emp_no, name, team in employees_data:
        existing = db.query(Employee).filter(Employee.emp_no == emp_no).first()
        if not existing:
            status = "离职" if emp_no == "KF770005" else "在职"
            db.add(Employee(emp_no=emp_no, name=name, team=team, dept="宽带营销中心", status=status))
    db.commit()


def _make_xlsx(rows: list[list]) -> io.BytesIO:
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet_0"

    ws.append(["新客服无缝订单统计表"])
    ws.append(["导出日期", "2026-06-30"])

    header = [
        "新客服无缝订单号", "下单新客服工号", "下单日期", "是否竣工", "地市名称",
        "是否1小时短单", "是否剔除", "是否重复单", "线下办理CB订单号",
        "线下办理CB业务号码", "线下办理CB订单状态", "最终办理产品名称",
        "最终办理宽带速率", "订单状态", "月份", "中台意向单受理人工号",
    ]
    # 第3行(索引2)为表头
    ws.append(header)

    for row in rows:
        padded = list(row) + [""] * (len(header) - len(row))
        ws.append(padded)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _upload_xlsx(xlsx_bytes: io.BytesIO, filename="broadband.xlsx"):
    data = {"file": (filename, xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    return client.post("/api/broadband/orders/import", files=data)


def _base_row(order_no="OD0001", emp_no="KF770001", order_date="2026-06-28",
              completed="是", city="南宁", hour_short="否", excluded="否",
              duplicate="否", product="300M", intention="KF880001", extra=""):
    row = [order_no, emp_no, order_date, completed, city, hour_short, excluded,
           duplicate, "CB001", "18800000000", "已竣工", product, "300M",
           "竣工", "2026-06", intention]
    if extra:
        row.append(extra)
    return row


class TestBroadbandImport:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
        finally:
            db.close()

    def test_import_normal(self):
        rows = [_base_row(), _base_row("OD0002", "KF770002")]
        resp = _upload_xlsx(_make_xlsx(rows))
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert len(data["batch"]) == 8

    def test_import_dedupes_by_order_no(self):
        rows = [_base_row("OD0001"), _base_row("OD0001")]
        resp = _upload_xlsx(_make_xlsx(rows))
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_import_replaces_old_records_on_same_date(self):
        rows1 = [_base_row("OD0001")]
        resp1 = _upload_xlsx(_make_xlsx(rows1))
        assert resp1.status_code == 200
        assert resp1.json()["count"] == 1

        rows2 = [_base_row("OD0002", product="1000M")]
        resp2 = _upload_xlsx(_make_xlsx(rows2))
        assert resp2.status_code == 200
        assert resp2.json()["count"] == 1

        db = SessionLocal()
        try:
            records = db.query(SeamlessOrder).all()
            assert len(records) == 1
            assert records[0].order_no == "OD0002"
        finally:
            db.close()

    def test_import_skips_bad_date(self):
        rows = [_base_row(order_date="not-a-date")]
        resp = _upload_xlsx(_make_xlsx(rows))
        assert resp.status_code == 400

    def test_import_skips_missing_order_no(self):
        rows = [["", "KF770001", "2026-06-28", "是", "南宁", "否", "否", "否", "", "", "", "", "", "", "2026-06", ""]]
        resp = _upload_xlsx(_make_xlsx(rows))
        assert resp.status_code == 400

    def test_import_invalid_file(self):
        data = {"file": ("empty.xlsx", io.BytesIO(b"not an excel"),
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = client.post("/api/broadband/orders/import", files=data)
        assert resp.status_code == 400


class TestBroadbandList:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            _create_test_employees(db)
            records = [
                SeamlessOrder(order_no="OD0001", emp_no="KF770001", order_date=date(2026, 6, 28),
                              is_completed="是", is_excluded="否", is_duplicate="否",
                              city="南宁", import_batch="b1"),
                SeamlessOrder(order_no="OD0002", emp_no="KF770002", order_date=date(2026, 6, 28),
                              is_completed="否", is_excluded="否", is_duplicate="否",
                              city="柳州", import_batch="b1"),
                SeamlessOrder(order_no="OD0003", emp_no="KF770001", order_date=date(2026, 6, 29),
                              is_completed="是", is_excluded="否", is_duplicate="否",
                              city="南宁", import_batch="b2"),
            ]
            for r in records:
                db.add(r)
            db.commit()
        finally:
            db.close()

    def test_list_all(self):
        resp = client.get("/api/broadband/orders")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_list_filter_by_date_range(self):
        resp = client.get("/api/broadband/orders", params={"start_date": "2026-06-29", "end_date": "2026-06-29"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_filter_by_emp_no(self):
        resp = client.get("/api/broadband/orders", params={"emp_no": "KF770001"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_list_filter_by_batch(self):
        resp = client.get("/api/broadband/orders", params={"import_batch": "b2"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_filter_by_name(self):
        resp = client.get("/api/broadband/orders", params={"name": "张三"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert all(i["name"] == "张三" for i in data["items"])

    def test_list_pagination(self):
        resp = client.get("/api/broadband/orders", params={"page": 1, "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3

    def test_delete_by_id(self):
        db = SessionLocal()
        try:
            o = db.query(SeamlessOrder).first()
            oid = o.id
        finally:
            db.close()
        resp = client.delete(f"/api/broadband/orders/{oid}")
        assert resp.status_code == 200
        db = SessionLocal()
        try:
            assert db.query(SeamlessOrder).count() == 2
        finally:
            db.close()

    def test_delete_not_found(self):
        resp = client.delete("/api/broadband/orders/99999")
        assert resp.status_code == 404

    def test_delete_by_date(self):
        resp = client.delete("/api/broadband/orders/by-date", params={"date": "2026-06-28"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 2
        db = SessionLocal()
        try:
            assert db.query(SeamlessOrder).count() == 1
        finally:
            db.close()

    def test_delete_by_date_invalid_format(self):
        resp = client.delete("/api/broadband/orders/by-date", params={"date": "not-a-date"})
        assert resp.status_code == 400

    def test_delete_by_batch(self):
        resp = client.delete("/api/broadband/orders/import/b1")
        assert resp.status_code == 200
        assert resp.json()["count"] == 2
        db = SessionLocal()
        try:
            assert db.query(SeamlessOrder).count() == 1
        finally:
            db.close()


class TestBroadbandReport:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            _create_test_employees(db)
            records = [
                # 张三(KF770001): 4单 3竣工
                SeamlessOrder(order_no="OD0001", emp_no="KF770001", order_date=date(2026, 6, 28),
                              is_completed="是", is_excluded="否", is_duplicate="否", city="南宁"),
                SeamlessOrder(order_no="OD0002", emp_no="KF770001", order_date=date(2026, 6, 28),
                              is_completed="是", is_excluded="否", is_duplicate="否", city="南宁"),
                SeamlessOrder(order_no="OD0003", emp_no="KF770001", order_date=date(2026, 6, 28),
                              is_completed="否", is_excluded="否", is_duplicate="否", city="南宁"),
                SeamlessOrder(order_no="OD0004", emp_no="KF770001", order_date=date(2026, 6, 29),
                              is_completed="是", is_excluded="否", is_duplicate="否", city="南宁"),
                # 李四(KF770002): 1单 0竣工
                SeamlessOrder(order_no="OD0005", emp_no="KF770002", order_date=date(2026, 6, 28),
                              is_completed="否", is_excluded="否", is_duplicate="否", city="柳州"),
                # 被剔除/重复单不计入
                SeamlessOrder(order_no="OD0006", emp_no="KF770001", order_date=date(2026, 6, 28),
                              is_completed="是", is_excluded="是", is_duplicate="否", city="南宁"),
                SeamlessOrder(order_no="OD0007", emp_no="KF770002", order_date=date(2026, 6, 28),
                              is_completed="是", is_excluded="否", is_duplicate="是", city="柳州"),
                # 离职员工不计入
                SeamlessOrder(order_no="OD0008", emp_no="KF770005", order_date=date(2026, 6, 28),
                              is_completed="是", is_excluded="否", is_duplicate="否", city="南宁"),
            ]
            for r in records:
                db.add(r)
            db.commit()
        finally:
            db.close()

    def test_report_aggregates_and_rate(self):
        resp = client.get("/api/broadband/report", params={"start_date": "2026-06-28", "end_date": "2026-06-29"})
        assert resp.status_code == 200
        data = resp.json()
        stats = data["stats"]
        assert stats["total_people"] == 2
        assert stats["total_recommend"] == 5
        assert stats["total_completed"] == 3
        assert stats["avg_success_rate"] == round(3 / 5, 4)

        items = {i["emp_no"]: i for i in data["items"]}
        zs = items["KF770001"]
        assert zs["name"] == "张三"
        assert zs["recommend"] == 4
        assert zs["intention_count"] == 4
        assert zs["completed"] == 3
        assert zs["success_rate"] == round(3 / 4, 4)
        assert zs["team"] == "云网一组"

        ls = items["KF770002"]
        assert ls["recommend"] == 1
        assert ls["completed"] == 0
        assert ls["success_rate"] == 0

    def test_report_dedupes_by_order_no(self):
        db = SessionLocal()
        try:
            db.add(SeamlessOrder(order_no="OD0001", emp_no="KF770001", order_date=date(2026, 6, 28),
                                 is_completed="是", is_excluded="否", is_duplicate="否", city="南宁"))
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/broadband/report", params={"start_date": "2026-06-28", "end_date": "2026-06-29"})
        data = resp.json()
        assert data["stats"]["total_recommend"] == 5

    def test_report_empty_range(self):
        resp = client.get("/api/broadband/report", params={"start_date": "2025-01-01", "end_date": "2025-01-31"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 0
        assert len(data["items"]) == 0

    def test_report_filter_by_name(self):
        resp = client.get("/api/broadband/report", params={
            "start_date": "2026-06-28", "end_date": "2026-06-29", "name": "张三"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 1
        assert data["items"][0]["emp_no"] == "KF770001"

    def test_report_filter_by_emp_no(self):
        resp = client.get("/api/broadband/report", params={
            "start_date": "2026-06-28", "end_date": "2026-06-29", "emp_no": "KF770002"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 1
        assert data["items"][0]["emp_no"] == "KF770002"

    def test_report_filter_by_team(self):
        resp = client.get("/api/broadband/report", params={
            "start_date": "2026-06-28", "end_date": "2026-06-29", "team": "云网一组"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 1
        assert data["items"][0]["emp_no"] == "KF770001"

    def test_report_filter_by_team_prefix(self):
        """班级前缀(云网)应同时匹配 云网一组/云网二组"""
        resp = client.get("/api/broadband/report", params={
            "start_date": "2026-06-28", "end_date": "2026-06-29", "team_prefix": "云网"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 2
        assert {i["emp_no"] for i in data["items"]} == {"KF770001", "KF770002"}

    def test_report_filter_by_city(self):
        resp = client.get("/api/broadband/report", params={
            "start_date": "2026-06-28", "end_date": "2026-06-29", "city": "柳州"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_people"] == 1
        assert data["items"][0]["emp_no"] == "KF770002"

    def test_report_sorted_by_recommend(self):
        resp = client.get("/api/broadband/report", params={"start_date": "2026-06-28", "end_date": "2026-06-29"})
        data = resp.json()
        items = data["items"]
        assert items[0]["emp_no"] == "KF770001"
        assert items[0]["recommend"] >= items[1]["recommend"]

    def test_report_export_csv(self):
        resp = client.get("/api/broadband/report/export", params={
            "start_date": "2026-06-28", "end_date": "2026-06-29"
        })
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        lines = content.strip().splitlines()
        assert lines[0] == "工号,姓名,班组,部门,意向单数量,推荐量,成功推荐,成功率(%)"
        assert any("KF770001" in line and "3" in line.split(",")[6] for line in lines)

    def test_report_month_resolves_full_month(self):
        resp = client.get("/api/broadband/report", params={"year_month": "2026-06"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_recommend"] == 5

    def test_report_export_csv_header_only_when_empty(self):
        resp = client.get("/api/broadband/report/export", params={
            "start_date": "2025-01-01", "end_date": "2025-01-31"
        })
        assert resp.status_code == 200
        lines = resp.content.decode("utf-8").strip().splitlines()
        assert len(lines) == 1