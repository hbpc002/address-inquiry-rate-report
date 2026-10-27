"""测试 agent.py 的 SSE 事件生成逻辑，重点是"模型生成工具调用时"的实时进度反馈。

背景：对复杂查询，模型要生成带参数的 SQL 工具调用；此阶段每个流式 chunk 的
content 为空（内容进了 tool_call_chunks），旧逻辑不发任何事件，导致前端长时间
卡在同一个 loading 步骤、最后一起出现。iter_sse_events 应在此阶段节流发 progress。
"""
import os
import sys
import json
import time
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.messages.tool import tool_call_chunk

from app.api.agent import (
    iter_sse_events,
    _with_heartbeat,
    _PROGRESS_TEXTS,
    PROGRESS_INTERVAL,
)


class FakeLLM:
    used_fallback = False
    used_model = None


class FakeGraph:
    def __init__(self, events):
        self._events = events

    async def astream_events(self, inputs, version="v2"):
        for e in self._events:
            yield e


def _ev(event, **data):
    return {"event": event, "data": data}


class FakeClock:
    """可控时钟：调用 advance() 推进虚拟时间。"""
    def __init__(self, start=0.0):
        self.t = start

    def advance(self, delta):
        self.t += delta

    def __call__(self):
        return self.t


class AdvancingClock:
    """每次调用自动推进固定步长的时钟，用于在单一事件流内模拟时间流逝。"""
    def __init__(self, step, start=0.0):
        self.t = start
        self.step = step

    def __call__(self):
        cur = self.t
        self.t += self.step
        return cur


def _content_chunk(text):
    return AIMessage(content=text, tool_call_chunks=[])


def _toolcall_chunk():
    return AIMessage(
        content="",
        tool_call_chunks=[tool_call_chunk(name="report_tool", args='{"a":', id="call_1", index=0)],
    )


async def _collect(events, llm=None, _now=time.monotonic):
    g = FakeGraph(events)
    out = []
    async for s in iter_sse_events(g, llm or FakeLLM(), [HumanMessage(content="q")], _now=_now):
        body = s[len("data: "):].strip()
        out.append(json.loads(body))
    return out


def test_progress_emitted_during_toolcall_generation():
    """content 为空的 tool_call 流式 chunk 应产生 progress 事件。"""
    events = [
        _ev("on_chat_model_start"),
        _ev("on_chat_model_stream", chunk=_toolcall_chunk()),
        _ev("on_chat_model_end", output=AIMessage(
            content="", tool_calls=[{"name": "report_tool", "args": {"a": 1}, "id": "call_1"}],
        )),
    ]
    result = asyncio_run(_collect(events))
    types = [e["type"] for e in result]
    assert "progress" in types, f"缺少 progress 事件: {types}"
    progress = result[types.index("progress")]
    assert progress["text"] in _PROGRESS_TEXTS


def test_token_emitted_for_visible_content():
    """content 非空时发 token 事件。"""
    events = [
        _ev("on_chat_model_stream", chunk=_content_chunk("你好")),
        _ev("on_chat_model_end", output=AIMessage(content="你好")),
    ]
    result = asyncio_run(_collect(events))
    tokens = [e for e in result if e["type"] == "token"]
    assert tokens and tokens[0]["content"] == "你好"


def test_progress_throttled_by_interval():
    """progress 受 PROGRESS_INTERVAL 节流：短时间内的多个空 content chunk 只发一次。"""
    events = [
        _ev("on_chat_model_stream", chunk=_toolcall_chunk()) for _ in range(10)
    ]
    events.append(_ev("on_chat_model_end", output=AIMessage(content="")))
    result = asyncio_run(_collect(events))
    count = sum(1 for e in result if e["type"] == "progress")
    # 时间间隔极小，10 个连续 chunk 只应产生 1 个 progress
    assert count == 1, f"应只发 1 个 progress(节流)，实际 {count}"


def test_progress_rotates_texts_across_intervals():
    """跨过 PROGRESS_INTERVAL 后，进度文案应轮换（反映仍在工作而非卡死）。"""
    # 每次调用虚拟时钟推进两个 interval，使相邻的空 content chunk 落在不同间隔
    clock = AdvancingClock(step=PROGRESS_INTERVAL * 2)
    events = [
        _ev("on_chat_model_stream", chunk=_toolcall_chunk()),
        _ev("on_chat_model_stream", chunk=_toolcall_chunk()),
        _ev("on_chat_model_end", output=AIMessage(content="")),
    ]
    result = asyncio_run(_collect(events, _now=clock))
    texts = [e["text"] for e in result if e["type"] == "progress"]
    assert len(texts) >= 2, f"应产生至少 2 个 progress(跨两个间隔)，实际 {len(texts)}"
    # 文案轮换：两次间隔的文案应不同
    assert texts[0] != texts[1], f"进度文案应轮换，实际均为 {texts[0]}"


