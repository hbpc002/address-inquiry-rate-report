import io
import os
import sys
from datetime import date
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:admin123%40kf@localhost:5432/schedule_test")

from fastapi.testclient import TestClient
from sqlalchemy import text

import app.models  # noqa: F401
from app.core.security import get_current_user, get_password_hash
from app.main import app
from app.models.app_config import AppConfig
from app.models.database import Base, SessionLocal, engine, init_db
from app.models.employee import Employee
from app.models.marketing_detail import MarketingDetail
from app.models.operation_log import OperationLog
from app.models.user import User

ADMIN = {"id": 1, "username": "marketing_admin", "role": "admin", "is_system": True, "permissions": "{}"}


def _override_user():
    return ADMIN


app.dependency_overrides[get_current_user] = _override_user
client = TestClient(app)

EN_HEADERS = [
    "KF_ID", "RESERVE6", "DATA_TYPE", "POS_SEQUENCE", "DEVELOP_DEPART_NAME",
    "CHANNEL", "AREA_NAME", "TRADE_ID", "FINISH_DATE", "SERVICE_TYPE",
    "PACKAGE_TYPE", "VALID_TYPE", "PRODUCT_ID", "PRODUCT_NAME", "LH_QH",
]

CN_HEADERS = [
    "客服id", "预留字段6", "重点业务分类", "叠加包分类", "叠加包有效期",
    "CBSS订单竣工时间", "产品ID", "产品名称", "来话去话", "CBSS订单号",
    "受理渠道", "人员岗位性质", "发展渠道",
]


def setup_module():
    Base.metadata.drop_all(bind=engine)
    init_db()
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.id == 1).first():
            db.add(User(id=1, username="marketing_admin", password_hash=get_password_hash("x"), role="admin", is_active=True))
            db.commit()
    finally:
        db.close()


def teardown_module():
    app.dependency_overrides.clear()


def _clean():
    db = SessionLocal()
    try:
        db.query(MarketingDetail).delete()
        db.query(Employee).delete()
        db.query(AppConfig).filter(AppConfig.key.in_([
            "marketing_group_rules", "marketing_overall_row_rules"
        ])).delete(synchronize_session=False)
        db.query(OperationLog).delete()
        db.commit()
    finally:
        db.close()


def _seed_employees():
    db = SessionLocal()
    try:
        db.add_all([
            Employee(emp_no="KF001", name="张三", team="热线一组", dept="客服部", status="在职"),
            Employee(emp_no="KF002", name="李四", team="区域二组", dept="客服部", status="在职"),
        ])
        db.commit()
    finally:
        db.close()


def _make_xlsx(headers, rows, pre_rows=None):
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    for row in pre_rows or []:
        ws.append(row)
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _en_row(kf="KF001", org="广西分公司>>省中心>>客户服务营销中心>>热线运营组",
            service="叠加包", valid="月包", finish="20261001120000", product_id="P1",
            product_name="测试产品", lh="来话", trade="T1", channel="热线人工",
            data_type="xszb", pos="一线坐席-10010", depart="10010", area="南宁"):
    return [kf, org, data_type, pos, depart, channel, area, trade, finish,
            service, "流量", valid, product_id, product_name, lh]


def _cn_row(kf="KF001", org="广西分公司>>省中心>>客户服务营销中心>>热线运营组",
            service="叠加包", valid="月包", finish="20261002120000", product_id="P1",
            product_name="测试产品", lh="来话", trade="T1", channel="热线人工",
            pos="一线坐席-10010", depart="10010"):
    return [kf, org, service, "流量", valid, finish, product_id, product_name,
            lh, trade, channel, pos, depart]


