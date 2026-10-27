"""智能体数据目录：业务表、字段、口径、查询路由与 SQL 规则。"""

SYSTEM_TABLES = frozenset({
    "users",
    "roles",
    "llm_providers",
    "llm_provider_models",
    "app_configs",
    "operation_logs",
})

TABLE_CATALOG = [
    {
        "name": "employees",
        "label": "员工主表",
        "fields": [
            "id", "emp_no", "name", "team", "dept", "role", "status",
            "hire_date", "deleted_at", "created_by", "created_at", "updated_at",
        ],
        "purpose": "员工工号、姓名、班组、部门、岗位、在职状态、入职日期。",
        "notes": "主键 id；默认过滤 status='在职' AND deleted_at IS NULL；role 常见值：组长、师傅、组员。",
        "scenarios": "人员筛选、班组/部门归属、与考勤/排班/工作量/营销/宽带表联表。",
    },
    {
        "name": "shift_types",
        "label": "班次类型",
        "fields": [
            "id", "shift_name", "time_segments", "work_hours", "color",
            "is_night", "is_active", "created_at",
        ],
        "purpose": "班次定义、时间段、额定工时、是否夜班。",
        "notes": "time_segments 为 JSON 数组；work_hours 单位为小时。",
        "scenarios": "班次规则、夜班定义、排班工时来源。",
    },
    {
        "name": "schedules",
        "label": "排班表",
        "fields": [
            "id", "emp_id", "schedule_date", "shift_type_id", "shift_name",
            "time_segments", "work_hours", "is_night", "schedule_type",
            "original_shift_id", "notes", "punctuality_rate", "call_duration",
            "organize_duration", "utilization_rate", "attendance_rate",
            "created_by", "created_at", "updated_at",
        ],
        "purpose": "员工每日计划排班、班次、计划工时和排班扩展指标。",
        "notes": "emp_id→employees.id；schedule_type 常见值：正常、请假、休息、加班；比率为 0-1 小数。",
        "scenarios": "排班查询、夜班统计、计划工时、班次分布、遵时率/利用率。",
    },
    {
        "name": "checkins",
        "label": "原始签到记录",
        "fields": [
            "id", "emp_no", "name", "checkin_time", "checkout_time",
            "device_no", "dept", "import_batch", "created_at",
        ],
        "purpose": "员工原始签入/签出打卡记录。",
        "notes": "通过 emp_no 关联 employees.emp_no；checkin_time/checkout_time 为时间戳；同一人同日可能多条。",
        "scenarios": "原始打卡、签入签出时间、设备号、导入批次核对。",
    },
    {
        "name": "daily_reports",
        "label": "考勤日报",
        "fields": [
            "id", "emp_id", "schedule_date", "shift_type_id", "schedule_type",
            "scheduled_start", "scheduled_end", "scheduled_hours",
            "actual_checkin", "actual_checkout", "actual_hours", "status",
            "late_minutes", "early_minutes", "overtime_hours",
            "segment_details", "calculated_at",
        ],
        "purpose": "员工每日实际考勤结果、状态、实际工时、迟到/早退/加班。",
        "notes": "emp_id→employees.id；status 取值为 正常/迟到/早退/缺勤/请假/休息；工时单位为小时。",
        "scenarios": "每日考勤、迟到/早退/缺勤名单、实际工时、加班、月度/区间汇总的底表。",
    },
    {
        "name": "monthly_reports",
        "label": "月度汇总（预计算）",
        "fields": [
            "id", "emp_id", "year_month", "scheduled_hours", "actual_hours",
            "normal_days", "late_days", "early_days", "absent_days",
            "leave_days", "timeoff_days", "overtime_hours", "owed_hours",
            "calculated_at",
        ],
        "purpose": "员工月度工时与考勤天数预汇总。",
        "notes": "emp_id→employees.id；year_month 格式 YYYY-MM；现有报表工具未使用该表，优先用工具从 daily_reports 实时计算，直接查此表时需说明口径。",
        "scenarios": "历史月度汇总、欠时工时、月度天数核对。",
    },
    {
        "name": "workloads",
        "label": "工作量统计",
        "fields": [
            "id", "date", "province", "account", "name", "emp_no",
            "team_desc", "metrics", "import_batch", "created_at",
        ],
        "purpose": "客服每日工作量：通话、工单、工时利用率、满意度、示忙/休息等。",
        "notes": "emp_no→employees.emp_no；metrics 为 JSONB，指标键含中文；工时利用率是 0-1 小数，时长类指标单位为秒。",
        "scenarios": "话务量、工单量、人工呼出量、工时利用率、满意度、示忙/休息、接话小时量。",
    },
    {
        "name": "training_records",
        "label": "培训记录",
        "fields": [
            "id", "emp_no", "record_date", "start_time", "end_time",
            "duration_minutes", "type", "reason", "created_by",
            "created_at", "updated_at",
        ],
        "purpose": "员工培训/请假等扣减记录。",
        "notes": "emp_no→employees.emp_no；start_time/end_time 为 HH:MM 字符串；duration_minutes 单位为分钟；type 常见值：培训、请假。",
        "scenarios": "培训时长、培训扣除、遵时率重算、请假记录。",
    },
    {
        "name": "marketing_details",
        "label": "营销明细",
        "fields": [
            "id", "kf_id", "org_name", "organization", "tenant",
            "work_order_id", "data_type", "pos_sequence",
            "develop_depart_name", "develop_depart_id", "develop_staff_name",
            "develop_staff_id", "tb_region_name", "channel", "area_name",
            "net_type", "trade_id", "finish_date", "service_type",
            "package_type", "valid_type", "product_id", "product_name",
            "lh_qh", "is_zero", "import_batch", "created_at",
        ],
        "purpose": "线上直办/营销工单明细，含客服工号、组织、渠道、地市、产品、重点业务。",
        "notes": "kf_id→employees.emp_no；data_type 取值 xszb（线上直办）/fwgd（办理工单）；finish_date 为竣工日期；is_zero 为 0元/非0元。",
        "scenarios": "营销量、重点业务、产品、渠道、地市、线上直办/办理工单对比。",
    },
    {
        "name": "seamless_orders",
        "label": "宽带无缝订单",
        "fields": [
            "id", "order_no", "emp_no", "order_date", "is_completed",
            "city", "is_hour_short", "is_excluded", "is_duplicate",
            "cb_order_no", "cb_business_no", "cb_order_status",
            "product_name", "bandwidth_speed", "order_status", "month",
            "intention_emp_no", "import_batch", "created_at",
        ],
        "purpose": "宽带无缝订单明细，含竣工、1小时短单、剔除、重复单、意向单受理人。",
        "notes": "emp_no→employees.emp_no；is_completed/is_hour_short/is_excluded/is_duplicate 取值为 是/否；统计默认过滤 is_excluded='否' AND is_duplicate='否'。",
        "scenarios": "宽带订单量、竣工量、短单、剔除/重复分析、地市/产品/速率、意向单转化。",
    },
    {
        "name": "attendance_configs",
        "label": "考勤配置",
        "fields": ["id", "key", "value", "created_at", "updated_at"],
        "purpose": "考勤阈值配置。",
        "notes": "key/value 键值对；常见 key：late_threshold_minutes、early_leave_threshold_minutes、long_hour_threshold。",
        "scenarios": "迟到/早退/超长工时判定口径。",
    },
    {
        "name": "salary_configs",
        "label": "绩效配置",
        "fields": ["id", "rule_key", "rule_data", "updated_at"],
        "purpose": "绩效规则配置。",
        "notes": "rule_data 为 JSON 字符串；常见 rule_key：call_salary_tiers、sat_salary、sat_diff、call_gap_targets、metric_targets、points_formula。",
        "scenarios": "接话绩效、满意度绩效、提单率目标、宽带积分规则。",
    },
    {
        "name": "work_hour_thresholds",
        "label": "工时预警阈值",
        "fields": [
            "id", "team", "overtime_ratio", "undertime_ratio",
            "created_by", "created_at", "updated_at",
        ],
        "purpose": "按班组配置超长/过短工时阈值。",
        "notes": "overtime_ratio/undertime_ratio 为相对排班工时的倍数，默认 1.2/0.8。",
        "scenarios": "超长工时、过短工时、工时预警。",
    },
    {
        "name": "announcements",
        "label": "平台公告",
        "fields": [
            "id", "type", "title", "content", "is_active",
            "created_by", "created_at", "updated_at",
        ],
        "purpose": "平台公告与更新日志。",
        "notes": "is_active 为是否启用；type 常见值：公告。",
        "scenarios": "平台公告、更新日志。",
    },
    {
        "name": "field_annotations",
        "label": "字段批注",
        "fields": [
            "id", "report_type", "field_path", "field_label", "source",
            "formula", "description", "sort_order", "created_at", "updated_at",
        ],
        "purpose": "报表字段的业务含义、来源与计算公式说明。",
        "notes": "report_type 区分 daily/monthly/workload/checkin/efficiency/ranking 等。",
        "scenarios": "解释字段口径、公式、数据来源。",
    },
]

