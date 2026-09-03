"""智能体工具集：复用报表查询逻辑 + 只读 text-to-SQL。"""
import json

from sqlalchemy import text
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

    @tool("run_sql")
    def run_sql_tool(sql_query: str) -> str:
        """对考勤数据库执行只读 SQL（仅 SELECT）。当现有报表工具无法覆盖自定义分析时使用。"""
        return _cap(json.dumps(run_sql(db, sql_query), ensure_ascii=False))

    return [
        query_team_ranking,
        query_month_summary,
        query_date_range,
        query_daily,
        query_efficiency,
        query_dashboard_stats,
        run_sql_tool,
    ]
