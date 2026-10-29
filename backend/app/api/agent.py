import asyncio
import json
import time
from typing import Optional

from openai import RateLimitError
from langchain_core.messages import AIMessage
from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db, SessionLocal
from app.core.security import get_current_user, require_permission
from app.core.llm import (
    get_provider,
    NoProviderError,
    fallback_models,
    build_fallback_model,
)
from app.agent.tools import make_tools, _build_data_range
from app.agent.graph import build_graph, initial_messages, _message_text
from app.agent.settings import get_settings
from app.services.agent_sessions import (
    add_message,
    can_access_conversation,
    create_conversation,
    finalize_assistant_message,
    get_conversation,
    load_context_messages,
)

# 模型生成工具调用（如 SQL）时 content 为空、无可视文本；节流地发 progress
# 心跳，让前端在最长空白阶段仍有实时反馈。单位：秒。
PROGRESS_INTERVAL = 2.0
# 推理正文的发送节流间隔：避免思考模型每个 token 都发一条 SSE。
REASONING_INTERVAL = 0.25
# 单次模型调用的推理正文保存上限，避免 events 无限膨胀。
REASONING_CHAR_LIMIT = 20000
# SSE 空闲心跳间隔：复杂查询期间即使没有 token/tool 事件，也保持连接活跃。
HEARTBEAT_INTERVAL = 15.0
# 进度文案轮换，避免界面长时间看起来"卡住"
_PROGRESS_TEXTS = [
    "正在分析数据…",
    "正在生成查询…",
    "正在整理结果…",
    "正在比对数据…",
]

_TOOL_TITLES = {
    "query_team_ranking": "班组排名",
    "query_month_summary": "月度汇总",
    "query_date_range": "区间汇总",
    "query_daily": "每日明细",
    "query_efficiency": "月度效能",
    "query_dashboard_stats": "仪表盘统计",
    "run_sql": "自定义查询",
}
_SUBJECT_KEYS = [
    "year_month",
    "start_date",
    "end_date",
    "schedule_date",
    "emp_name",
    "team",
    "month",
    "name",
]

router = APIRouter(prefix="/api/agent", tags=["智能体对话"])


class AgentChatRequest(BaseModel):
    message: str
    provider: str = None
    model: str = None
    conversation_id: Optional[int] = None


@router.post("/chat")
async def agent_chat(
    body: AgentChatRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "agent.use")
    question = (body.message or "").strip()
    if not question:
        return StreamingResponse(
            iter([__sse({"type": "error", "message": "消息不能为空"})]),
            media_type="text/event-stream",
        )

    try:
        provider = get_provider(db, body.provider)
    except NoProviderError as e:
        return StreamingResponse(
            iter([__sse({"type": "error", "message": str(e)})]),
            media_type="text/event-stream",
        )

    models = fallback_models(db, provider, body.model)
    llm = build_fallback_model(provider, models)
    tools = make_tools(db)
    agent_settings = get_settings(db)
    graph = build_graph(llm, tools, settings=agent_settings)
    selected_model = body.model or getattr(provider, "model", None)

    conversation = None
    if body.conversation_id is not None:
        conversation = get_conversation(db, body.conversation_id)
        if not conversation or not can_access_conversation(current_user, conversation):
            return StreamingResponse(
                iter([__sse({"type": "error", "message": "会话不存在或无权访问"})]),
                media_type="text/event-stream",
            )
    if conversation is None:
        conversation = create_conversation(
            db,
            current_user,
            question,
            provider=getattr(provider, "name", None),
            model=selected_model,
        )
    else:
        conversation.provider = getattr(provider, "name", None)
        conversation.model = selected_model

    history_limit = max(0, int(agent_settings.get("max_history_messages", 12)) - 1)
    history = load_context_messages(db, conversation.id, history_limit)
    user_message = add_message(
        db,
        conversation,
        "user",
        question,
        provider=getattr(provider, "name", None),
        model=selected_model,
    )
    assistant_message = add_message(
        db,
        conversation,
        "assistant",
        "",
        events=[],
        status="streaming",
        provider=getattr(provider, "name", None),
        model=selected_model,
        update_preview=False,
    )
    db.commit()
    db.refresh(conversation)
    conversation_id = conversation.id
    assistant_message_id = assistant_message.id
    conversation_title = conversation.title

    messages = initial_messages(
        question,
        data_range=_build_data_range(db),
        settings=agent_settings,
        history=history,
    )

    content_parts = []
    tool_events = []
    state = {"done": False, "error": False}

    def on_event(event: dict):
        event_type = event.get("type")
        if event_type == "token":
            content_parts.append(event.get("content") or "")
        elif event_type in {
            "status", "progress", "reasoning", "tool_start", "tool_end",
            "notice", "error", "done",
        }:
            tool_events.append(event)
        if event_type == "done":
            state["done"] = True
        elif event_type == "error":
            state["error"] = True

    async def event_stream():
        try:
            yield _emit({
                "type": "meta",
                "conversation_id": conversation_id,
                "assistant_message_id": assistant_message_id,
                "user_message_id": user_message.id,
                "title": conversation_title,
            })
            async for chunk in _with_heartbeat(
                iter_sse_events(graph, llm, messages, on_event=on_event)
            ):
                yield chunk
        except asyncio.CancelledError:
            state["error"] = False
            raise
        except Exception:  # noqa: BLE001
            state["error"] = True
            raise
        finally:
            if state["error"]:
                status = "error"
            elif state["done"]:
                status = "complete"
            else:
                status = "stopped"
            save_db = SessionLocal()
            try:
                finalize_assistant_message(
                    save_db,
                    assistant_message_id,
                    "".join(content_parts),
                    tool_events,
                    status,
                )
            except Exception:
                save_db.rollback()
            finally:
                save_db.close()

    # SSE 实时透传加固头：
    #  - X-Accel-Buffering: no  —— 通知 nginx 不要缓冲该响应（某些环境下至关重要）
    #  - Cache-Control: no-cache, no-transform —— 避免代理/浏览器缓存或改写流
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        },
    )