TABLE_BY_NAME = {item["name"]: item for item in TABLE_CATALOG}
TABLE_COLUMNS = {item["name"]: set(item["fields"]) for item in TABLE_CATALOG}
TABLE_NOTES = {item["name"]: item.get("notes", "") for item in TABLE_CATALOG}
TABLE_LABELS = {item["name"]: item["label"] for item in TABLE_CATALOG}

WORKLOAD_METRIC_KEYS = [
    "总体-工作总时长(秒)",
    "总体-工时利用率",
    "呼入人工服务-人工服务-通话次数",
    "呼入人工服务-人工服务-通话总时长(秒)",
    "呼入人工服务-工单-生成总量",
    "呼出服务-人工呼出呼叫量",
    "服务量合计-通话量",
    "服务量合计-服务后整理总时长(秒)",
    "人工服务-满意度-满意率",
    "呼入人工服务-解决率-解决率",
]

FIELD_NOTES = [
    "employees.status：在职/离职；默认只统计在职员工，历史排名需结合 hire_date/deleted_at。",
    "daily_reports.status：正常/迟到/早退/缺勤/请假/休息；迟到/早退分钟在 late_minutes/early_minutes。",
    "schedules 与 daily_reports 的区别：schedules 是计划排班，daily_reports 是实际考勤结果。",
    "schedules 的 punctuality_rate/attendance_rate/utilization_rate 为 0-1 小数；query_efficiency 返回的 attendance_rate/efficiency_rate 为 0-100 百分数。",
    "query_team_ranking 返回的 avg_attendance 为 0-1 小数，展示时乘 100 转百分比。",
    "monthly_reports 是预汇总表；报表工具从 daily_reports 实时计算，二者口径可能不同。",
    "workloads.metrics 是 JSONB；用 metrics->>'指标名' 取值，数值可能为字符串，聚合前先 ::numeric。",
    "workloads 的时长指标单位为秒，工时利用率/满意率为 0-1 小数；展示时按需换算。",
    "marketing_details.data_type：xszb=线上直办，fwgd=办理工单；kf_id 关联 employees.emp_no。",
    "seamless_orders 的 is_completed/is_hour_short/is_excluded/is_duplicate 取值为 是/否；默认排除 is_excluded='否' AND is_duplicate='否'。",
    "attendance_configs 是 key/value 配置；salary_configs.rule_data 是 JSON 字符串；work_hour_thresholds 是班组级倍数阈值。",
]

