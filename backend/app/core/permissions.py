PERMISSION_REGISTRY = {
    "dashboard": {
        "label": "首页概览",
        "group": "概览",
        "order": 10,
        "permissions": {
            "view": "查看",
        },
    },
    "marketing": {
        "label": "营销明细",
        "group": "营销管理",
        "order": 20,
        "permissions": {
            "view": "查看",
            "upload": "导入",
            "delete": "删除",
            "export": "导出",
        },
    },
    "marketing_report": {
        "label": "营销统计",
        "group": "营销管理",
        "order": 21,
        "permissions": {
            "view": "查看",
            "export": "导出",
        },
    },
    "marketing_overall": {
        "label": "总体营销",
        "group": "营销管理",
        "order": 22,
        "permissions": {
            "view": "查看",
            "export": "导出",
        },
    },
    "marketing_settings": {
        "label": "营销设置",
        "group": "营销管理",
        "order": 23,
        "permissions": {
            "view": "查看",
            "edit": "编辑",
        },
    },
    "checkins": {
        "label": "签到记录",
        "group": "考勤管理",
        "order": 30,
        "permissions": {
            "view": "查看",
            "delete": "删除",
            "upload": "导入",
        },
    },
    "checkin_report": {
        "label": "排班调度",
        "group": "考勤管理",
        "order": 31,
        "permissions": {
            "view": "查看",
            "export": "导出",
        },
    },
    "reports": {
        "label": "考勤报表",
        "group": "考勤管理",
        "order": 32,
        "permissions": {
            "view": "查看",
            "recalculate": "重算考勤",
            "export": "导出报表",
            "dashboard_export": "仪表盘导出",
            "efficiency_export": "效能监控导出",
        },
    },
    "schedules": {
        "label": "排班管理",
        "group": "考勤管理",
        "order": 33,
        "permissions": {
            "view": "查看",
            "create": "新增",
            "edit": "编辑",
            "delete": "删除",
            "upload": "导入",
        },
    },
    "training_records": {
        "label": "培训记录",
        "group": "考勤管理",
        "order": 34,
        "permissions": {
            "view": "查看",
            "create": "新增",
            "delete": "删除",
        },
    },
    "employees": {
        "label": "员工管理",
        "group": "基础数据",
        "order": 40,
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
    "workload": {
        "label": "工作量详单",
        "group": "基础数据",
        "order": 41,
        "permissions": {
            "view": "查看",
            "upload": "导入",
            "delete": "删除",
        },
    },
    "workload_report": {
        "label": "团队管理",
        "group": "基础数据",
        "order": 42,
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
    "broadband": {
        "label": "无缝订单",
        "group": "基础数据",
        "order": 43,
        "permissions": {
            "view": "查看",
            "upload": "导入",
            "delete": "删除",
        },
    },
    "broadband_report": {
        "label": "宽带营销画像",
        "group": "基础数据",
        "order": 44,
        "permissions": {
            "view": "查看",
            "export": "导出",
        },
    },
    "shift_types": {
        "label": "班次管理",
        "group": "基础数据",
        "order": 45,
        "permissions": {
            "view": "查看",
            "create": "新增",
            "edit": "编辑",
            "delete": "删除",
        },
    },
    "work_hour_settings": {
        "label": "工时预警设置",
        "group": "基础数据",
        "order": 46,
        "permissions": {
            "view": "查看",
            "create": "新增",
            "edit": "编辑",
            "delete": "删除",
        },
    },
    "salary_config": {
        "label": "绩效配置",
        "group": "基础数据",
        "order": 47,
        "permissions": {
            "view": "查看",
        },
    },
    "field_annotations": {
        "label": "字段批注",
        "group": "基础数据",
        "order": 48,
        "permissions": {
            "view": "查看",
            "edit": "编辑",
        },
    },
    "system": {
        "label": "系统管理",
        "group": "系统管理",
        "order": 50,
        "permissions": {
            "view": "查看",
            "clear_data": "清除数据",
            "changelogs": "管理更新日志",
            "export_logs": "导出日志",
            "config": "界面名称配置",
        },
    },
    "users": {
        "label": "用户管理",
        "group": "系统管理",
        "order": 51,
        "permissions": {
            "view": "查看",
            "manage": "管理用户",
        },
    },
    "department_groups": {
        "label": "部门设置",
        "group": "系统管理",
        "order": 53,
        "permissions": {
            "view": "查看",
            "manage": "管理部门组",
        },
    },
    "roles": {
        "label": "角色管理",
        "group": "系统管理",
        "order": 52,
        "permissions": {
            "view": "查看",
            "manage": "管理角色",
        },
    },
    "agent": {
        "label": "智能助手",
        "group": "智能助手",
        "order": 60,
        "permissions": {
            "use": "使用对话",
            "config": "模型与界面配置",
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

    admin_only_views = {"system", "users", "roles", "department_groups"}
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