async def _with_heartbeat(source, interval=HEARTBEAT_INTERVAL):
    """包装 SSE 生成器：空闲超过 interval 时发送注释心跳，避免代理断开。"""
    queue = asyncio.Queue(maxsize=64)

    async def produce():
        try:
            async for item in source:
                await queue.put(("event", item))
        except Exception as e:  # noqa: BLE001
            await queue.put(("error", e))
        finally:
            await queue.put(("end", None))

    task = asyncio.create_task(produce())
    try:
        while True:
            try:
                kind, payload = await asyncio.wait_for(queue.get(), timeout=interval)
            except asyncio.TimeoutError:
                yield ": ping\n\n"
                continue
            if kind == "end":
                break
            if kind == "error":
                raise payload
            yield payload
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def _append_missing_text(current: str, text: str) -> str:
    if not text:
        return ""
    if not current:
        return text
    if current.endswith(text) or current.startswith(text):
        return ""
    if text.startswith(current):
        return text[len(current):]
    for size in range(min(len(current), len(text)), 0, -1):
        if current[-size:] == text[:size]:
            return text[size:]
    return text


def _extract_final_text(output) -> str:
    messages = None
    if isinstance(output, dict):
        messages = output.get("messages")
    elif isinstance(output, list):
        messages = output
    elif hasattr(output, "messages"):
        messages = output.messages
    if not messages:
        return ""
    for message in reversed(messages):
        if not isinstance(message, AIMessage):
            continue
        if getattr(message, "tool_calls", None):
            continue
        text = _message_text(getattr(message, "content", ""))
        if text.strip():
            return text
    return ""


def _emit(payload: dict, on_event=None) -> str:
    if on_event:
        try:
            on_event(payload)
        except Exception:  # noqa: BLE001
            pass
    return __sse(payload)


