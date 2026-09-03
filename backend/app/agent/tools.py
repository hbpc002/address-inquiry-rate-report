"""智能体工具集：复用报表查询逻辑 + 只读 text-to-SQL。"""
import json

from sqlalchemy import text, inspect
from langchain_core.tools import tool

from app.services import report_queries
from app.agent.sql_safe import validate_sql

# 单次工具结果回传给 LLM 的最大长度，避免长 JSON 撑爆每轮令牌预算
MAX_RESULT_CHARS = 2000
# run_sql 回传的最大行数（原始 SQL 仍受 sql_safe.MAX_ROWS=200 约束）
MAX_RESULT_ROWS = 50


def _cap(text_out: str, limit: int = MAX_RESULT_CHARS) -> str:
    if len(text_out) <= limit:
        return text_out
    return text_out[:limit] + f" ...【结果过长已截断，共 {len(text_out)} 字符】"


def _rows_to_dicts(result) -> list:
    cols = list(result.keys())
    out = []
    for row in result:
        item = {}
        for col, val in zip(cols, row):
            item[col] = val if not hasattr(val, "isoformat") else val.isoformat()
            if isinstance(item[col], (bytes,)):
                item[col] = item[col].decode("utf-8", "replace")
        out.append(item)
    return out


# ── 动态表结构：从 SQLAlchemy metadata 自动生成紧凑的 schema 描述 ────────────

# 与考勤报表无关的系统/配置表，不暴露给 LLM 以避免干扰
_SKIP_TABLES = frozenset({
    "users", "roles", "llm_providers", "llm_provider_models",
    "app_configs", "operation_logs", "field_annotations",
    "attendance_configs", "salary_configs", "work_hour_thresholds",
    "announcements",
})

# 只展示给 LLM 的核心列（精简以控制 token 数）
_SHOW_COLUMNS = {
    "employees": {"emp_no", "name", "team", "dept", "status", "hire_date"},
    "schedules": {"emp_id", "schedule_date", "shift_name", "work_hours", "is_night",
                  "schedule_type", "punctuality_rate", "call_duration",
                  "organize_duration", "utilization_rate", "attendance_rate"},
    "daily_reports": {"emp_id", "schedule_date", "shift_type_id", "schedule_type",
                      "scheduled_start", "scheduled_end", "scheduled_hours",
                      "actual_checkin", "actual_checkout", "actual_hours",
                      "status", "late_minutes", "early_minutes", "overtime_hours"},
    "checkins": {"emp_no", "name", "checkin_time", "checkout_time", "dept"},
    "monthly_reports": {"emp_id", "year_month", "scheduled_hours", "actual_hours",
                        "normal_days", "late_days", "early_days", "absent_days",
                        "leave_days", "timeoff_days", "overtime_hours", "owed_hours"},
    "workloads": {"account", "name", "emp_no", "team_desc", "date",
                  "metrics"},
    "training_records": {"emp_no", "record_date", "start_time", "end_time",
                         "duration_minutes", "type", "reason"},
}


def _build_schema_description(db) -> str:
    """通过 SQLAlchemy inspector 从数据库中获取实际表结构，生成紧凑描述。

    仅暴露与考勤报表相关的核心表和关键列，不暴露系统/配置表。
    """
    try:
        inspector = inspect(db.get_bind())
    except Exception:
        return ""

    lines = []
    # 额外关系提示
    rel_hints = {
        "employees": "PK=id; 员工主表",
        "schedules": "emp_id→employees.id; 排班表",
        "daily_reports": "emp_id→employees.id; 考勤日报",
        "checkins": "签到记录，通过 emp_no 关联 employees.emp_no",
        "monthly_reports": "emp_id→employees.id; 月度汇总",
        "workloads": "工作量数据，通过 emp_no 关联 employees.emp_no",
        "training_records": "培训记录，通过 emp_no 关联 employees.emp_no",
    }

    for table_name in inspector.get_table_names():
        if table_name in _SKIP_TABLES:
            continue
        columns = inspector.get_columns(table_name)
        if not columns:
            continue
        show = _SHOW_COLUMNS.get(table_name)
        if show is not None:
            col_names = [c["name"] for c in columns if c["name"] in show]
        else:
            col_names = [c["name"] for c in columns]
        if not col_names:
            continue
        hint = rel_hints.get(table_name, "")
        lines.append(f"{table_name}({', '.join(col_names)})" + (f"  -- {hint}" if hint else ""))

    return "\n".join(lines)


