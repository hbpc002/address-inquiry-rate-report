import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@127.0.0.1:5432/schedule_test')

from app.models.database import Base, engine, SessionLocal, init_db
from app.main import app


def setup_module():
    Base.metadata.drop_all(bind=engine)
    init_db()


def teardown_module():
    pass


def test_report_tools_return_json_on_empty_db():
    db = SessionLocal()
    try:
        from app.agent.tools import make_tools
        tools = make_tools(db)
        assert len(tools) >= 6
        by_name = {t.name: t for t in tools}
        # 空库下返回空列表的 JSON
        res = by_name["query_team_ranking"].invoke({"year_month": "2026-07"})
        assert json.loads(res) == []
        res2 = by_name["query_dashboard_stats"].invoke({"year_month": "2026-07"})
        data = json.loads(res2)
        assert "employee_count" in data
    finally:
        db.close()


def test_run_sql_readonly_executes():
    db = SessionLocal()
    try:
        from app.agent.tools import make_tools
        tools = make_tools(db)
        by_name = {t.name: t for t in tools}
        res = by_name["run_sql"].invoke({"sql_query": "SELECT 1 AS n"})
        data = json.loads(res)
        assert data["row_count"] == 1
        assert data["rows"][0]["n"] == 1
    finally:
        db.close()


def test_run_sql_rejects_write():
    """被禁止的 SQL 关键字现在返回结构化错误而非抛异常。"""
    db = SessionLocal()
    try:
        from app.agent.tools import make_tools
        tools = make_tools(db)
        by_name = {t.name: t for t in tools}
        # DROP 语句首先被拦截为"仅允许 SELECT"
        res = by_name["run_sql"].invoke({"sql_query": "DROP TABLE employees"})
        data = json.loads(res)
        assert "error" in data
        assert "SELECT" in data["error"] or "禁止" in data["error"]
        # INSERT 语句被关键字拦截
        res2 = by_name["run_sql"].invoke({"sql_query": "SELECT 1 FROM employees INSERT INTO x VALUES(1)"})
        data2 = json.loads(res2)
        assert "error" in data2
    finally:
        db.close()


def test_run_sql_bad_table_returns_structured_error():
    """不存在的表名返回结构化错误 + 可用表提示。"""
    db = SessionLocal()
    try:
        from app.agent.tools import make_tools
        tools = make_tools(db)
        by_name = {t.name: t for t in tools}
        res = by_name["run_sql"].invoke({"sql_query": "SELECT * FROM attendance"})
        data = json.loads(res)
        assert "error" in data
        assert "hint" in data
        assert "attendance" in data["error"] or "does not exist" in data["error"]
        # hint 中应包含实际可用的表名
        assert "employees" in data["hint"] or "schedules" in data["hint"]
    finally:
        db.close()


def test_run_sql_bad_column_returns_structured_error():
    """不存在的列名返回结构化错误。"""
    db = SessionLocal()
    try:
        from app.agent.tools import make_tools
        tools = make_tools(db)
        by_name = {t.name: t for t in tools}
        res = by_name["run_sql"].invoke({"sql_query": "SELECT nonexistent_col FROM employees"})
        data = json.loads(res)
        assert "error" in data
    finally:
        db.close()


def test_run_sql_tool_description_contains_schema():
    """run_sql 工具描述应包含实际表结构信息。"""
    db = SessionLocal()
    try:
        from app.agent.tools import make_tools
        tools = make_tools(db)
        by_name = {t.name: t for t in tools}
        doc = by_name["run_sql"].description
        # 应包含实际表名
        assert "employees" in doc
        assert "schedules" in doc
        assert "daily_reports" in doc
        # 应包含关键列名
        assert "emp_no" in doc
        assert "schedule_date" in doc
    finally:
        db.close()


def test_build_schema_description_returns_content():
    """_build_schema_description 应返回包含实际表信息的字符串。"""
    db = SessionLocal()
    try:
        from app.agent.tools import _build_schema_description
        desc = _build_schema_description(db)
        assert "employees" in desc
        assert "schedules" in desc
        assert "emp_no" in desc
        assert "schedule_date" in desc
        # 不应包含系统表
        assert "users" not in desc
        assert "roles" not in desc
    finally:
        db.close()


def test_count_consecutive_run_sql_failures():
    """连续 run_sql 失败计数器应正确识别。"""
    from langchain_core.messages import AIMessage, ToolMessage, HumanMessage
    from app.agent.graph import _count_consecutive_run_sql_failures

    # 无 run_sql 调用 → 0
    state1 = {"messages": [HumanMessage("hi"), AIMessage("bye")]}
    assert _count_consecutive_run_sql_failures(state1) == 0

    # 一次 run_sql 成功 → 0
    state2 = {"messages": [
        HumanMessage("hi"),
        AIMessage(content="", tool_calls=[{"name": "run_sql", "args": {}, "id": "c1"}]),
        ToolMessage(content='{"columns":[],"rows":[],"row_count":0}', tool_call_id="c1"),
    ]}
    assert _count_consecutive_run_sql_failures(state2) == 0

    # 一次 run_sql 失败 → 1
    state3 = {"messages": [
        HumanMessage("hi"),
        AIMessage(content="", tool_calls=[{"name": "run_sql", "args": {}, "id": "c1"}]),
        ToolMessage(content='{"error":"bad table"}', tool_call_id="c1"),
    ]}
    assert _count_consecutive_run_sql_failures(state3) == 1

    # 两次连续 run_sql 失败 → 2
    state4 = {"messages": [
        HumanMessage("hi"),
        AIMessage(content="", tool_calls=[{"name": "run_sql", "args": {}, "id": "c1"}]),
        ToolMessage(content='{"error":"bad table"}', tool_call_id="c1"),
        AIMessage(content="", tool_calls=[{"name": "run_sql", "args": {}, "id": "c2"}]),
        ToolMessage(content='{"error":"bad column"}', tool_call_id="c2"),
    ]}
    assert _count_consecutive_run_sql_failures(state4) == 2

    # run_sql 失败后成功 → 仅计数连续失败（成功打断了连续性）
    state5 = {"messages": [
        HumanMessage("hi"),
        AIMessage(content="", tool_calls=[{"name": "run_sql", "args": {}, "id": "c1"}]),
        ToolMessage(content='{"error":"bad"}', tool_call_id="c1"),
        AIMessage(content="", tool_calls=[{"name": "run_sql", "args": {}, "id": "c2"}]),
        ToolMessage(content='{"columns":[],"rows":[],"row_count":0}', tool_call_id="c2"),
    ]}
    assert _count_consecutive_run_sql_failures(state5) == 0

    # 中间穿插其他工具调用 → 0
    state6 = {"messages": [
        HumanMessage("hi"),
        AIMessage(content="", tool_calls=[{"name": "query_daily", "args": {}, "id": "c1"}]),
        ToolMessage(content='[]', tool_call_id="c1"),
        AIMessage(content="", tool_calls=[{"name": "run_sql", "args": {}, "id": "c2"}]),
        ToolMessage(content='{"error":"bad"}', tool_call_id="c2"),
    ]}
    assert _count_consecutive_run_sql_failures(state6) == 1
