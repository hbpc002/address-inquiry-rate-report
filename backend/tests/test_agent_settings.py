import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@127.0.0.1:5432/schedule_test')

from fastapi.testclient import TestClient
from app.models.database import Base, engine, SessionLocal, init_db
from app.main import app
from app.core.security import get_current_user
from app.models.app_config import AppConfig
from app.agent.settings import DEFAULT_SETTINGS, get_settings, validate_settings

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
    r = client.post("/api/agent-settings/reset")
    assert r.status_code == 200, r.text


def test_default_settings_structure():
    assert set(DEFAULT_SETTINGS.keys()) == {
        "system_prompt", "suggestions", "max_iterations",
        "max_history_messages", "consecutive_run_sql_failures",
    }
    assert "{current_date}" in DEFAULT_SETTINGS["system_prompt"]
    assert "{data_range}" in DEFAULT_SETTINGS["system_prompt"]
    assert DEFAULT_SETTINGS["max_iterations"] == 6
    assert DEFAULT_SETTINGS["max_history_messages"] == 12
    assert DEFAULT_SETTINGS["consecutive_run_sql_failures"] == 2
    assert len(DEFAULT_SETTINGS["suggestions"]) == 4


def test_get_defaults():
    r = client.get("/api/agent-settings")
    assert r.status_code == 200
    data = r.json()
    assert data["system_prompt"] == DEFAULT_SETTINGS["system_prompt"]
    assert data["suggestions"] == DEFAULT_SETTINGS["suggestions"]
    assert data["max_iterations"] == 6
    _restore_defaults()


def test_update_and_persist():
    r = client.put("/api/agent-settings", json={
        "system_prompt": "自定义提示词 {current_date}",
        "suggestions": ["问题A", "问题B"],
        "max_iterations": 8,
        "max_history_messages": 16,
        "consecutive_run_sql_failures": 3,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["system_prompt"] == "自定义提示词 {current_date}"
    assert data["suggestions"] == ["问题A", "问题B"]
    assert data["max_iterations"] == 8
    assert data["max_history_messages"] == 16
    assert data["consecutive_run_sql_failures"] == 3

    # 重新读取确认持久化
    r2 = client.get("/api/agent-settings")
    data2 = r2.json()
    assert data2["system_prompt"] == "自定义提示词 {current_date}"
    assert data2["max_iterations"] == 8

    # 存入 app_configs
    db = SessionLocal()
    try:
        rec = db.query(AppConfig).filter(AppConfig.key == "agent_settings").first()
        assert rec is not None, "agent_settings 应写入 app_configs 表"
        stored = json.loads(rec.value)
        assert stored["max_iterations"] == 8
    finally:
        db.close()

    _restore_defaults()


def test_partial_update_keeps_other_fields():
    r = client.put("/api/agent-settings", json={"max_iterations": 10})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["max_iterations"] == 10
    # 其他字段保持默认
    assert data["system_prompt"] == DEFAULT_SETTINGS["system_prompt"]
    assert data["suggestions"] == DEFAULT_SETTINGS["suggestions"]
    _restore_defaults()


def test_validation_rejects_bad_params():
    r = client.put("/api/agent-settings", json={"max_iterations": 0})
    assert r.status_code == 422
    r = client.put("/api/agent-settings", json={"max_iterations": 100})
    assert r.status_code == 422
    r = client.put("/api/agent-settings", json={"system_prompt": "   "})
    assert r.status_code == 422
    r = client.put("/api/agent-settings", json={"suggestions": "not-a-list"})
    assert r.status_code == 422


def test_reset_restores_defaults():
    client.put("/api/agent-settings", json={"max_iterations": 15})
    r = client.post("/api/agent-settings/reset")
    assert r.status_code == 200
    data = r.json()
    assert data["max_iterations"] == DEFAULT_SETTINGS["max_iterations"]
    assert data["system_prompt"] == DEFAULT_SETTINGS["system_prompt"]
    # reset 后 GET 也应回到默认
    r2 = client.get("/api/agent-settings")
    assert r2.json()["max_iterations"] == 6


def test_update_requires_permission():
    from app.core.security import get_current_user as gcu
    _old = app.dependency_overrides[gcu]
    app.dependency_overrides[gcu] = lambda: {
        "id": 2, "username": "u", "role": "user", "permissions": "{}", "is_system": False,
    }
    try:
        r = client.put("/api/agent-settings", json={"max_iterations": 9})
        assert r.status_code == 403
        r = client.post("/api/agent-settings/reset")
        assert r.status_code == 403
    finally:
        app.dependency_overrides[gcu] = _old


def test_get_settings_merges_stored():
    db = SessionLocal()
    try:
        rec = db.query(AppConfig).filter(AppConfig.key == "agent_settings").first()
        if rec:
            db.delete(rec)
            db.commit()
        # 无记录 → 默认
        s = get_settings(db)
        assert s["max_iterations"] == 6
        # 写入自定义
        rec = AppConfig(key="agent_settings", value=json.dumps({"max_iterations": 9}))
        db.add(rec)
        db.commit()
        s = get_settings(db)
        assert s["max_iterations"] == 9
        assert s["system_prompt"] == DEFAULT_SETTINGS["system_prompt"]
    finally:
        db.close()
        _restore_defaults()


def test_validate_settings_bounds():
    assert validate_settings({"max_iterations": 6}) == {"max_iterations": 6}
    assert validate_settings({"suggestions": [" a ", "", "b"]})["suggestions"] == ["a", "b"]
    try:
        validate_settings({"max_history_messages": 1})
        assert False, "应抛出 ValueError"
    except ValueError:
        pass


def test_initial_messages_uses_custom_prompt():
    from app.agent.graph import initial_messages
    settings = {"system_prompt": "你是测试机器人。日期 {current_date}"}
    msgs = initial_messages("你好", settings=settings)
    assert msgs[0].content.startswith("你是测试机器人。")
    assert "日期 20" in msgs[0].content


def test_llm_error_mentions_agent_config():
    from app.core.llm import get_provider, NoProviderError
    db = SessionLocal()
    try:
        try:
            get_provider(db, None)
            assert False, "应抛出 NoProviderError"
        except NoProviderError as e:
            assert "智能体配置" in str(e)
    finally:
        db.close()