TOOL_ROUTING = [
    ("班组排名、月度班组对比", "query_team_ranking(year_month)"),
    ("个人月度汇总、按团队/部门/姓名/工号筛选", "query_month_summary(year_month, ...)"),
    ("最近一周、上月、任意日期区间", "query_date_range(start_date, end_date, ...)"),
    ("单日明细、迟到名单、某人某天", "query_daily(schedule_date, ...)"),
    ("月度效能、出勤率、工时效率、预警", "query_efficiency(year_month, ...)"),
    ("整体总人数/总工时/总览", "query_dashboard_stats(year_month)"),
    ("夜班、班次、排班规则、培训、原始签到、工作量、营销、宽带订单、配置", "run_sql"),
]


def build_data_catalog_prompt() -> str:
    """生成系统提示词中的数据表/字段/口径段落。"""
    lines = [
        "# 数据表与字段",
        "数据库为 PostgreSQL。以下为全部业务表；系统、安全、密钥和审计表不暴露。",
    ]
    for item in TABLE_CATALOG:
        lines.append(
            f"- {item['name']}（{item['label']}）：{', '.join(item['fields'])}"
        )
        lines.append(f"  用途：{item['purpose']}")
        if item.get("notes"):
            lines.append(f"  注意：{item['notes']}")
        if item.get("scenarios"):
            lines.append(f"  场景：{item['scenarios']}")
    lines.append("")
    lines.append("# 关键字段口径")
    for note in FIELD_NOTES:
        lines.append(f"- {note}")
    lines.append("")
    lines.append("# 工作量高频指标键")
    lines.append("workloads.metrics 常用键（JSONB，中文键名）：")
    for key in WORKLOAD_METRIC_KEYS:
        lines.append(f"- {key}")
    return "\n".join(lines)


