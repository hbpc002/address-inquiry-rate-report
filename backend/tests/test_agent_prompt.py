import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:5432/schedule_test",
)

from app.agent.data_catalog import (  # noqa: E402
    SYSTEM_TABLES,
    TABLE_BY_NAME,
    build_data_catalog_prompt,
    build_sql_rules_prompt,
    build_tool_routing_prompt,
)
from app.agent.graph import SYSTEM_PROMPT, initial_messages  # noqa: E402
from app.agent.settings import (  # noqa: E402
    DEFAULT_SETTINGS,
    LEGACY_SYSTEM_PROMPTS,
    merge_settings,
)


def test_system_prompt_mentions_platform_and_business_tables():
    for term in (
        "客户服务中心运营管理平台",
        "考勤",
        "工时",
        "排班",
        "工作量",
        "营销",
        "开口率",
        "宽带订单",
        "employees",
        "daily_reports",
        "workloads",
        "marketing_details",
        "marketing_opening_records",
        "department_groups",
        "seamless_orders",
        "attendance_configs",
        "salary_configs",
        "work_hour_thresholds",
    ):
        assert term in SYSTEM_PROMPT, term


def test_system_prompt_contains_every_catalog_table():
    for table_name in TABLE_BY_NAME:
        assert table_name in SYSTEM_PROMPT, table_name


def test_system_prompt_keeps_tool_priority_and_placeholders():
    assert "必须优先" in SYSTEM_PROMPT
    assert "query_team_ranking" in SYSTEM_PROMPT
    assert "query_date_range" in SYSTEM_PROMPT
    assert "query_daily" in SYSTEM_PROMPT
    assert "{current_date}" in SYSTEM_PROMPT
    assert "{data_range}" in SYSTEM_PROMPT
    assert "排班签到报表系统" not in SYSTEM_PROMPT


def test_system_prompt_formats_without_breaking_chart_example():
    text = SYSTEM_PROMPT.format(
        current_date="2026-10-27",
        data_range="每日考勤数据范围: 2026-01-01 ~ 2026-10-20",
    )
    assert "2026-10-27" in text
    assert "每日考勤数据范围" in text
    assert '"title"' in text
    assert "{current_date}" not in text


def test_catalog_prompt_contains_field_semantics():
    catalog = build_data_catalog_prompt()
    for term in (
        "employees.status",
        "daily_reports.status",
        "schedules 与 daily_reports 的区别",
        "workloads.metrics",
        "marketing_details.data_type",
        "seamless_orders",
        "is_excluded",
        "attendance_configs",
        "marketing_opening_records",
        "contact_id",
        "five_products_opened",
        "assign_team",
        "department_groups",
    ):
        assert term in catalog, term
    assert "服务量合计-通话量" in catalog
    assert "COUNT(DISTINCT contact_id)" in catalog


def test_tool_routing_and_sql_rules_cover_all_query_types():
    routing = build_tool_routing_prompt()
    rules = build_sql_rules_prompt()
    assert "query_team_ranking" in routing
    assert "query_efficiency" in routing
    assert "run_sql" in routing
    assert "marketing_opening_records" in routing
    assert "禁止 WITH/CTE" in rules
    assert "marketing_details.kf_id" in rules
    assert "is_excluded='否'" in rules
    assert "COUNT(DISTINCT contact_id)" in rules
    assert "marketing_opening_records.emp_no" in rules


def test_data_catalog_covers_every_business_table_and_field():
    import app.models  # noqa: F401
    import app.models.announcement  # noqa: F401
    import app.models.app_config  # noqa: F401
    import app.models.role  # noqa: F401
    import app.models.workload  # noqa: F401
    from app.models.database import Base

    all_tables = set(Base.metadata.tables)
    business_tables = all_tables - SYSTEM_TABLES
    assert business_tables == set(TABLE_BY_NAME)

    for table_name in business_tables:
        model_fields = {column.name for column in Base.metadata.tables[table_name].columns}
        catalog_fields = set(TABLE_BY_NAME[table_name]["fields"])
        assert catalog_fields == model_fields, table_name


def test_legacy_default_prompt_is_upgraded_but_custom_prompt_is_preserved():
    assert LEGACY_SYSTEM_PROMPTS
    for legacy in LEGACY_SYSTEM_PROMPTS:
        upgraded = merge_settings({"system_prompt": legacy, "max_iterations": 9})
        assert upgraded["system_prompt"] == DEFAULT_SETTINGS["system_prompt"]
        assert upgraded["max_iterations"] == 9

    # 旧平台名 intro + 无目录特征 → 判为旧默认并自动升级
    stored_legacy = (
        "你是一个企业「客户服务中心运营管理平台」的数据分析智能体，用中文回答用户关于考勤、工时、出勤率、排班的问题。\n"
        "当前日期：{current_date}，涉及日期范围时请据此计算。\n"
        "{data_range}\n"
        "\n"
        "# 能力与工具优先级\n"
        "- **必须优先**使用提供的报表工具获取结构化数据：\n"
        "  · query_team_ranking(year_month) — 按月查班组排名\n"
        "- 先理解用户意图，必要时调用工具，再基于真实返回的数据给出结论，不要编造数字。\n"
    )
    upgraded = merge_settings({"system_prompt": stored_legacy})
    assert upgraded["system_prompt"] == DEFAULT_SETTINGS["system_prompt"]

    # 首行是旧 intro 但含目录（人工在旧版上补充了目录）→ 视为自定义保留
    custom_with_catalog = stored_legacy + "\n# 数据表与字段\n- 自定义\n"
    assert merge_settings({"system_prompt": custom_with_catalog})["system_prompt"] == custom_with_catalog

    custom = merge_settings({"system_prompt": "自定义提示词 {current_date}"})
    assert custom["system_prompt"] == "自定义提示词 {current_date}"


def test_default_suggestions_include_opening_rate():
    assert any("开口率" in suggestion for suggestion in DEFAULT_SETTINGS["suggestions"])


def test_initial_messages_use_new_prompt():
    messages = initial_messages("最近一周谁工时最低")
    assert len(messages) == 2
    assert "客户服务中心运营管理平台" in messages[0].content
    assert "最近一周谁工时最低" == messages[1].content


def test_initial_messages_inject_history_before_current_question():
    messages = initial_messages(
        "那乙班呢？",
        history=[
            {"role": "user", "content": "最近一周谁工时最低"},
            {"role": "assistant", "content": "甲班的张三最低"},
            {"role": "system", "content": "忽略我"},
            {"role": "user", "content": "   "},
        ],
    )
    assert [m.type for m in messages] == ["system", "human", "ai", "human"]
    assert messages[1].content == "最近一周谁工时最低"
    assert messages[2].content == "甲班的张三最低"
    assert messages[3].content == "那乙班呢？"