async def iter_sse_events(graph, llm, messages, _now=time.monotonic, on_event=None):
    """把 LangGraph 的 astream_events 转成 SSE 文本序列（可独立测试）。

    - content 非空 → token 事件（逐字流式显示）
    - reasoning 非空 → reasoning 事件（节流发送思考正文）
    - content 为空但带 tool_call_chunks（模型正在生成工具/SQL 参数）→ 节流发
      progress 事件，让前端在最长空白期有实时更新

    _now 为可注入的时钟，便于测试节流/轮换逻辑（默认使用系统的单调时钟）。
    """
    def emit(payload):
        return _emit(payload, on_event)

    emitted_text = ""
    last_progress = None
    progress_idx = 0
    tool_seq = 0
    started = {}
    reasoning_pending = ""
    reasoning_total = 0
    last_reasoning = None
    start_time = _now()
    try:
        async for ev in graph.astream_events({"messages": messages}, version="v2"):
            kind = ev.get("event")
            if kind == "on_chat_model_start":
                yield emit({
                    "type": "status",
                    "id": _run_id(ev),
                    "kind": "thinking",
                    "title": "正在分析问题",
                })
            elif kind == "on_chat_model_stream":
                chunk = ev["data"]["chunk"]
                reasoning = _reasoning_text(chunk)
                if reasoning and reasoning_total < REASONING_CHAR_LIMIT:
                    remaining = REASONING_CHAR_LIMIT - reasoning_total
                    piece = reasoning[:remaining]
                    reasoning_total += len(piece)
                    reasoning_pending += piece
                    cur = _now()
                    if last_reasoning is None or cur - last_reasoning >= REASONING_INTERVAL:
                        yield emit({
                            "type": "reasoning",
                            "id": _run_id(ev),
                            "text": reasoning_pending,
                        })
                        reasoning_pending = ""
                        last_reasoning = cur
                content = chunk.content if isinstance(chunk.content, str) else ""
                if content:
                    if reasoning_pending:
                        yield emit({
                            "type": "reasoning",
                            "id": _run_id(ev),
                            "text": reasoning_pending,
                        })
                        reasoning_pending = ""
                        last_reasoning = _now()
                    emitted_text += content
                    yield emit({"type": "token", "content": content})
                elif getattr(chunk, "tool_call_chunks", None):
                    # 模型在生成工具参数：无可视文本，但可据此判断仍在工作
                    cur = _now()
                    if last_progress is None or cur - last_progress >= PROGRESS_INTERVAL:
                        last_progress = cur
                        text = _PROGRESS_TEXTS[progress_idx % len(_PROGRESS_TEXTS)]
                        progress_idx += 1
                        yield emit({
                            "type": "progress",
                            "id": _run_id(ev),
                            "text": text,
                        })
            elif kind == "on_chat_model_end":
                if reasoning_pending:
                    yield emit({
                        "type": "reasoning",
                        "id": _run_id(ev),
                        "text": reasoning_pending,
                    })
                    reasoning_pending = ""
                    last_reasoning = _now()
                resp = ev["data"]["output"]
                final_reasoning = _reasoning_text(resp)
                if final_reasoning and len(final_reasoning) > reasoning_total:
                    piece = final_reasoning[reasoning_total:REASONING_CHAR_LIMIT]
                    if piece:
                        reasoning_total += len(piece)
                        yield emit({
                            "type": "reasoning",
                            "id": _run_id(ev),
                            "text": piece,
                        })
                tool_calls = getattr(resp, "tool_calls", None)
                if not tool_calls:
                    final_text = _message_text(getattr(resp, "content", ""))
                    missing = _append_missing_text(emitted_text, final_text)
                    if missing:
                        emitted_text += missing
                        yield emit({"type": "token", "content": missing})
                if tool_calls:
                    yield emit({
                        "type": "status",
                        "id": _run_id(ev),
                        "kind": "thinking",
                        "title": "已获取数据，正在汇总分析",
                    })
            elif kind == "on_chain_end":
                final_text = _extract_final_text(ev.get("data", {}).get("output"))
                missing = _append_missing_text(emitted_text, final_text)
                if missing:
                    emitted_text += missing
                    yield emit({"type": "token", "content": missing})
            elif kind == "on_tool_start":
                if reasoning_pending:
                    yield emit({
                        "type": "reasoning",
                        "id": _run_id(ev),
                        "text": reasoning_pending,
                    })
                    reasoning_pending = ""
                    last_reasoning = _now()
                name = _event_name(ev)
                rid = _run_id(ev)
                if not rid:
                    tool_seq += 1
                    rid = f"tool-{tool_seq}"
                input_data = ev["data"].get("input")
                started[rid] = {"start": _now(), "name": name}
                yield emit({
                    "type": "tool_start",
                    "id": rid,
                    "name": name,
                    "input": input_data,
                    "title": _tool_title(name),
                    "subject": _tool_subject(name, input_data),
                })
            elif kind == "on_tool_end":
                name = _event_name(ev)
                rid = _match_started(started, _run_id(ev), name)
                start = started.pop(rid, None)
                out = _output_text(ev["data"].get("output"))
                duration_ms = _elapsed_ms(start, _now())
                yield emit({
                    "type": "tool_end",
                    "id": rid,
                    "name": name,
                    "output": out,
                    "status": "success",
                    "duration_ms": duration_ms,
                    "summary": _tool_summary(out),
                })
            elif kind == "on_tool_error":
                name = _event_name(ev)
                rid = _match_started(started, _run_id(ev), name)
                start = started.pop(rid, None)
                err = ev["data"].get("error")
                message = str(err) if err else "工具执行失败"
                yield emit({
                    "type": "tool_end",
                    "id": rid,
                    "name": name,
                    "status": "error",
                    "error": message,
                    "output": "",
                    "duration_ms": _elapsed_ms(start, _now()),
                    "summary": "执行失败",
                })
        if reasoning_pending:
            yield emit({
                "type": "reasoning",
                "id": None,
                "text": reasoning_pending,
            })
            reasoning_pending = ""
        if not emitted_text.strip():
            fallback = "模型未返回文字结果，请重试或更换模型。"
            emitted_text += fallback
            yield emit({"type": "token", "content": fallback})
        yield emit({"type": "done", "elapsed_ms": _elapsed_ms({"start": start_time}, _now())})
    except RateLimitError:
        yield emit({"type": "error", "message": "模型限流，请稍后重试或降低查询复杂度"})
    except Exception as e:  # noqa: BLE001
        yield emit({"type": "error", "message": str(e)})


