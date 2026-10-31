from datetime import date, datetime
import csv
import io
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.security import create_access_token, get_password_hash
from app.models.app_config import AppConfig
from app.models.checkin import Checkin
from app.models.database import Base, get_db
from app.models.department_group import DepartmentGroup, DepartmentGroupPath
from app.models.employee import Employee
from app.models.marketing_detail import MarketingDetail
from app.models.user import User
from app.models.workload import Workload

TEST_DB_URL = "postgresql://postgres:admin123%40kf@localhost:5432/schedule_test"
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

TARGET_DEPT = "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表"
DEPT_A = f"{TARGET_DEPT}>>A部门"
DEPT_B = f"{TARGET_DEPT}>>B部门"
TEAM = "一班1组"
GROUP_A = "工单运营组"
GROUP_B = "客户投诉处理组"
DAY = date(2026, 10, 20)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        admin = User(
            username="team_scope_admin",
            password_hash=get_password_hash("pass"),
            display_name="测试管理员",
            role="admin",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        group_a = DepartmentGroup(name=GROUP_A, is_active=True)
        group_b = DepartmentGroup(name=GROUP_B, is_active=True)
        inactive_group = DepartmentGroup(name="停用部门组", is_active=False)
        db.add_all([group_a, group_b, inactive_group])
        db.flush()
        db.add_all([
            DepartmentGroupPath(group_id=group_a.id, path=DEPT_A),
            DepartmentGroupPath(group_id=group_b.id, path=DEPT_B),
            DepartmentGroupPath(group_id=group_b.id, path=TARGET_DEPT),
            DepartmentGroupPath(group_id=inactive_group.id, path=DEPT_A),
        ])
        db.commit()

        db.add_all([
            AppConfig(
                key="marketing_overall_row_rules",
                value=json.dumps({"rules": [{
                    "field": "org_name",
                    "match_type": "contains",
                    "pattern": TARGET_DEPT,
                    "row_label": "线上直办-热线",
                    "enabled": True,
                    "priority": 1,
                }]}, ensure_ascii=False),
            ),
            AppConfig(
                key="marketing_key_products",
                value=json.dumps({"products": [{
                    "product_id": "P1",
                    "product_name": "产品1",
                    "business_name": "产品1",
                    "sort": 0,
                }]}, ensure_ascii=False),
            ),
        ])
        db.add_all([
            Employee(emp_no="A001", name="A组长", team=TEAM, dept=DEPT_A, role="组长", status="在职"),
            Employee(emp_no="A002", name="A组员", team=TEAM, dept=DEPT_A, role="组员", status="在职"),
            Employee(emp_no="B001", name="B组长", team=TEAM, dept=DEPT_B, role="组长", status="在职"),
            Employee(emp_no="B002", name="B组员", team=TEAM, dept=DEPT_B, role="组员", status="在职"),
        ])
        db.add_all([
            MarketingDetail(
                kf_id="A002", org_name=DEPT_A, organization=DEPT_A, tenant="A租户",
                data_type="xszb", finish_date=DAY, service_type="叠加包", valid_type="日包",
                trade_id="TA001", product_id="P1", product_name="产品1", lh_qh="来话",
                import_batch="test",
            ),
            MarketingDetail(
                kf_id="B002", org_name=DEPT_B, organization=DEPT_B, tenant="B租户",
                data_type="xszb", finish_date=DAY, service_type="叠加包", valid_type="日包",
                trade_id="TB001", product_id="P1", product_name="产品1", lh_qh="来话",
                import_batch="test",
            ),
        ])
        db.add_all([
            Checkin(
                emp_no="A002", name="A组员", dept=DEPT_A,
                checkin_time=datetime(2026, 10, 20, 8, 0),
                checkout_time=datetime(2026, 10, 20, 18, 0), import_batch="test",
            ),
            Checkin(
                emp_no="B002", name="B组员", dept=DEPT_B,
                checkin_time=datetime(2026, 10, 20, 8, 0),
                checkout_time=datetime(2026, 10, 20, 18, 0), import_batch="test",
            ),
        ])
        db.add_all([
            Workload(
                date=DAY, account="A002", name="A组员", emp_no="A002",
                team_desc=TEAM, metrics={}, import_batch="test",
            ),
            Workload(
                date=DAY, account="B002", name="B组员", emp_no="B002",
                team_desc=TEAM, metrics={}, import_batch="test",
            ),
        ])
        db.commit()
        global TOKEN
        TOKEN = create_access_token(data={"sub": str(admin.id)})
    finally:
        db.close()
    yield


def auth_header():
    return {"Authorization": f"Bearer {TOKEN}"}


def test_team_options_and_leaders_are_scoped_by_dept():
    teams_res = client.get("/api/employees/teams", params={"include_dept": True}, headers=auth_header())
    assert teams_res.status_code == 200
    assert {(item["dept"], item["dept_group"], item["team"]) for item in teams_res.json()} == {
        (DEPT_A, GROUP_A, TEAM), (DEPT_B, GROUP_B, TEAM)
    }

    leaders_res = client.get("/api/employees/leaders", headers=auth_header())
    assert leaders_res.status_code == 200
    leaders = {(item["dept"], item["team"]): item["leader"] for item in leaders_res.json()}
    assert leaders[(DEPT_A, TEAM)] == "A组长"
    assert leaders[(DEPT_B, TEAM)] == "B组长"


def test_marketing_team_rows_and_leaders_do_not_cross_depts():
    res = client.get("/api/marketing/report", params={"date": DAY.isoformat()}, headers=auth_header())
    assert res.status_code == 200
    data = res.json()
    teams = [item for item in data["teams"] if item["team"] == TEAM]
    assert len(teams) == 2
    leaders = {item["dept"]: item["leader"] for item in teams}
    assert leaders == {DEPT_A: "A组长", DEPT_B: "B组长"}
    assert {item["dept"]: item["dept_group"] for item in teams} == {DEPT_A: GROUP_A, DEPT_B: GROUP_B}
    assert {(item["dept"], item["dept_group"], item["team"]) for item in data["options"]["team_options"]} == {
        (DEPT_A, GROUP_A, TEAM), (DEPT_B, GROUP_B, TEAM)
    }
    assert data["options"]["department_groups"] == [GROUP_B, GROUP_A]
    assert "停用部门组" not in data["options"]["department_groups"]


def test_marketing_overall_key_product_rows_are_scoped_by_dept():
    res = client.get(
        "/api/marketing/overall-report",
        params={"start_date": DAY.isoformat(), "end_date": DAY.isoformat()},
        headers=auth_header(),
    )
    assert res.status_code == 200
    rows = [row for row in res.json()["key_product_rows"] if row["team"] == TEAM]
    assert len(rows) == 2
    leaders = {row["dept"]: row["leader"] for row in rows}
    assert leaders == {DEPT_A: "A组长", DEPT_B: "B组长"}
    assert {row["dept"]: row["dept_group"] for row in rows} == {DEPT_A: GROUP_A, DEPT_B: GROUP_B}


def test_marketing_dept_and_class_filters_are_scoped():
    dept_res = client.get(
        "/api/marketing/report",
        params={"date": DAY.isoformat(), "dept": DEPT_A, "class_name": "一班"},
        headers=auth_header(),
    )
    assert dept_res.status_code == 200
    data = dept_res.json()
    assert [item["dept"] for item in data["teams"]] == [DEPT_A]
    assert data["teams"][0]["leader"] == "A组长"
    assert {(item["dept"], item["dept_group"], item["class_name"]) for item in data["options"]["class_options"]} == {
        (DEPT_A, GROUP_A, "一班"), (DEPT_B, GROUP_B, "一班")
    }


def test_marketing_department_group_filter():
    res = client.get(
        "/api/marketing/report",
        params={"date": DAY.isoformat(), "department_group": GROUP_A},
        headers=auth_header(),
    )
    assert res.status_code == 200
    data = res.json()
    assert [item["dept"] for item in data["teams"]] == [DEPT_A]
    assert data["teams"][0]["dept_group"] == GROUP_A


def test_marketing_details_export_csv():
    res = client.get(
        "/api/marketing/details/export",
        params={"start_date": DAY.isoformat(), "end_date": DAY.isoformat()},
        headers=auth_header(),
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert "filename*=UTF-8''" in res.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(res.content.decode("utf-8-sig"))))
    assert rows[0][:8] == ["竣工日期", "数据来源", "客服工号", "姓名", "部门组", "部门", "班组", "行分类"]
    exported = {row[2]: row for row in rows[1:]}
    assert exported["A002"][4] == GROUP_A
    assert exported["B002"][4] == GROUP_B


def test_checkin_report_filters_by_dept():
    res = client.get(
        "/api/checkins/report",
        params={"date": DAY.isoformat(), "dept": DEPT_A, "team": TEAM},
        headers=auth_header(),
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert [item["emp_no"] for item in items] == ["A002"]
    assert items[0]["dept_group"] == GROUP_A


def test_workload_report_returns_dept_and_filters_by_dept():
    res = client.get(
        "/api/workloads/report",
        params={"start_date": DAY.isoformat(), "end_date": DAY.isoformat(), "dept": DEPT_A, "team_desc": TEAM},
        headers=auth_header(),
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["account"] == "A002"
    assert items[0]["dept"] == DEPT_A
    assert items[0]["dept_group"] == GROUP_A