def run_sql(db, sql: str) -> dict:
    validated = validate_sql(sql)
    bind = db.get_bind()
    with bind.connect() as conn:
        result = conn.execute(text(validated))
        rows = _rows_to_dicts(result)
    truncated = len(rows) > MAX_RESULT_ROWS
    return {
        "columns": list(result.keys()),
        "rows": rows[:MAX_RESULT_ROWS],
        "row_count": len(rows),
        "truncated": truncated,
    }


def make_tools(db):
    """根据当前请求会话构建 LangChain 工具列表（闭包持有 db）。"""

    # 动态生成 schema 描述，写入 run_sql 工具的 docstring
    schema_desc = _build_schema_description(db)

    @tool("query_team_ranking")
    def query_team_ranking(year_month: str) -> str:
        """按月份查询各班组出勤率/工时/迟到缺勤排名。year_month 形如 '2026-07'。"""
        return _cap(json.dumps(report_queries.team_ranking(db, year_month), ensure_ascii=False))

    @tool("query_month_summary")
    def query_month_summary(
        year_month: str,
        team: str = None,
        dept: str = None,
        name: str = None,
        emp_no: str = None,
    ) -> str:
        """按月查询每个员工的工时/出勤/迟到/缺勤汇总。year_month 形如 '2026-07'。"""
        data = report_queries.month_summary(db, year_month, team, dept, name, emp_no)
        return _cap(json.dumps(data, ensure_ascii=False))

    @tool("query_date_range")
    def query_date_range(
        start_date: str, end_date: str, team: str = None, dept: str = None,
    ) -> str:
        """按日期区间（如 '2026-07-01' '2026-07-31'）汇总员工工时与出勤。"""
        data = report_queries.date_range_summary(db, start_date, end_date, team, dept)
        return _cap(json.dumps(data, ensure_ascii=False))

    @tool("query_daily")
    def query_daily(
        schedule_date: str,
        team: str = None, dept: str = None, status: str = None,
        name: str = None, emp_no: str = None,
    ) -> str:
        """查询指定日期的逐人考勤明细。schedule_date 形如 '2026-07-15'。"""
        data = report_queries.daily(db, schedule_date, team, dept, status, name, emp_no)
        return _cap(json.dumps(data, ensure_ascii=False))

    @tool("query_efficiency")
    def query_efficiency(
        year_month: str, team: str = None, dept: str = None,
    ) -> str:
        """查询员工月度效能（出勤率/工时效率/迟到缺勤天数）。year_month 形如 '2026-07'。"""
        data = report_queries.efficiency_summary(db, year_month, team, dept)
        return _cap(json.dumps(data, ensure_ascii=False))

    @tool("query_dashboard_stats")
    def query_dashboard_stats(year_month: str = None) -> str:
        """查询月度整体仪表盘统计（总人数/出勤率/工时/迟到缺勤等）。year_month 形如 '2026-07'，留空取当月。"""
        data = report_queries.dashboard_stats(db, year_month)
        return _cap(json.dumps(data, ensure_ascii=False))

    run_sql_tool = tool("run_sql")(_make_run_sql(db, schema_desc))

    return [
        query_team_ranking,
        query_month_summary,
        query_date_range,
        query_daily,
        query_efficiency,
        query_dashboard_stats,
        run_sql_tool,
    ]


def _make_run_sql(db, schema_desc: str):
    """构建 run_sql 工具函数（闭包持有 db + schema 描述）。"""
    # 动态 docstring：包含实际表结构，LLM 能直接看到表名和列名
    doc = (
        "对考勤数据库执行只读 SQL（仅 SELECT）。当现有报表工具无法覆盖自定义分析时使用。\n"
        "注意：仅允许单条 SELECT，禁止 INSERT/UPDATE/DELETE/DROP/WITH/INTO。\n"
        "以下是数据库中实际存在的表和关键列（PostgreSQL 语法）：\n"
        f"{schema_desc}"
    )

    def run_sql_tool(sql_query: str) -> str:
        try:
            result = run_sql(db, sql_query)
            return _cap(json.dumps(result, ensure_ascii=False))
        except ValueError as e:
            return json.dumps(
                {"error": f"SQL 校验失败: {e}", "hint": "请检查 SQL 语法，仅允许单条 SELECT，不支持 WITH/INTO 子句。"},
                ensure_ascii=False,
            )
        except Exception as e:
            return json.dumps(
                {"error": f"SQL 执行失败: {e}",
                 "hint": f"可能原因：表名或列名不正确。请参考工具说明中的表结构。\n可用表: {schema_desc}"},
                ensure_ascii=False,
            )

    run_sql_tool.__doc__ = doc
    return run_sql_tool
