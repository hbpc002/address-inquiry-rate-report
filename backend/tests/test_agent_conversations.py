import os
import sys
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from langchain_core.messages import AIMessage
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api import agent as agent_api
from app.api import agent_conversations
from app.core.security import get_current_user
from app.models.agent_conversation import AgentConversation
from app.models.agent_message import AgentMessage
from app.models.database import Base, get_db
from app.models.role import Role
from app.models.user import User
from app.agent.settings import validate_settings
from app.services.agent_sessions import (
    add_message,
    cleanup_expired_conversations,
    create_conversation,
    finalize_assistant_message,
    load_context_messages,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[Role.__table__, User.__table__, AgentConversation.__table__, AgentMessage.__table__],
    )
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(
            bind=engine,
            tables=[AgentMessage.__table__, AgentConversation.__table__, User.__table__, Role.__table__],
        )


@pytest.fixture()
def users(db_session):
    role = Role(name="user", permissions="{}")
    db_session.add(role)
    db_session.flush()
    user_a = User(username="alice", password_hash="x", display_name="Alice", role="user", role_id=role.id)
    user_b = User(username="bob", password_hash="x", display_name="Bob", role="user", role_id=role.id)
    db_session.add_all([user_a, user_b])
    db_session.commit()
    return user_a, user_b


@pytest.fixture()
def client(db_session):
    current = {"user": None}

    def override_db():
        yield db_session

    def override_user():
        return current["user"]

    app = FastAPI()
    app.include_router(agent_conversations.router)
    app.include_router(agent_api.router)
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    test_client = TestClient(app)
    test_client.current = current
    return test_client


def _as(user):
    return {"id": user.id, "username": user.username, "role": "admin", "is_system": True, "permissions": "{}"}


def _normal(user):
    return {
        "id": user.id,
        "username": user.username,
        "role": "user",
        "is_system": False,
        "permissions": '{"agent.use": true}',
    }


def test_conversation_isolation_and_admin_visibility(client, db_session, users):
    user_a, user_b = users
    conv_a = create_conversation(db_session, _normal(user_a), "Alice 的会话")
    add_message(db_session, conv_a, "user", "Alice 的会话")
    conv_b = create_conversation(db_session, _normal(user_b), "Bob 的会话")
    add_message(db_session, conv_b, "user", "Bob 的会话")
    db_session.commit()

    client.current["user"] = _normal(user_a)
    data = client.get("/api/agent/conversations").json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == conv_a.id

    assert client.get(f"/api/agent/conversations/{conv_b.id}").status_code == 404

    client.current["user"] = _as(user_a)
    data = client.get("/api/agent/conversations").json()
    assert data["total"] == 2
    assert {item["owner_name"] for item in data["items"]} == {"Alice", "Bob"}
    assert client.get(f"/api/agent/conversations/{conv_b.id}").status_code == 200


def test_search_pin_rename_and_delete(client, db_session, users):
    user_a, _ = users
    conv_a = create_conversation(db_session, _normal(user_a), "最近一周工时")
    add_message(db_session, conv_a, "user", "最近一周谁工时最低")
    conv_b = create_conversation(db_session, _normal(user_a), "本月迟到名单")
    add_message(db_session, conv_b, "user", "本月迟到次数最多的人")
    db_session.commit()
    client.current["user"] = _normal(user_a)

    data = client.get("/api/agent/conversations", params={"q": "迟到"}).json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == conv_b.id

    pinned = client.patch(
        f"/api/agent/conversations/{conv_b.id}", json={"is_pinned": True}
    ).json()
    assert pinned["is_pinned"] is True
    data = client.get("/api/agent/conversations").json()
    assert data["items"][0]["id"] == conv_b.id

    renamed = client.patch(
        f"/api/agent/conversations/{conv_a.id}", json={"title": "新标题"}
    ).json()
    assert renamed["title"] == "新标题"

    assert client.delete(f"/api/agent/conversations/{conv_a.id}").status_code == 200
    data = client.get("/api/agent/conversations").json()
    assert all(item["id"] != conv_a.id for item in data["items"])
    deleted = db_session.query(AgentConversation).filter(AgentConversation.id == conv_a.id).first()
    assert deleted.deleted_at is not None


def test_context_messages_and_assistant_finalize(db_session, users):
    user_a, _ = users
    conv = create_conversation(db_session, _normal(user_a), "上下文")
    for index in range(5):
        add_message(db_session, conv, "user", f"问题{index}")
        add_message(db_session, conv, "assistant", f"回答{index}", events=[{"type": "done"}])
    db_session.commit()

    history = load_context_messages(db_session, conv.id, 5)
    assert len(history) == 4
    assert history[0]["role"] == "user"
    assert history[-1]["content"] == "回答4"

    message = add_message(
        db_session,
        conv,
        "assistant",
        "",
        events=[],
        status="streaming",
        update_preview=False,
    )
    db_session.commit()
    finalize_assistant_message(
        db_session,
        message.id,
        "最终回答",
        [{"type": "status", "title": "分析"}],
        "complete",
    )
    updated = db_session.query(AgentMessage).filter(AgentMessage.id == message.id).first()
    assert updated.content == "最终回答"
    assert updated.status == "complete"
    assert updated.events[0]["title"] == "分析"
    refreshed = db_session.query(AgentConversation).filter(AgentConversation.id == conv.id).first()
    assert refreshed.last_message_preview == "最终回答"


