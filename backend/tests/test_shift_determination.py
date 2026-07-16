"""测试 determine_shift_name 班次判断逻辑（按排班字段优先，首签时间兜底）"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.checkins import determine_shift_name


class FakeSchedule:
    def __init__(self, shift_name):
        self.shift_name = shift_name


def test_schedule_night():
    """含'晚'的班次名称 → 晚班"""
    assert determine_shift_name(FakeSchedule("晚二8.5"), "2026-07-15 08:00") == "晚班"
    assert determine_shift_name(FakeSchedule("中晚（8.5HH）"), "2026-07-15 10:00") == "晚班"
    assert determine_shift_name(FakeSchedule("中晚（9.0HH）"), "2026-07-15 12:00") == "晚班"
    assert determine_shift_name(FakeSchedule("晚班"), "2026-07-15 08:00") == "晚班"
    assert determine_shift_name(FakeSchedule("大晚班"), "2026-07-15 08:00") == "晚班"


def test_schedule_admin():
    """含'行政'的班次名称 → 早班"""
    assert determine_shift_name(FakeSchedule("行政9.0H"), "2026-07-15 10:00") == "早班"
    assert determine_shift_name(FakeSchedule("行政班"), "2026-07-15 14:00") == "早班"


def test_schedule_morning():
    """含'早'的班次名称 → 早班"""
    assert determine_shift_name(FakeSchedule("早班"), "2026-07-15 14:00") == "早班"
    assert determine_shift_name(FakeSchedule("早班(08:00-16:00)"), "2026-07-15 15:00") == "早班"


def test_schedule_mid():
    """含'中'的班次名称 → 中班"""
    assert determine_shift_name(FakeSchedule("中班（9.0H）"), "2026-07-15 06:00") == "中班"
    assert determine_shift_name(FakeSchedule("中班9小时"), "2026-07-15 18:00") == "中班"
    assert determine_shift_name(FakeSchedule("中班"), "2026-07-15 20:00") == "中班"


def test_schedule_priority_order():
    """'晚'的优先级高于'中'（如 中晚）→ 晚班"""
    assert determine_shift_name(FakeSchedule("中晚（8.5HH）"), "2026-07-15 08:00") == "晚班"


def test_no_schedule_fallback_before_10():
    """无排班时，首签时间 < 10:00 → 早班"""
    assert determine_shift_name(None, "2026-07-15 08:05") == "早班"
    assert determine_shift_name(None, "2026-07-15 06:30") == "早班"
    assert determine_shift_name(None, "2026-07-15 09:59") == "早班"


def test_no_schedule_fallback_10_to_15():
    """无排班时，首签时间 10:00~14:59 → 中班"""
    assert determine_shift_name(None, "2026-07-15 10:00") == "中班"
    assert determine_shift_name(None, "2026-07-15 12:30") == "中班"
    assert determine_shift_name(None, "2026-07-15 14:59") == "中班"


def test_no_schedule_fallback_15_plus():
    """无排班时，首签时间 >= 15:00 → 晚班"""
    assert determine_shift_name(None, "2026-07-15 15:00") == "晚班"
    assert determine_shift_name(None, "2026-07-15 20:00") == "晚班"
    assert determine_shift_name(None, "2026-07-15 23:59") == "晚班"


def test_schedule_unknown_name_fallback():
    """排班名称不含早/中/晚/行政时，按首签时间兜底"""
    assert determine_shift_name(FakeSchedule("值班"), "2026-07-15 08:00") == "早班"
    assert determine_shift_name(FakeSchedule("培训"), "2026-07-15 12:00") == "中班"
    assert determine_shift_name(FakeSchedule("会议"), "2026-07-15 16:00") == "晚班"


def test_schedule_empty_shift_name():
    """排班存在但 shift_name 为空 → 按首签时间"""
    s = FakeSchedule("")
    assert determine_shift_name(s, "2026-07-15 08:00") == "早班"


def test_schedule_none_shift_name():
    """排班存在但 shift_name 为 None → 按首签时间"""
    s = FakeSchedule(None)
    assert determine_shift_name(s, "2026-07-15 14:00") == "中班"
