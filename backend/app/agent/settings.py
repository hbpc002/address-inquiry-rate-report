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

DEFAULT_SETTINGS = {
    "system_prompt": SYSTEM_PROMPT,
    "suggestions": [
        "2026-07 各班组出勤率排名",
        "最近一周谁工时最低",
        "导出 7 月考勤报表",
        "本月迟到次数最多的人",
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


def get_settings(db: Session) -> dict:
    """读取已存配置并与默认值合并；db 为 None 时直接返回默认值。"""
    from app.models.app_config import AppConfig

    merged = dict(DEFAULT_SETTINGS)
    if db is None:
        return merged
    try:
        rec = db.query(AppConfig).filter(AppConfig.key == SETTINGS_KEY).first()
        if rec and rec.value:
            stored = json.loads(rec.value)
            if isinstance(stored, dict):
                for k, v in stored.items():
                    if k in DEFAULT_SETTINGS and v is not None:
                        if k == "system_prompt" and not str(v).strip():
                            continue
                        if k == "suggestions" and not isinstance(v, list):
                            continue
                        merged[k] = v
    except Exception:
        pass
    return merged


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