def build_tool_routing_prompt() -> str:
    """生成场景到工具/表的查询路由段落。"""
    lines = [
        "# 查询路由",
        "先判断用户要的是汇总、排名、单日明细，还是跨表/扩展分析，再选择工具。",
    ]
    for scene, route in TOOL_ROUTING:
        lines.append(f"- {scene} → {route}")
    lines.append("")
    lines.append("工具无法覆盖时再用 run_sql；不要为了简单汇总绕过报表工具。")
    return "\n".join(lines)


def build_sql_rules_prompt() -> str:
    """生成 run_sql 使用规则和标准示例。"""
    return "\n".join([
        "# run_sql 规则",
        "- 仅允许单条 SELECT；禁止 INSERT/UPDATE/DELETE/DROP/ALTER 等写操作。",
        "- 禁止 WITH/CTE、SQL 注释、多语句；需要分步时用子查询。",
        "- 日期统一使用 YYYY-MM-DD；月份使用 YYYY-MM；不要用空字符串日期。",
        "- 日期过滤用 schedule_date/record_date/date/order_date/finish_date，不要用 created_at 代替业务日期。",
        "- 未写 LIMIT 时系统会自动补 LIMIT 200；run_sql 回传最多 50 行、2000 字符，优先写聚合查询。",
        "- 联表键：employees.id = daily_reports.emp_id / schedules.emp_id / monthly_reports.emp_id；employees.emp_no = checkins.emp_no / workloads.emp_no / training_records.emp_no / marketing_details.kf_id / seamless_orders.emp_no。",
        "- 统计在职员工时加 employees.status='在职' AND employees.deleted_at IS NULL。",
        "- 宽带订单默认加 is_excluded='否' AND is_duplicate='否'；营销明细按 data_type 区分线上直办/办理工单。",
        "- 查询结果为空时说明日期范围和筛选条件，不要编造数据。",
        "",
        "# 常用 SQL 示例",
        "- 日期区间个人工时：",
        "  SELECT e.name, SUM(d.actual_hours) AS hours FROM daily_reports d JOIN employees e ON e.id = d.emp_id WHERE d.schedule_date BETWEEN '2026-07-01' AND '2026-07-07' GROUP BY e.name ORDER BY hours DESC",
        "- 夜班排班：",
        "  SELECT e.name, s.schedule_date, s.shift_name FROM schedules s JOIN employees e ON e.id = s.emp_id WHERE s.is_night = TRUE AND s.schedule_date >= '2026-07-01' AND s.schedule_date < '2026-08-01' ORDER BY s.schedule_date",
        "- 工作量通话量：",
        "  SELECT w.name, SUM((w.metrics->>'服务量合计-通话量')::numeric) AS calls FROM workloads w WHERE w.date >= '2026-07-01' AND w.date < '2026-08-01' GROUP BY w.name ORDER BY calls DESC",
    ])
