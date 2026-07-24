PERMISSION_REGISTRY = {
    "employees": {
        "label": "员工管理",
        "permissions": {
            "view": "查看",
            "create": "新增",
            "edit": "编辑",
            "delete": "删除",
            "restore": "恢复",
            "upload": "导入",
            "export": "导出",
        },
    },
    "schedules": {
        "label": "排班管理",
        "permissions": {
            "view": "查看",
            "create": "新增",
            "edit": "编辑",
            "delete": "删除",
            "upload": "导入",
        },
    },
    "checkins": {
        "label": "签到记录",
        "permissions": {
            "view": "查看",
            "delete": "删除",
            "upload": "导入",
        },
    },
    "checkin_report": {
        "label": "签入签出报表",
        "permissions": {
            "view": "查看",
            "export": "导出",
        },
    },
    "workload": {
        "label": "工作量详单",
        "permissions": {
            "view": "查看",
            "upload": "导入",
            "delete": "删除",
        },
    },
    "workload_report": {
        "label": "工作量报表",
        "permissions": {
            "view": "查看",
            "export": "导出",
            "screenshot": "截图导出",
            "view_call_salary": "查看接话绩效",
            "view_sat_salary": "查看满意度绩效",
            "view_total_salary": "查看合计绩效",
            "view_gap": "查看话务量差额",
            "view_sat_diff": "查看满意度差额",
        },
    },
    "reports": {
        "label": "考勤报表",
        "permissions": {
            "view": "查看",
            "recalculate": "重算考勤",
            "export": "导出报表",
            "dashboard_export": "仪表盘导出",
            "efficiency_export": "效能监控导出",
        },
    },
    "shift_types": {
        "label": "班次管理",
        "permissions": {
            "view": "查看",
            "create": "新增",
            "edit": "编辑",
            "delete": "删除",
        },
    },
    "work_hour_settings": {
        "label": "工时预警设置",
        "permissions": {
            "view": "查看",
            "create": "新增",
            "edit": "编辑",
            "delete": "删除",
        },
    },
    "system": {
        "label": "系统管理",
        "permissions": {
            "view": "查看",
            "clear_data": "清除数据",
            "changelogs": "管理更新日志",
            "export_logs": "导出日志",
        },
    },
    "users": {
        "label": "用户管理",
        "permissions": {
            "view": "查看",
            "manage": "管理用户",
        },
    },
    "roles": {
        "label": "角色管理",
        "permissions": {
            "view": "查看",
            "manage": "管理角色",
        },
    },
    "salary_config": {
        "label": "绩效配置",
        "permissions": {
            "view": "查看",
        },
    },
    "field_annotations": {
        "label": "字段批注",
        "permissions": {
            "view": "查看",
            "edit": "编辑",
        },
    },
}


def get_all_permission_keys():
    keys = []
    for page, info in PERMISSION_REGISTRY.items():
        for action in info["permissions"]:
            keys.append(f"{page}.{action}")
    return keys


def get_default_permissions(role_name: str) -> dict:
    all_keys = get_all_permission_keys()
    if role_name == "admin":
        return {k: True for k in all_keys}

    admin_only_views = {"system", "users", "roles"}
    admin_only_actions = {"clear_data", "manage"}

    defaults = {}
    for page, info in PERMISSION_REGISTRY.items():
        for action in info["permissions"]:
            key = f"{page}.{action}"
            if action == "view":
                defaults[key] = page not in admin_only_views
            elif action in admin_only_actions:
                defaults[key] = False
            else:
                defaults[key] = role_name == "manager"
    return defaults
