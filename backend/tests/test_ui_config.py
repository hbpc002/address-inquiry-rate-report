import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@127.0.0.1:5432/schedule_test')

from fastapi.testclient import TestClient
from app.models.database import Base, engine, SessionLocal, init_db
from app.main import app
from app.core.security import get_current_user, require_permission
from app.models.app_config import AppConfig
from app.api.ui_config import DEFAULT_UI_LABELS

_admin = {"id": 1, "username": "admin", "role": "admin", "is_system": True, "permissions": "{}"}
client = TestClient(app)
_prev_override = None


def setup_module():
    global _prev_override
    Base.metadata.drop_all(bind=engine)
    init_db()
    _prev_override = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: _admin


def teardown_module():
    global _prev_override
    if _prev_override is not None:
        app.dependency_overrides[get_current_user] = _prev_override
    else:
        app.dependency_overrides.pop(get_current_user, None)
    _prev_override = None


def _restore_defaults():
    r = client.put("/api/ui-labels", json=dict(DEFAULT_UI_LABELS))
    assert r.status_code == 200, r.text


def test_ui_labels_defaults():
    r = client.get("/api/ui-labels")
    assert r.status_code == 200
    data = r.json()
    assert data["project_name"] == "客户服务中心运营管理平台"
    assert data["dashboard"] == "工效仪表盘"
    assert data["checkin_report"] == "排班调度"
    assert data["workload_report"] == "团队管理"
    assert data["broadband_report"] == "宽带营销画像"
    assert data["reports"] == "考勤报表"
    assert data["broadband_orders"] == "无缝订单"
    assert data["menu_data"] == "数据管理"
    assert data["menu_system"] == "系统设置"
    assert data["agent"] == "哟你通通"


def test_ui_labels_update_and_persist():
    r = client.put("/api/ui-labels", json={"dashboard": "数据看板", "agent": "小助手", "broadband_report": "宽带画像", "broadband_orders": "订单中心"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["dashboard"] == "数据看板"
    assert data["agent"] == "小助手"
    assert data["broadband_report"] == "宽带画像"
    assert data["broadband_orders"] == "订单中心"
    # 未传入的字段保持默认
    assert data["project_name"] == "客户服务中心运营管理平台"

    # 重新读取确认持久化
    r2 = client.get("/api/ui-labels")
    data2 = r2.json()
    assert data2["dashboard"] == "数据看板"
    assert data2["agent"] == "小助手"
    assert data2["broadband_report"] == "宽带画像"
    assert data2["broadband_orders"] == "订单中心"

    _restore_defaults()


def test_ui_labels_partial_update_and_trims_blank():
    r = client.put("/api/ui-labels", json={"dashboard": "  ", "checkin_report": "值班看板"})
    assert r.status_code == 200, r.text
    data = r.json()
    # 空白字符串不应被写入，保留默认
    assert data["dashboard"] == "工效仪表盘"
    assert data["checkin_report"] == "值班看板"

    _restore_defaults()


def test_ui_labels_update_requires_permission():
    from app.core.security import get_current_user as gcu
    _old = app.dependency_overrides[gcu]
    app.dependency_overrides[gcu] = lambda: {
        "id": 2, "username": "u", "role": "user", "permissions": "{}", "is_system": False,
    }
    try:
        r = client.put("/api/ui-labels", json={"dashboard": "hacked"})
        assert r.status_code == 403
    finally:
        app.dependency_overrides[gcu] = _old


def test_ui_labels_stored_in_app_config():
    db = SessionLocal()
    try:
        rec = db.query(AppConfig).filter(AppConfig.key == "ui_labels").first()
        assert rec is not None, "ui_labels 应写入 app_configs 表"
        stored = json.loads(rec.value)
        assert stored["project_name"] == "客户服务中心运营管理平台"
        assert stored["dashboard"] == "工效仪表盘"
    finally:
        db.close()


def test_default_labels_module_constant():
    assert DEFAULT_UI_LABELS["project_name"] == "客户服务中心运营管理平台"
    assert set(DEFAULT_UI_LABELS.keys()) == {
        "project_name", "dashboard", "checkin_report", "workload_report",
        "broadband_report", "reports", "menu_data", "schedules", "employees",
        "checkins", "training_records", "workload", "broadband_orders",
        "menu_system", "system", "users", "roles", "work_hour_settings",
        "salary_config", "field_annotations", "agent",
    }


def test_admin_has_system_config_permission():
    from app.core.permissions import get_default_permissions, get_all_permission_keys
    assert "system.config" in get_all_permission_keys()
    perms = get_default_permissions("admin")
    assert perms["system.config"] is True