def test_status_emitted_when_model_ends_with_tool_calls():
    """模型结束且带 tool_calls 时应发 status「已获取数据，正在汇总分析」。"""
    events = [
        _ev("on_chat_model_end", output=AIMessage(
            content="", tool_calls=[{"name": "report_tool", "args": {}, "id": "call_1"}],
        )),
    ]
    result = asyncio_run(_collect(events))
    assert any(e.get("title") == "已获取数据，正在汇总分析" for e in result)


def test_done_emitted_at_end():
    """正常结束后应发 done。"""
    events = [_ev("on_chat_model_end", output=AIMessage(content="ok"))]
    result = asyncio_run(_collect(events))
    assert result[-1]["type"] == "done"


def test_error_on_exception():
    """内部异常时发 error 而非崩溃。"""

    class BoomGraph(FakeGraph):
        def __init__(self):
            super().__init__([])

        async def astream_events(self, inputs, version="v2"):
            raise RuntimeError("boom")
            yield  # 保持 async generator 语义，让异常在迭代时抛出

    out = []
    async def run():
        async for s in iter_sse_events(BoomGraph(), FakeLLM(), [HumanMessage(content="q")], _now=FakeClock()):
            body = s[len("data: "):].strip()
            out.append(json.loads(body))
    asyncio_run(run())
    assert out[-1]["type"] == "error"
    assert "boom" in out[-1]["message"]


def test_no_notice_event_when_fallback():
    """降级到备用模型时不再向用户输出"主模型限流"notice。"""
    llm = FakeLLM()
    llm.used_fallback = True
    llm.used_model = "backup-model"
    events = [
        _ev("on_chat_model_stream", chunk=_content_chunk("你好")),
        _ev("on_chat_model_end", output=AIMessage(content="你好")),
    ]
    result = asyncio_run(_collect(events, llm=llm))
    assert not any(e["type"] == "notice" for e in result), (
        "不再输出限流 notice，实际: " + str([e for e in result if e["type"] == "notice"])
    )


def test_sse_response_has_streaming_headers():
    """/api/agent/chat 的响应头应包含 SSE 实时透传加固头。"""
    from starlette.responses import StreamingResponse

    async def gen():
        yield "data: {}\n\n"

    resp = StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        },
    )
    assert resp.headers["X-Accel-Buffering"] == "no"
    assert resp.headers["Cache-Control"] == "no-cache, no-transform"
    assert resp.headers["Connection"] == "keep-alive"
    assert resp.media_type == "text/event-stream"


def test_tool_events_include_id_title_subject_duration_and_summary():
    """工具开始/结束事件应携带前端时间线需要的 id、标题、对象、耗时和摘要。"""
    events = [
        _ev(
            "on_tool_start",
            run_id="r1",
            name="query_date_range",
            input={"start_date": "2026-07-01", "end_date": "2026-07-07"},
        ),
        _ev(
            "on_tool_end",
            run_id="r1",
            name="query_date_range",
            output='{"rows":[{"a":1},{"a":2}]}',
        ),
    ]
    result = asyncio_run(_collect(events, _now=AdvancingClock(step=0.05)))
    start = next(e for e in result if e["type"] == "tool_start")
    end = next(e for e in result if e["type"] == "tool_end")
    assert start["id"] == "r1"
    assert start["title"] == "区间汇总"
    assert "2026-07-01" in start["subject"]
    assert end["id"] == "r1"
    assert end["status"] == "success"
    assert end["duration_ms"] is not None
    assert end["summary"] == "返回 2 行"
    assert not any(e["type"] == "status" for e in result)


def test_tool_error_emits_error_status_and_message():
    """工具异常应发 tool_end(status=error)，而不是只留下一个永远 loading 的步骤。"""
    events = [
        _ev("on_tool_start", run_id="r2", name="run_sql", input={"sql_query": "select 1"}),
        _ev("on_tool_error", run_id="r2", name="run_sql", error=RuntimeError("SQL 超时")),
    ]
    result = asyncio_run(_collect(events, _now=AdvancingClock(step=0.02)))
    end = next(e for e in result if e["type"] == "tool_end")
    assert end["id"] == "r2"
    assert end["status"] == "error"
    assert "SQL 超时" in end["error"]
    assert end["summary"] == "执行失败"
    assert end["duration_ms"] is not None


def test_heartbeat_emitted_when_stream_is_idle():
    """长时间无业务事件时应发 SSE 注释心跳，避免代理或浏览器断开。"""
    async def slow_source():
        await asyncio.sleep(0.05)
        yield "data: {}\n\n"

    async def run():
        return [item async for item in _with_heartbeat(slow_source(), interval=0.01)]

    out = asyncio_run(run())
    assert any(item.startswith(": ping") for item in out)
    assert out[-1].startswith("data:")


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)
