import json

from openai import RateLimitError
from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.core.security import get_current_user, require_permission
from app.core.llm import (
    get_provider,
    NoProviderError,
    fallback_models,
    build_fallback_model,
)
from app.agent.tools import make_tools, _build_data_range
from app.agent.graph import build_graph, initial_messages

router = APIRouter(prefix="/api/agent", tags=["智能体对话"])


class AgentChatRequest(BaseModel):
    message: str
    provider: str = None
    model: str = None


@router.post("/chat")
async def agent_chat(
    body: AgentChatRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "agent.use")
    if not body.message or not body.message.strip():
        return StreamingResponse(iter([__sse({"type": "error", "message": "消息不能为空"})]), media_type="text/event-stream")

    try:
        provider = get_provider(db, body.provider)
    except NoProviderError as e:
        return StreamingResponse(iter([__sse({"type": "error", "message": str(e)})]), media_type="text/event-stream")

    models = fallback_models(db, provider, body.model)
    llm = build_fallback_model(provider, models)
    tools = make_tools(db)
    graph = build_graph(llm, tools)
    messages = initial_messages(body.message, data_range=_build_data_range(db))

    async def event_stream():
        fallback_notified = False
        try:
            async for ev in graph.astream_events({"messages": messages}, version="v2"):
                kind = ev.get("event")
                if kind == "on_chat_model_stream":
                    chunk = ev["data"]["chunk"]
                    content = chunk.content if isinstance(chunk.content, str) else ""
                    if content:
                        yield __sse({"type": "token", "content": content})
                elif kind == "on_tool_start":
                    yield __sse({
                        "type": "tool_start",
                        "name": ev.get("name"),
                        "input": ev["data"].get("input"),
                    })
                elif kind == "on_tool_end":
                    out = str(ev["data"].get("output"))[:800]
                    yield __sse({"type": "tool_end", "name": ev.get("name"), "output": out})
            if llm.used_fallback and not fallback_notified:
                fallback_notified = True
                yield __sse({"type": "notice", "message": f"主模型限流，已自动切换备用模型 {llm.used_model}"})
            yield __sse({"type": "done"})
        except RateLimitError:
            yield __sse({"type": "error", "message": "模型限流，请稍后重试或降低查询复杂度"})
        except Exception as e:  # noqa: BLE001
            yield __sse({"type": "error", "message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def __sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
