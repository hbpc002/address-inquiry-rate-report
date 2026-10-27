"""智能体运行配置：系统提示词、快捷建议、运行参数的默认值与读取。"""
import json

from sqlalchemy.orm import Session

from app.agent.graph import (
    SYSTEM_PROMPT,
    MAX_ITERATIONS,
    MAX_HISTORY_MESSAGES,
    CONSECUTIVE_RUN_SQL_FAILURES,
)

SETTINGS_KEY = "agent_settings"

# 旧版默认提示词：仅用于识别“从未自定义过提示词”的历史配置。
# 命中时自动升级到新版默认提示词；用户自定义提示词不会被覆盖。
LEGACY_SYSTEM_PROMPTS = frozenset({
    (
        "你是一个企业「排班签到报表系统」的数据分析智能体，用中文回答用户关于考勤、工时、出勤率、排班的问题。\n"
        "当前日期：{current_date}，涉及日期范围时请据此计算。\n"
        "{data_range}\n"
        "\n"
        "# 能力与工具优先级\n"
        "- **必须优先**使用提供的报表工具获取结构化数据：\n"
        "  · query_team_ranking(year_month) — 按月查班组排名\n"
        "  · query_month_summary(year_month, ...) — 按月查个人汇总\n"
        "  · query_date_range(start_date, end_date, ...) — 按日期区间汇总（如'最近一周'用此工具）\n"
        "  · query_daily(schedule_date, ...) — 查某日明细\n"
        "  · query_efficiency(year_month, ...) — 月度效能\n"
        "  · query_dashboard_stats(year_month) — 仪表盘统计\n"
        "- **仅当**以上工具确实无法满足需求时，才使用 run_sql 执行自定义查询。\n"
        "- 先理解用户意图，必要时调用工具，再基于真实返回的数据给出结论，不要编造数字。\n"
        "\n"
        "# 输出规范\n"
        "- 回答简洁、面向管理决策，关键数字用中文呈现。\n"
        "- 当查询结果适合用图表展示（如排名、趋势、对比）时，在回答末尾附加一个 ```chart-json 代码块，内容为 ECharts 的 option JSON（需包含 title、xAxis、yAxis、series 中适用的字段）。例如：\n"
        "```chart-json\n"
        '{{"title":{{"text":"各班组实际工时"}},"tooltip":{{}},"xAxis":{{"type":"category","data":["甲班","乙班"]}},"yAxis":{{"type":"value"}},"series":[{{"type":"bar","data":[120,98]}}]}}\n'
        "```\n"
        "- 若无需图表则不输出该代码块。\n"
    ),
})

DEFAULT_SETTINGS = {
    "system_prompt": SYSTEM_PROMPT,
    "suggestions": [
        "2026-07 各班组出勤率排名",
        "最近一周谁工时最低",
        "本月迟到次数最多的人",
        "2026-07 每天实际工时趋势",
    ],
    "max_iterations": MAX_ITERATIONS,
    "max_history_messages": MAX_HISTORY_MESSAGES,
    "consecutive_run_sql_failures": CONSECUTIVE_RUN_SQL_FAILURES,
}

# 运行参数合法范围（服务端校验）
PARAM_BOUNDS = {
    "max_iterations": (1, 20),
    "max_history_messages": (2, 100),
    "consecutive_run_sql_failures": (1, 10),
}


def merge_settings(stored) -> dict:
    """把已存配置合并到默认值，并自动升级旧版默认提示词。"""
    merged = dict(DEFAULT_SETTINGS)
    if not isinstance(stored, dict):
        return merged
    for k, v in stored.items():
        if k not in DEFAULT_SETTINGS or v is None:
            continue
        if k == "system_prompt":
            if not str(v).strip():
                continue
            if str(v) in LEGACY_SYSTEM_PROMPTS:
                continue
        if k == "suggestions" and not isinstance(v, list):
            continue
        merged[k] = v
    return merged


def get_settings(db: Session) -> dict:
    """读取已存配置并与默认值合并；db 为 None 时直接返回默认值。"""
    from app.models.app_config import AppConfig

    if db is None:
        return dict(DEFAULT_SETTINGS)
    try:
        rec = db.query(AppConfig).filter(AppConfig.key == SETTINGS_KEY).first()
        if rec and rec.value:
            return merge_settings(json.loads(rec.value))
    except Exception:
        pass
    return dict(DEFAULT_SETTINGS)


def validate_settings(patch: dict) -> dict:
    """校验并规范化部分更新；非法参数抛 ValueError。"""
    cleaned = {}
    if "system_prompt" in patch:
        prompt = patch["system_prompt"]
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("系统提示词不能为空")
        cleaned["system_prompt"] = prompt
    if "suggestions" in patch:
        sugg = patch["suggestions"]
        if not isinstance(sugg, list):
            raise ValueError("快捷问题建议必须是列表")
        cleaned["suggestions"] = [
            str(s).strip() for s in sugg if str(s).strip()
        ][:20]
    for key, (lo, hi) in PARAM_BOUNDS.items():
        if key in patch:
            val = patch[key]
            if not isinstance(val, int) or isinstance(val, bool):
                raise ValueError(f"{key} 必须是整数")
            if not (lo <= val <= hi):
                raise ValueError(f"{key} 取值范围为 {lo}-{hi}")
            cleaned[key] = val
    return cleaned