def test_cleanup_retains_pinned_and_purges_old_deleted(db_session, users):
    user_a, _ = users
    now = datetime.utcnow()
    old = create_conversation(db_session, _normal(user_a), "旧会话")
    old.last_message_at = now - timedelta(days=30)
    pinned = create_conversation(db_session, _normal(user_a), "置顶会话")
    pinned.is_pinned = True
    pinned.last_message_at = now - timedelta(days=30)
    deleted = create_conversation(db_session, _normal(user_a), "已删除")
    deleted.deleted_at = now - timedelta(days=10)
    db_session.commit()

    old_id = old.id
    pinned_id = pinned.id
    deleted_id = deleted.id
    removed = cleanup_expired_conversations(db_session, 7, now=now)
    db_session.expunge_all()
    assert removed == 1
    assert db_session.query(AgentConversation).filter(AgentConversation.id == old_id).first().deleted_at is not None
    assert db_session.query(AgentConversation).filter(AgentConversation.id == pinned_id).first().deleted_at is None
    assert db_session.query(AgentConversation).filter(AgentConversation.id == deleted_id).first() is None


def test_retention_setting_bounds():
    assert validate_settings({"conversation_retention_days": 0}) == {
        "conversation_retention_days": 0
    }
    assert validate_settings({"conversation_retention_days": 3650}) == {
        "conversation_retention_days": 3650
    }
    with pytest.raises(ValueError):
        validate_settings({"conversation_retention_days": -1})
    with pytest.raises(ValueError):
        validate_settings({"conversation_retention_days": 3651})


class _FakeProvider:
    name = "fake"
    model = "fake-model"


class _FakeGraph:
    def __init__(self):
        self.inputs = []

    async def astream_events(self, inputs, version="v2"):
        self.inputs.append(inputs["messages"])
        yield {
            "event": "on_chat_model_stream",
            "data": {"chunk": AIMessage(content="答案")},
        }
        yield {
            "event": "on_chat_model_end",
            "data": {"output": AIMessage(content="答案")},
        }


def test_chat_persists_messages_meta_and_uses_db_history(client, db_session, users, monkeypatch):
    user_a, _ = users
    client.current["user"] = _normal(user_a)
    graph = _FakeGraph()

    monkeypatch.setattr(agent_api, "get_provider", lambda db, name: _FakeProvider())
    monkeypatch.setattr(agent_api, "fallback_models", lambda db, provider, model: ["fake-model"])
    monkeypatch.setattr(agent_api, "build_fallback_model", lambda provider, models: object())
    monkeypatch.setattr(agent_api, "make_tools", lambda db: [])
    monkeypatch.setattr(
        agent_api,
        "get_settings",
        lambda db: {
            "system_prompt": "系统日期 {current_date}",
            "max_history_messages": 12,
        },
    )
    monkeypatch.setattr(agent_api, "build_graph", lambda llm, tools, settings=None: graph)
    monkeypatch.setattr(agent_api, "_build_data_range", lambda db: "")
    monkeypatch.setattr(agent_api, "SessionLocal", lambda: SessionLocalFor(db_session))

    response = client.post("/api/agent/chat", json={"message": "最近一周谁工时最低"})
    assert response.status_code == 200
    assert '"type": "meta"' in response.text
    assert "答案" in response.text

    conversation = db_session.query(AgentConversation).first()
    assert conversation is not None
    assert conversation.title == "最近一周谁工时最低"
    messages = (
        db_session.query(AgentMessage)
        .filter(AgentMessage.conversation_id == conversation.id)
        .order_by(AgentMessage.id)
        .all()
    )
    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[1].content == "答案"
    assert messages[1].status == "complete"
    assert any(e.get("type") == "done" for e in messages[1].events)

    second = client.post(
        "/api/agent/chat",
        json={"message": "那乙班呢？", "conversation_id": conversation.id},
    )
    assert second.status_code == 200
    assert len(graph.inputs) == 2
    contents = [getattr(m, "content", "") for m in graph.inputs[1]]
    assert "最近一周谁工时最低" in contents
    assert "答案" in contents
    assert contents[-1] == "那乙班呢？"


def SessionLocalFor(db_session):
    class _Session:
        def __init__(self):
            self._db = db_session

        def __getattr__(self, name):
            return getattr(self._db, name)

        def close(self):
            pass

    return _Session()
