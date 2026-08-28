import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.permissions import (
    PERMISSION_REGISTRY,
    get_all_permission_keys,
    get_default_permissions,
)


def test_registry_contains_salary_config():
    assert "salary_config" in PERMISSION_REGISTRY
    assert PERMISSION_REGISTRY["salary_config"]["label"] == "绩效配置"
    assert "view" in PERMISSION_REGISTRY["salary_config"]["permissions"]


def test_registry_contains_workload():
    assert "workload" in PERMISSION_REGISTRY
    assert PERMISSION_REGISTRY["workload"]["label"] == "工作量详单"


def test_registry_contains_workload_report():
    assert "workload_report" in PERMISSION_REGISTRY
    assert PERMISSION_REGISTRY["workload_report"]["label"] == "工作量报表"
    assert "view_call_salary" in PERMISSION_REGISTRY["workload_report"]["permissions"]
    assert "view_sat_salary" in PERMISSION_REGISTRY["workload_report"]["permissions"]
    assert "view_total_salary" in PERMISSION_REGISTRY["workload_report"]["permissions"]
    assert "view_gap" in PERMISSION_REGISTRY["workload_report"]["permissions"]
    assert "view_sat_diff" in PERMISSION_REGISTRY["workload_report"]["permissions"]


def test_registry_contains_agent():
    assert "agent" in PERMISSION_REGISTRY
    assert PERMISSION_REGISTRY["agent"]["label"] == "智能体"
    assert "use" in PERMISSION_REGISTRY["agent"]["permissions"]
    assert "config" in PERMISSION_REGISTRY["agent"]["permissions"]


def test_all_keys_contains_salary_config():
    keys = get_all_permission_keys()
    assert "salary_config.view" in keys


def test_all_keys_contains_workload():
    keys = get_all_permission_keys()
    assert "workload.view" in keys
    assert "workload.upload" in keys
    assert "workload.delete" in keys


def test_all_keys_contains_new_permissions():
    keys = get_all_permission_keys()
    assert "reports.recalculate" in keys
    assert "reports.export" in keys
    assert "employees.export" in keys
    assert "system.export_logs" in keys
    assert "reports.dashboard_export" in keys
    assert "reports.efficiency_export" in keys
    assert "checkin_report.export" in keys
    assert "workload_report.export" in keys
    assert "workload_report.view_call_salary" in keys
    assert "workload_report.view_sat_salary" in keys
    assert "workload_report.view_total_salary" in keys
    assert "workload_report.view_gap" in keys
    assert "workload_report.view_sat_diff" in keys
    assert "agent.use" in keys
    assert "agent.config" in keys


def test_all_keys_count():
    keys = get_all_permission_keys()
    expected = 0
    for info in PERMISSION_REGISTRY.values():
        expected += len(info["permissions"])
    assert len(keys) == expected


def test_default_permissions_admin():
    perms = get_default_permissions("admin")
    assert perms["salary_config.view"] is True
    assert perms["workload.view"] is True
    assert perms["workload_report.view"] is True


def test_default_permissions_manager():
    perms = get_default_permissions("manager")
    assert perms["salary_config.view"] is True
    assert perms["workload.view"] is True
    assert perms["workload_report.view"] is True


def test_default_permissions_user():
    perms = get_default_permissions("user")
    assert perms["salary_config.view"] is True
    assert perms["workload.view"] is True
    assert perms["workload_report.view"] is True


def test_default_permissions_new_keys_admin():
    perms = get_default_permissions("admin")
    assert perms["reports.recalculate"] is True
    assert perms["reports.export"] is True
    assert perms["employees.export"] is True
    assert perms["system.export_logs"] is True
    assert perms["reports.dashboard_export"] is True
    assert perms["reports.efficiency_export"] is True
    assert perms["checkin_report.export"] is True
    assert perms["workload_report.export"] is True
    assert perms["workload_report.view_call_salary"] is True
    assert perms["workload_report.view_sat_salary"] is True
    assert perms["workload_report.view_total_salary"] is True
    assert perms["workload_report.view_gap"] is True
    assert perms["workload_report.view_sat_diff"] is True


def test_default_permissions_new_keys_manager():
    perms = get_default_permissions("manager")
    assert perms["reports.recalculate"] is True
    assert perms["reports.export"] is True
    assert perms["employees.export"] is True
    assert perms["reports.dashboard_export"] is True
    assert perms["reports.efficiency_export"] is True
    assert perms["checkin_report.export"] is True
    assert perms["workload_report.export"] is True
    assert perms["workload_report.view_call_salary"] is True
    assert perms["workload_report.view_sat_salary"] is True
    assert perms["workload_report.view_total_salary"] is True
    assert perms["workload_report.view_gap"] is True
    assert perms["workload_report.view_sat_diff"] is True
    assert perms["agent.use"] is True
    assert perms["agent.config"] is True


def test_default_permissions_new_keys_user():
    perms = get_default_permissions("user")
    assert perms["reports.recalculate"] is False
    assert perms["reports.export"] is False
    assert perms["employees.export"] is False
    assert perms["reports.dashboard_export"] is False
    assert perms["reports.efficiency_export"] is False
    assert perms["checkin_report.export"] is False
    assert perms["workload_report.export"] is False
    assert perms["workload_report.view_call_salary"] is False
    assert perms["workload_report.view_sat_salary"] is False
    assert perms["workload_report.view_total_salary"] is False
    assert perms["workload_report.view_gap"] is False
    assert perms["workload_report.view_sat_diff"] is False
    assert perms["agent.use"] is False
    assert perms["agent.config"] is False
