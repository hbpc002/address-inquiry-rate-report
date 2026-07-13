import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.salary_config import DEFAULT_CONFIGS


def test_default_configs_contains_metric_targets():
    assert "metric_targets" in DEFAULT_CONFIGS
    targets = DEFAULT_CONFIGS["metric_targets"]["targets"]
    assert isinstance(targets, list)
    assert len(targets) > 0


def test_metric_targets_structure():
    targets = DEFAULT_CONFIGS["metric_targets"]["targets"]
    for t in targets:
        assert "field" in t
        assert "label" in t
        assert "operator" in t
        assert "value" in t
        assert "color" in t
        assert "enabled" in t
        assert t["operator"] in ("lt", "le", "gt", "ge")
        assert isinstance(t["enabled"], bool)


def test_metric_targets_satisfaction_rate():
    targets = DEFAULT_CONFIGS["metric_targets"]["targets"]
    sat_target = next((t for t in targets if t["field"] == "人工服务-满意度-满意率"), None)
    assert sat_target is not None
    assert sat_target["label"] == "满意率"
    assert sat_target["operator"] == "lt"
    assert sat_target["value"] == 0.95
    assert sat_target["enabled"] is True


def test_metric_targets_ti_dan_lv():
    targets = DEFAULT_CONFIGS["metric_targets"]["targets"]
    td_target = next((t for t in targets if t["field"] == "_ti_dan_lv"), None)
    assert td_target is not None
    assert td_target["label"] == "提单率"
    assert td_target["operator"] == "gt"
    assert td_target["value"] == 0.15
    assert td_target["enabled"] is True


def test_all_default_configs_have_required_keys():
    required_keys = {
        "call_salary_tiers", "sat_salary", "call_gap_targets",
        "sat_diff", "metric_targets"
    }
    for key in required_keys:
        assert key in DEFAULT_CONFIGS, f"Missing key: {key}"
