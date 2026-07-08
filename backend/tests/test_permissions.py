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


def test_all_keys_contains_salary_config():
    keys = get_all_permission_keys()
    assert "salary_config.view" in keys


def test_all_keys_contains_workload():
    keys = get_all_permission_keys()
    assert "workload.view" in keys
    assert "workload.upload" in keys
    assert "workload.delete" in keys


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
