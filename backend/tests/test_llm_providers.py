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


def test_launcher_icon_offset_and_scale():
    upd = {
        "enabled": True,
        "icon_type": "url",
        "icon_value": "/static/agent-icon-test.png",
        "icon_offset_x": 12,
        "icon_offset_y": -8,
        "icon_scale": 130,
    }
    r = client.put("/api/llm-providers/launcher", json=upd)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["icon_offset_x"] == 12
    assert data["icon_offset_y"] == -8
    assert data["icon_scale"] == 130

    again = client.get("/api/llm-providers/launcher").json()
    assert again["icon_offset_x"] == 12
    assert again["icon_offset_y"] == -8
    assert again["icon_scale"] == 130

    # 部分更新（不含偏移/缩放字段）应保留已保存的值，而不是重置为默认
    r2 = client.put("/api/llm-providers/launcher", json={"label": "只改文字"})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["label"] == "只改文字"
    assert d2["icon_offset_x"] == 12
    assert d2["icon_offset_y"] == -8
    assert d2["icon_scale"] == 130


def test_launcher_partial_update_preserves_icon():
    # 先保存带 URL 图标的完整配置
    full = {
        "enabled": True,
        "label": "智能助手",
        "icon_type": "url",
        "icon_value": "/static/agent-icon-abc.png",
        "position": "bottom-right",
        "color": "#409EFF",
        "draggable": True,
        "pos_x": 100,
        "pos_y": 200,
    }
    r = client.put("/api/llm-providers/launcher", json=full)
    assert r.status_code == 200, r.text
    assert r.json()["icon_type"] == "url"

    # 模拟拖动悬浮按钮：只更新 pos，不应冲掉已保存的图标配置
    r2 = client.put("/api/llm-providers/launcher", json={"pos_x": 300, "pos_y": 400})
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert d2["pos_x"] == 300
    assert d2["pos_y"] == 400
    assert d2["icon_type"] == "url"
    assert d2["icon_value"] == "/static/agent-icon-abc.png"
    assert d2["label"] == "智能助手"

    # 重新读取，确保持久化且未被重置为默认 emoji
    again = client.get("/api/llm-providers/launcher").json()
    assert again["icon_type"] == "url"
    assert again["icon_value"] == "/static/agent-icon-abc.png"
    assert again["pos_x"] == 300
    assert again["pos_y"] == 400


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
    # 默认重试次数为 7（限流退避后才有机会切 fallback）
    assert build_chat_model(p).max_retries == 7
    assert build_chat_model(p, max_retries=2).max_retries == 2


def _mk_provider(db, name, models):
    from app.core.crypto import encrypt_secret
    from app.models.llm_provider import LLMProvider, LLMProviderModel

    p = LLMProvider(
        name=name, base_url="http://127.0.0.1:1/v1", model=models[0]["model"],
        api_key_encrypted=encrypt_secret("k"),
    )
    db.add(p)
    db.flush()
    for m in models:
        db.add(LLMProviderModel(provider_id=p.id, model=m["model"], is_default=m["is_default"], fallback_order=m.get("fallback_order", 0)))
    db.commit()
    return p


def test_fallback_models_order():
    from app.core.llm import fallback_models
    from app.models.database import SessionLocal
    from app.models.llm_provider import LLMProvider, LLMProviderModel

    db = SessionLocal()
    try:
        p = _mk_provider(db, "fallback-order", [
            {"model": "primary-a", "is_default": True},
            {"model": "backup-2", "is_default": False, "fallback_order": 2},
            {"model": "backup-1", "is_default": False, "fallback_order": 1},
        ])
        chain = fallback_models(db, p)
        names = [m.model for m in chain]
        assert names == ["primary-a", "backup-1", "backup-2"], names
        # 指定主模型时，其余按 fallback_order 升序
        chain2 = fallback_models(db, p, requested_model="backup-2")
        assert [m.model for m in chain2] == ["backup-2", "primary-a", "backup-1"]
    finally:
        db.close()


def test_fallback_crud_via_api():
    body = {
        "name": "fallback-api",
        "base_url": "https://api.example.com/v1",
        "api_key": "sk-x",
        "models": [
            {"model": "main-model", "is_default": True, "fallback_order": 0},
            {"model": "fb-1", "is_default": False, "fallback_order": 1},
            {"model": "fb-2", "is_default": False, "fallback_order": 2},
        ],
    }
    r = client.post("/api/llm-providers", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    fb = {m["model"]: m["fallback_order"] for m in data["models"]}
    assert fb == {"main-model": 0, "fb-1": 1, "fb-2": 2}

    lst = client.get("/api/llm-providers").json()
    prov = next(p for p in lst if p["name"] == "fallback-api")
    assert {m["model"]: m["fallback_order"] for m in prov["models"]} == fb
    client.delete(f"/api/llm-providers/{data['id']}")


def test_fallback_chat_model_switches_on_rate_limit():
    """主模型抛 429 时自动切换到备用模型；全部失败才抛错。"""
    from langchain_core.messages import HumanMessage
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.outputs import ChatGeneration, ChatResult
    from langchain_core.messages import AIMessage
    from openai import RateLimitError
    from app.core.llm import FallbackChatModel
    import httpx

    def rate_limit_error(msg="429 rate limit"):
        req = httpx.Request("POST", "http://test/v1")
        resp = httpx.Response(429, request=req)
        return RateLimitError(msg, response=resp, body={"error": {"message": msg}})

    class Flaky(BaseChatModel):
        model_name: str = "m"
        fail: bool = True

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            if self.fail:
                raise rate_limit_error()
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=f"ok-{self.model_name}"))])

        @property
        def _llm_type(self):
            return "flaky"

    primary = Flaky(model_name="primary", fail=True)
    backup = Flaky(model_name="backup", fail=True)
    rescue = Flaky(model_name="rescue", fail=False)
    chain = FallbackChatModel([primary, backup, rescue])

    out = chain.invoke([HumanMessage("q")])
    assert "ok-rescue" in out.content
    assert chain.used_fallback is True
    assert chain.used_model == "rescue"  # 最终产出答案的是第三个模型

    # 全部成功（未遇限流）不应标记降级
    ok_chain = FallbackChatModel([Flaky(model_name="a", fail=False)])
    assert ok_chain.invoke([HumanMessage("q")]).content == "ok-a"
    assert ok_chain.used_fallback is False

    # 全部失败 → 抛最后限流错误
    all_fail = FallbackChatModel([Flaky(model_name="a", fail=True), Flaky(model_name="b", fail=True)])
    try:
        all_fail.invoke([HumanMessage("q")])
        assert False, "应当抛 RateLimitError"
    except RateLimitError:
        pass
