import os
import sys
import json
import base64

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@127.0.0.1:5432/schedule_test')

from fastapi.testclient import TestClient
from app.models.database import Base, engine, SessionLocal, init_db
from app.main import app
from app.core.security import get_current_user

_admin = {"id": 1, "username": "admin", "role": "admin", "is_system": True, "permissions": "{}"}
app.dependency_overrides[get_current_user] = lambda: _admin
client = TestClient(app)


def setup_module():
    Base.metadata.drop_all(bind=engine)
    init_db()


def teardown_module():
    app.dependency_overrides.clear()


def test_provider_crud_and_mask():
    body = {
        "name": "ollama", "base_url": "http://127.0.0.1:11434/v1",
        "api_key": "sk-secret-value", "model": "qwen2.5:72b", "is_default": True,
    }
    r = client.post("/api/llm-providers", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["id"] > 0
    assert data["name"] == "ollama"
    # 密钥脱敏，不应原样返回
    assert data["api_key_masked"] != "sk-secret-value"
    assert "****" in data["api_key_masked"]

    # 列表同样脱敏
    lst = client.get("/api/llm-providers").json()
    assert any(p["name"] == "ollama" for p in lst)

    # 测试连接（无真实服务，应返回 ok 布尔字段）
    t = client.post("/api/llm-providers/test", json={"base_url": "http://127.0.0.1:1/v1", "model": "x", "api_key": "k"})
    assert t.status_code == 200
    assert "ok" in t.json()

    # 默认应为 true
    assert data["is_default"] is True

    # 删除
    d = client.delete(f"/api/llm-providers/{data['id']}")
    assert d.status_code == 200
    assert not any(p["name"] == "ollama" for p in client.get("/api/llm-providers").json())


def test_launcher_default_and_update():
    # 无配置时返回默认值
    g = client.get("/api/llm-providers/launcher")
    assert g.status_code == 200
    assert g.json()["enabled"] is True

    upd = {"enabled": True, "label": "小助手", "icon_type": "emoji", "icon_value": "🚀", "position": "bottom-left", "color": "#67C23A"}
    r = client.put("/api/llm-providers/launcher", json=upd)
    assert r.status_code == 200
    assert r.json()["icon_value"] == "🚀"
    assert r.json()["position"] == "bottom-left"

    # 未知字段不应写入
    again = client.get("/api/llm-providers/launcher").json()
    assert again["label"] == "小助手"
    assert "extra" not in again


def test_agent_chat_no_provider_errors():
    r = client.post("/api/agent/chat", json={"message": "你好"})
    assert r.status_code == 200
    assert '"type": "error"' in r.text


_PNG = base64.b64decode(
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def test_launcher_icon_upload():
    r = client.post(
        "/api/llm-providers/launcher/icon",
        files={"file": ("a.png", _PNG, "image/png")},
    )
    assert r.status_code == 200, r.text
    url = r.json()["url"]
    assert url.startswith("/static/agent-icon-")
    # 上传的文件可被静态服务访问
    got = client.get(url)
    assert got.status_code == 200
    assert got.content == _PNG


def test_launcher_icon_rejects_bad_type():
    r = client.post(
        "/api/llm-providers/launcher/icon",
        files={"file": ("a.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 400


def test_launcher_icon_rejects_oversize():
    big = b"\x00" * (2 * 1024 * 1024 + 100)
    r = client.post(
        "/api/llm-providers/launcher/icon",
        files={"file": ("big.png", big, "image/png")},
    )
    assert r.status_code == 400


def test_launcher_pos_and_draggable():
    upd = {
        "enabled": True, "label": "小助手", "icon_type": "emoji", "icon_value": "🚀",
        "position": "bottom-left", "color": "#67C23A", "draggable": True,
        "pos_x": 120, "pos_y": 240,
    }
    r = client.put("/api/llm-providers/launcher", json=upd)
    assert r.status_code == 200
    data = r.json()
    assert data["pos_x"] == 120
    assert data["pos_y"] == 240
    assert data["draggable"] is True

    again = client.get("/api/llm-providers/launcher").json()
    assert again["pos_x"] == 120
    assert again["pos_y"] == 240


def test_provider_multi_model_crud():
    body = {
        "name": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-x",
        "models": [
            {"model": "deepseek-chat", "is_default": True},
            {"model": "deepseek-reasoner", "is_default": False},
        ],
        "is_default": True,
    }
    r = client.post("/api/llm-providers", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["models"]) == 2
    assert data["model"] == "deepseek-chat"
    # 列表接口返回模型列表
    lst = client.get("/api/llm-providers").json()
    prov = next(p for p in lst if p["name"] == "deepseek")
    assert {m["model"] for m in prov["models"]} == {"deepseek-chat", "deepseek-reasoner"}
    assert prov["models"][0]["model"] == "deepseek-chat"  # 默认排在前

    # 更新：把默认切到 reasoner，并增删模型
    upd = {
        "name": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "models": [
            {"model": "deepseek-chat", "is_default": False},
            {"model": "deepseek-reasoner", "is_default": True},
            {"model": "deepseek-lite", "is_default": False},
        ],
    }
    r2 = client.put(f"/api/llm-providers/{data['id']}", json=upd)
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert d2["model"] == "deepseek-reasoner"
    assert {m["model"] for m in d2["models"]} == {"deepseek-chat", "deepseek-reasoner", "deepseek-lite"}
    assert next(m for m in d2["models"] if m["is_default"])["model"] == "deepseek-reasoner"

    # 删除后子表也清理
    client.delete(f"/api/llm-providers/{data['id']}")


def test_build_chat_model_selection():
    from app.core.llm import build_chat_model
    from app.models.llm_provider import LLMProvider

    p = LLMProvider(name="t", base_url="http://x/v1", model="default-model")
    assert build_chat_model(p).model == "default-model"
    assert build_chat_model(p, model="other-model").model == "other-model"