def _upload(headers, rows, pre_rows=None, filename="marketing.xlsx"):
    data = {"file": (filename, _make_xlsx(headers, rows, pre_rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    return client.post("/api/marketing/details/import", files=data)


def _set_group_rules(default_group, rules):
    payload = {"default_group": default_group, "rules": rules}
    resp = client.put("/api/marketing/group-rules", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _set_overall_rules(rules):
    resp = client.put("/api/marketing/overall-row-rules", json={"rules": rules})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _overall_row(report, label):
    return next(row for row in report["rows"] if row["label"] == label)


class TestMarketingImport:

    def setup_method(self):
        _clean()
        _seed_employees()

    def test_import_english_header_and_report(self):
        rows = [
            _en_row(trade="T1", product_id="P1", service="叠加包", valid="月包", lh="来话"),
            _en_row(trade="T2", product_id="P2", service="叠加包", valid="日包", lh="去话"),
            _en_row(kf="KF002", org="南方二中心>>通软-在线>>李智", trade="T3", product_id="P3",
                    service="套餐适配", valid="", lh="来话"),
            _en_row(kf="KF999", org="广西分公司>>省中心>>客户服务部>>客户关系运营中心",
                    trade="T4", product_id="P4", service="叠加包", valid="长期", lh="来话"),
        ]
        resp = _upload(EN_HEADERS, rows)
        assert resp.status_code == 200, resp.text
        assert resp.json()["count"] == 4

        _set_group_rules("未分组", [
            {"group_name": "区域", "match_type": "contains", "pattern": "南方二中心", "priority": 1, "enabled": True},
            {"group_name": "维系组", "match_type": "contains", "pattern": "客户关系运营中心", "priority": 2, "enabled": True},
        ])
        report = client.get("/api/marketing/report", params={"year_month": "2026-10"}).json()
        assert report["stats"]["total"] == 4
        assert report["stats"]["overlay"] == 3
        assert report["stats"]["package_change"] == 1
        assert report["stats"]["inbound"] == 3
        assert report["stats"]["outbound"] == 1
        assert report["stats"]["people_count"] == 3
        assert set(report["options"]["groups"]) == {"未分组", "区域", "维系组"}
        emp = next(item for item in report["employees"] if item["kf_id"] == "KF999")
        assert emp["name"] == ""
        assert emp["team"] == "未匹配班组"
        assert emp["group_name"] == "维系组"

    def test_import_chinese_header_and_same_date_overwrite(self):
        first = _upload(CN_HEADERS, [_cn_row(product_id="OLD", product_name="旧产品")])
        assert first.status_code == 200, first.text
        second = _upload(CN_HEADERS, [_cn_row(product_id="NEW", product_name="新产品")])
        assert second.status_code == 200, second.text
        details = client.get("/api/marketing/details", params={"start_date": "2026-10-02", "end_date": "2026-10-02"}).json()
        assert details["total"] == 1
        assert details["items"][0]["product_id"] == "NEW"

    def test_import_detects_header_after_title_rows(self):
        resp = _upload(CN_HEADERS, [_cn_row()], pre_rows=[["营销明细"], ["导出时间", "2026-10-20"]])
        assert resp.status_code == 200, resp.text
        assert resp.json()["count"] == 1

    def test_import_invalid_file(self):
        data = {"file": ("bad.xlsx", io.BytesIO(b"not excel"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = client.post("/api/marketing/details/import", files=data)
        assert resp.status_code == 400


class TestMarketingReport:

    def setup_method(self):
        _clean()
        _seed_employees()

    def test_business_type_valid_type_and_lh_filters(self):
        rows = [
            _en_row(trade="T1", product_id="P1", service="叠加包", valid="日包", lh="去话"),
            _en_row(trade="T2", product_id="P2", service="叠加包", valid="月包", lh="来话"),
            _en_row(trade="T3", product_id="P3", service="叠加包", valid="长期", lh="来话"),
            _en_row(trade="T4", product_id="P4", service="叠加包", valid="", lh="来话"),
            _en_row(trade="T5", product_id="P5", service="套餐适配", valid="", lh="来话"),
        ]
        assert _upload(EN_HEADERS, rows).status_code == 200
        report = client.get("/api/marketing/report", params={"start_date": "2026-10-01", "end_date": "2026-10-01"}).json()
        stats = report["stats"]
        assert stats["overlay"] == 4
        assert stats["overlay_day"] == 1
        assert stats["overlay_month"] == 1
        assert stats["overlay_long"] == 1
        assert stats["overlay_undefined"] == 1
        assert stats["package_change"] == 1

        filtered = client.get("/api/marketing/report", params={
            "start_date": "2026-10-01", "end_date": "2026-10-01",
            "business_type": "叠加包", "valid_type": "日包", "lh_qh": "去话",
        }).json()
        assert filtered["stats"]["total"] == 1
        assert filtered["employees"][0]["kf_id"] == "KF001"

    def test_group_rule_priority_and_default(self):
        rows = [
            _en_row(kf="KF001", org="A>>维系>>投诉中心", trade="T1", product_id="P1"),
            _en_row(kf="KF002", org="未知组织", trade="T2", product_id="P2"),
        ]
        assert _upload(EN_HEADERS, rows).status_code == 200
        _set_group_rules("默认组", [
            {"group_name": "投诉工单组", "match_type": "contains", "pattern": "投诉中心", "priority": 1, "enabled": True},
            {"group_name": "维系组", "match_type": "contains", "pattern": "维系", "priority": 10, "enabled": True},
        ])
        report = client.get("/api/marketing/report", params={"year_month": "2026-10"}).json()
        groups = {item["group_name"]: item for item in report["groups"]}
        assert groups["投诉工单组"]["total"] == 1
        assert groups["默认组"]["total"] == 1
        assert "维系组" not in groups
        rules = client.get("/api/marketing/group-rules").json()
        assert rules["default_group"] == "默认组"
        assert len(rules["rules"]) == 2

    def test_overall_report_structure_subtotal_and_unclassified(self):
        rows = [
            _en_row(kf="KF001", org="广西分公司>>热线运营组", trade="T1", product_id="P1", service="叠加包", valid="月包"),
            _en_row(kf="KF002", org="南方二中心>>通软-在线", trade="T2", product_id="P2", service="套餐适配", valid=""),
            _en_row(kf="KF001", org="未知组织", trade="T3", product_id="P3", service="叠加包", valid="日包"),
        ]
        assert _upload(EN_HEADERS, rows).status_code == 200
        _set_overall_rules([
            {"row_label": "线上直办-热线", "field": "org_name", "match_type": "contains", "pattern": "热线运营组", "priority": 1, "enabled": True},
            {"row_label": "线上直办-区域", "field": "org_name", "match_type": "contains", "pattern": "南方二中心", "priority": 2, "enabled": True},
        ])
        report = client.get("/api/marketing/overall-report", params={"year_month": "2026-10"}).json()
        assert len(report["rows"]) == 14
        hotline = _overall_row(report, "线上直办-热线")
        area = _overall_row(report, "线上直办-区域")
        sub1 = next(row for row in report["rows"] if row["section_no"] == 1 and row["is_subtotal"])
        assert hotline["counts"]["overlay"] == 1
        assert area["counts"]["package_change"] == 1
        assert sub1["counts"]["overlay"] == 1
        assert sub1["counts"]["package_change"] == 1
        assert sub1["total"] == 2
        assert report["stats"]["grand_total"] == 2
        assert report["stats"]["unclassified_rows"] == 1
        assert report["total_row"]["total"] == 2
        assert hotline["rowspan"] == 6
        assert report["rows"][1]["rowspan"] == 0

    def test_overall_export_has_style_merge_and_formulas(self):
        assert _upload(EN_HEADERS, [_en_row(org="热线运营组")]).status_code == 200
        _set_overall_rules([
            {"row_label": "线上直办-热线", "field": "org_name", "match_type": "contains", "pattern": "热线运营组", "priority": 1, "enabled": True},
        ])
        resp = client.get("/api/marketing/overall-report/export", params={"year_month": "2026-10"})
        assert resp.status_code == 200
        wb = load_workbook(io.BytesIO(resp.content))
        ws = wb["总体营销"]
        assert ws["A1"].value == "序号"
        assert ws["C1"].font.color.rgb == "FFFF0000"
        assert ws["A2"].value == 1
        assert any(str(rng) == "A2:A7" for rng in ws.merged_cells.ranges)
        assert ws["H2"].value == "=SUM(C2:G2)"
        assert str(ws["I2"].value).startswith("=IFERROR")
        assert ws["A16"].value == "合计"
        assert ws["B2"].value == "线上直办-热线"

    def test_delete_details_by_date_and_batch(self):
        resp = _upload(EN_HEADERS, [_en_row()])
        batch = resp.json()["batch"]
        details = client.get("/api/marketing/details").json()
        assert details["total"] == 1
        deleted = client.delete(f"/api/marketing/details/import/{batch}")
        assert deleted.status_code == 200
        assert deleted.json()["count"] == 1
        assert client.get("/api/marketing/details").json()["total"] == 0