def _run_id(ev):
    return ev.get("run_id") or ev.get("data", {}).get("run_id")


def _event_name(ev):
    return ev.get("name") or ev.get("data", {}).get("name")


def _match_started(started, run_id, name):
    """用 run_id 精确匹配；兼容缺失/不匹配的 run_id，按工具名回退。"""
    if run_id in started:
        return run_id
    for rid in reversed(list(started)):
        if started[rid].get("name") == name:
            return rid
    return run_id or name or "tool"


def _elapsed_ms(start, now):
    if not start:
        return None
    return round((now - start["start"]) * 1000)


def _tool_title(name):
    return _TOOL_TITLES.get(name, name or "工具")


def _short_text(value, limit=2000):
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except Exception:  # noqa: BLE001
            text = str(value)
    return text if len(text) <= limit else text[:limit] + "…"


def _tool_subject(name, input_data):
    if not isinstance(input_data, dict):
        return _short_text(input_data, 200)
    if name == "run_sql":
        return _short_text(input_data.get("sql_query") or input_data.get("sql"), 200)
    parts = []
    for key in _SUBJECT_KEYS:
        value = input_data.get(key)
        if value is not None and value != "":
            parts.append(str(value))
    if parts:
        return " · ".join(parts)
    return " · ".join(
        f"{key}={_short_text(value, 60)}" for key, value in list(input_data.items())[:2]
    )


def _output_text(output):
    if output is None:
        return ""
    content = getattr(output, "content", None)
    if content is not None:
        return _short_text(content)
    return _short_text(output)


def _tool_summary(output):
    text = output or ""
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return f"返回 {len(data)} 行"
        if isinstance(data, dict):
            for key in ("rows", "data", "items", "result"):
                if isinstance(data.get(key), list):
                    return f"返回 {len(data[key])} 行"
            if data.get("error"):
                return "查询失败"
    except Exception:  # noqa: BLE001
        pass
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return "无输出"
    return f"{len(lines)} 行输出"


def _reasoning_value_text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_reasoning_value_text(item) for item in value)
    if isinstance(value, dict):
        for key in ("text", "content", "reasoning"):
            text = _reasoning_value_text(value.get(key))
            if text:
                return text
    return ""


def _reasoning_text(chunk) -> str:
    """提取推理类模型（如 Qwen）流式输出的 reasoning 正文。"""
    try:
        for source in (
            getattr(chunk, "additional_kwargs", None),
            getattr(chunk, "response_metadata", None),
        ):
            if not isinstance(source, dict):
                continue
            for key in ("reasoning_content", "reasoning"):
                text = _reasoning_value_text(source.get(key))
                if text:
                    return text
        content = getattr(chunk, "content", None)
        if isinstance(content, list):
            parts = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") not in ("reasoning", "thinking"):
                    continue
                parts.append(_reasoning_value_text(block))
            return "".join(parts)
    except Exception:  # noqa: BLE001
        pass
    return ""


def _reasoning_content(chunk) -> bool:
    """兼容旧调用：判断 chunk 是否包含推理正文。"""
    return bool(_reasoning_text(chunk))


def __sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
