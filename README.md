# 排班签到报表系统 - 详细设计文档

## 一、系统概述

### 1.1 项目背景

在现代企业管理中，员工考勤是人力资源管理的核心环节。传统的人工统计方式效率低下且易出错，需要一套自动化的排班签到管理系统来提升考勤管理效率。本系统旨在实现排班管理、签到记录导入、考勤自动计算、多维度查询统计的一体化解决方案。

### 1.2 项目目标

- **核心目标**：开发一个Web版排班签到情况报表系统，用于分析每天员工的到岗情况
- **功能目标**：支持排班管理、签到记录导入、多维度查询和导出
- **性能目标**：支持1000+员工、50000+条签到记录的稳定运行
- **体验目标**：提供友好的Web界面，支持多维度筛选和导出

### 1.3 技术栈

| 层级 | 技术选型 | 版本 | 说明 |
|-----|--------|------|------|
| 后端框架 | FastAPI | 0.104+ | 高性能异步框架 |
| ORM | SQLAlchemy | 2.0+ | Python ORM |
| 数据库 | PostgreSQL | 15+ | 主数据库 |
| 前端框架 | Vue3 | 3.3+ | Composition API |
| UI组件库 | Element Plus | 2.4+ | Element UI Vue3版 |
| 构建工具 | Vite | 5.0+ | 快速构建 |
| 部署 | Docker Compose | 3.8+ | 容器编排 |

### 1.4 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue3 + Element Plus)          │
│  登录页 │ 仪表盘 │ 员工管理 │ 排班管理 │ 考勤报表    │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP REST API
┌─────────────────────┴───────────────────────────────────┐
│                    后端 (FastAPI + SQLAlchemy)         │
│  认证模块 │ 员工模块 │ 排班模块 │ 签到模块 │ 报表模块  │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────┐
│                    数据库 (PostgreSQL 15)               │
│  users │ employees │ shift_types │ schedules │ checkins  │
│  daily_reports │ monthly_reports │ operation_logs         │
└─────────────────────────────────────────────────────────┘
```

## 二、数据库设计

### 2.1 ER图关系

```
┌──────────────────┐         ┌──────────────────┐
│      users       │         │      employees    │
│ (操作者/管理员)  │         │    (员工信息)    │
├──────────────────┤         ├──────────────────┤
│ PK id            │◄───┐   │ PK id            │
│    username      │    │   │    emp_no        │
│    password_hash │    │   │    name          │
│    role          │    └───│ FK created_by    │
│    created_at    │       │    team          │
└──────────────────┘       │    dept          │
                          │    role          │
┌──────────────────┐      │    status       │
│  shift_types     │       └────────┬─────────┘
│ (班次类型)       │                │
├──────────────────┤         ┌────┴────────┐
│ PK id            │         │ schedules   │
│    shift_name    │◄───────┤ (排班记录) │
│    start_time   │         ├─────────────┤
│    end_time    │         │ FK emp_id   │
│    work_hours  │         │ FK shift_type_id
│    color      │         │ FK created_by
│    is_night   │         │ schedule_date
└───────┬────────┘         │ schedule_type
        │                │ original_shift_id
        │                └────────┬────────┘
        │                         │
┌───────┴────────┐         ┌────┴────────┐
│    checkins   │         │ daily_reports│
│ (签到记录)   │         │ (考勤汇总)   │
├──────────────┤         ├─────────────┤
│ PK id       │         │ PK id       │
│    emp_no   │         │ FK emp_id   │
│    emp_name│         │ FK shift_type_id
│    checkin_time│     │ schedule_date
│    checkout_time   │ schedule_type
│    device_no │         │ status
│    dept    │         │ scheduled_hours│
│    import_batch  │    │ actual_hours  │
└──────────────┘         │ late_minutes  │
                         │ early_minutes│
                         └─────────────┘
```

### 2.2 表结构

#### 2.2.1 用户表 (users)

| 字段 | 类型 | 约束 | 说明 |
|-----|------|------|------|
| id | SERIAL | PK | 主键 |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 用户名 |
| password_hash | VARCHAR(255) | NOT NULL | 密码哈希(bcrypt) |
| display_name | VARCHAR(50) | | 显示名称 |
| role | VARCHAR(20) | DEFAULT 'user' | 角色(admin/user) |
| is_active | BOOLEAN | DEFAULT TRUE | 是否激活 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |

**索引**：`idx_users_username` ON `username`

#### 2.2.2 员工表 (employees)

| 字段 | 类型 | 约束 | 说明 |
|-----|------|------|------|
| id | SERIAL | PK | 主键 |
| emp_no | VARCHAR(20) | UNIQUE, NOT NULL | 工号 |
| name | VARCHAR(50) | NOT NULL | 姓名 |
| team | VARCHAR(50) | NOT NULL | 班组 |
| dept | VARCHAR(100) | | 归属部门 |
| role | VARCHAR(20) | DEFAULT '组员' | 岗位(组长/师傅/组员) |
| status | VARCHAR(20) | DEFAULT '在职' | 状态(在职/离职) |
| created_by | INTEGER | FK(users.id) | 创建人 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |

**索引**：
- `idx_employees_emp_no` ON `emp_no`
- `idx_employees_team` ON `team`
- `idx_employees_dept` ON `dept`
- `idx_employees_status` ON `status`

#### 2.2.3 班次类型表 (shift_types)

| 字段 | 类型 | 约束 | 说明 |
|-----|------|------|------|
| id | SERIAL | PK | 主键 |
| shift_name | VARCHAR(20) | UNIQUE, NOT NULL | 班次名称 |
| start_time | TIME | NOT NULL | 开始时间 |
| end_time | TIME | NOT NULL | 结束时间 |
| work_hours | DECIMAL(4,1) | NOT NULL | 工作时长(小时) |
| color | VARCHAR(20) | DEFAULT '#409EFF' | 颜色(前端显示) |
| is_night | BOOLEAN | DEFAULT FALSE | 是否夜班 |
| is_active | BOOLEAN | DEFAULT TRUE | 是否启用 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

**示例数据**：

| 班次名称 | 开始时间 | 结束时间 | 工作时长 | 颜色 | 是否夜班 |
|---------|---------|---------|---------|------|---------|
| 行政班 | 09:00 | 18:00 | 8.0 | #409EFF | 否 |
| 早班 | 08:00 | 16:00 | 8.0 | #67C23A | 否 |
| 中班 | 16:00 | 24:00 | 8.0 | #E6A23C | 否 |
| 晚班 | 24:00 | 08:00 | 8.0 | #909399 | 是 |

#### 2.2.4 排班表 (schedules)

| 字段 | 类型 | 约束 | 说明 |
|-----|------|------|------|
| id | SERIAL | PK | 主键 |
| emp_id | INTEGER | FK(employees.id), NOT NULL | 员工ID |
| schedule_date | DATE | NOT NULL | 排班日期 |
| shift_type_id | INTEGER | FK(shift_types.id) | 班次类型ID |
| shift_name | VARCHAR(50) | | 班次名称(冗余) |
| time_segments | JSON | | 时段详情(含扩展指标) |
| work_hours | DECIMAL(4,1) | | 排班工时 |
| is_night | BOOLEAN | DEFAULT FALSE | 是否晚班 |
| schedule_type | VARCHAR(20) | DEFAULT '正常' | 排班类型 |
| original_shift_id | INTEGER | FK(shift_types.id) | 原班次ID(换班时用) |
| notes | VARCHAR(200) | | 备注 |
| punctuality_rate | DECIMAL(5,2) | | 遵时率(%) |
| call_duration | DECIMAL(4,1) | | 通话时长(H) |
| organize_duration | DECIMAL(4,1) | | 整理时长(H) |
| utilization_rate | DECIMAL(5,2) | | 工时利用率(%) |
| attendance_rate | DECIMAL(5,2) | | 班表出勤率(%) |
| created_by | INTEGER | FK(users.id) | 创建人ID |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |

**排班类型枚举**：
- `正常` - 正常排班
- `换班` - 与他人换班
- `请假` - 请假
- `公休` - 公休
- `加班` - 加班
- `旷工` - 旷工

**索引**：
- `idx_schedules_date` ON `(schedule_date, emp_id)`
- `idx_schedules_emp_date` ON `(emp_id, schedule_date)`
- `idx_schedules_shift` ON `shift_type_id`

#### 2.2.5 签到记录表 (checkins)

| 字段 | 类型 | 约束 | 说明 |
|-----|------|------|------|
| id | SERIAL | PK | 主键 |
| emp_no | VARCHAR(20) | NOT NULL | 工号 |
| name | VARCHAR(50) | | 姓名 |
| checkin_time | DATETIME | NOT NULL | 签到时间 |
| checkout_time | DATETIME | | 签退时间 |
| device_no | VARCHAR(50) | | 设备号 |
| dept | VARCHAR(100) | | 归属部门(从系统导入) |
| import_batch | VARCHAR(50) | NOT NULL | 导入批次号 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

**索引**：
- `idx_checkins_time` ON `(checkin_time)`
- `idx_checkins_batch` ON `import_batch`
- `idx_checkins_empno` ON `emp_no`

#### 2.2.6 考勤汇总表 (daily_reports)

| 字段 | 类型 | 约束 | 说明 |
|-----|------|------|------|
| id | SERIAL | PK | 主键 |
| emp_id | INTEGER | FK(employees.id), NOT NULL | 员工ID |
| schedule_date | DATE | NOT NULL | 日期 |
| shift_type_id | INTEGER | FK(shift_types.id) | 班次ID |
| schedule_type | VARCHAR(20) | | 排班类型 |
| scheduled_start | TIME | | 计划开始时间 |
| scheduled_end | TIME | | 计划结束时间 |
| scheduled_hours | DECIMAL(4,1) | | 计划工时 |
| actual_checkin | DATETIME | | 实际签到时间 |
| actual_checkout | DATETIME | | 实际签退时间 |
| actual_hours | DECIMAL(4,1) | | 实际工时 |
| status | VARCHAR(20) | | 状态 |
| late_minutes | INTEGER | DEFAULT 0 | 迟到分钟数 |
| early_minutes | INTEGER | DEFAULT 0 | 早退分钟数 |
| overtime_hours | DECIMAL(4,1) | DEFAULT 0 | 加班工时 |
| calculated_at | TIMESTAMP | | 计算时间 |

**考勤状态枚举**：
- `正常` - 正常出勤
- `迟到` - 迟到
- `早退` - 早退
- `缺勤` - 缺勤
- `未排班` - 未排班
- `请假` - 请假
- `公休` - 公休
- `加班` - 加班

**索引**：
- `idx_daily_emp_date` ON `(emp_id, schedule_date)` UNIQUE
- `idx_daily_date` ON `schedule_date`
- `idx_daily_status` ON `status`

#### 2.2.7 月度考勤汇总表 (monthly_reports)

| 字段 | 类型 | 约束 | 说明 |
|-----|------|------|------|
| id | SERIAL | PK | 主键 |
| emp_id | INTEGER | FK(employees.id), NOT NULL | 员工ID |
| year_month | VARCHAR(7) | NOT NULL | 年月(2026-04) |
| scheduled_hours | DECIMAL(6,1) | DEFAULT 0 | 计划工时 |
| actual_hours | DECIMAL(6,1) | DEFAULT 0 | 实际工时 |
| normal_days | INTEGER | DEFAULT 0 | 正常天数 |
| late_days | INTEGER | DEFAULT 0 | 迟到天数 |
| early_days | INTEGER | DEFAULT 0 | 早退天数 |
| absent_days | INTEGER | DEFAULT 0 | 缺勤天数 |
| leave_days | INTEGER | DEFAULT 0 | 请假天数 |
| timeoff_days | INTEGER | DEFAULT 0 | 公休天数 |
| overtime_hours | DECIMAL(6,1) | DEFAULT 0 | 加班工时 |
| owed_hours | DECIMAL(6,1) | DEFAULT 0 | 欠时工时 |
| calculated_at | TIMESTAMP | | 计算时间 |

**索引**：
- `idx_monthly_emp_month` ON `(emp_id, year_month)` UNIQUE

#### 2.2.8 操作日志表 (operation_logs)

| 字段 | 类型 | 约束 | 说明 |
|-----|------|------|------|
| id | SERIAL | PK | 主键 |
| user_id | INTEGER | FK(users.id) | 操作人ID |
| operation_type | VARCHAR(50) | NOT NULL | 操作类型 |
| target_table | VARCHAR(50) | NOT NULL | 目标表 |
| target_id | INTEGER | | 目标ID |
| details | JSONB | | 详情 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

**索引**：
- `idx_logs_user` ON `user_id`
- `idx_logs_table` ON `(target_table, target_id)`
- `idx_logs_created` ON `created_at`

## 三、功能模块

### 3.1 认证模块

| 功能 | 说明 |
|-----|------|
| 用户登录 | 用户名+密码登录，会话token管理 |
| 用户登出 | 清除会话 |
| 会话保持 | JWT Token有效期24小时 |
| 权限控制 | admin和user两种角色 |

### 3.2 员工管理

| 功能 | 说明 |
|-----|------|
| 员工列表 | 支持分页、关键词搜索、部门/班组筛选 |
| 员工新增 | 手动新增员工信息 |
| 员工编辑 | 修改员工信息 |
| 员工删除 | 软删除(标记为离职) |
| 员工导入 | Excel批量导入员工 |
| 员工导出 | 导出为Excel/CSV |

**Excel导入模板**：

| 工号 | 姓名 | 班组 | 部门 | 岗位 |
|-----|------|------|------|------|
| E001 | 张三 | 一班1组 | 客服中心 | 组员 |

### 3.3 班次类型管理

| 功能 | 说明 |
|-----|------|
| 班次列表 | 查看所有班次类型 |
| 班次新增 | 新增班次类型 |
| 班次编辑 | 修改班次时间 |
| 班次删除 | 软删除(关联排班时禁止删除) |

### 3.4 排班管理

| 功能 | 说明 |
|-----|------|
| 日排班表 | 按日期查看排班情况 |
| 月排班表 | 按月查看排班日历 |
| 手动排班 | 新增/修改单条排班 |
| 批量排班 | 按班组/部门批量设置排班 |
| 换班管理 | 两人交换班次 |
| 请假申请 | 标记请假 |
| 公休申请 | 标记公休 |
| 导入考勤报表 | Excel批量导入排班(含遵时率/通话时长等指标) |

### 3.5 签到记录

| 功能 | 说明 |
|-----|------|
| 记录查看 | 查看已导入的签到记录 |
| 记录导入 | CSV文件导入签到记录 |
| 批次管理 | 按导入批次删除记录 |
| 记录统计 | 查看导入统计 |

**CSV导入格式**：

```
工号,姓名,签到时间,签退时间,设备号,归属部门
E001,张三,2026-04-14 08:05:00,2026-04-14 17:02:00,Device001,客服中心
```

### 3.6 考勤计算

| 功能 | 说明 |
|-----|------|
| 自动计算 | 导入签到记录时自动计算当天考勤 |
| 重新计算 | 修改排班后自动重新计算 |
| 迟到判定 | 签到时间晚于班次开始时间>0 |
| 早退判定 | 签退时间早于班次结束时间>0 |
| 欠时统计 | 月度欠时=计划工时-实际工时-加班 |
| 加班计算 | 实际工时-计划工时>0部分 |

### 3.7 考勤报表

| 功能 | 说明 |
|-----|------|
| 日报表 | 按日期查看考勤明细 |
| 月度汇总 | 按月统计汇总 |
| 多维度筛选 | 支持部门/班组/状态筛选 |
| 数据导出 | Excel/CSV导出 |

### 3.8 系统管理

| 功能 | 说明 |
|-----|------|
| 用户管理 | 管理员用户CRUD |
| 操作日志 | 查看所有操作记录 |
| 系统统计 | 员工总数/今日考勤率等 |

## 四、API设计

### 4.1 认证模块

| 方法 | 路径 | 说明 | 请求体 | 响应 |
|-----|------|------|--------|------|
| POST | /api/auth/login | 登录 | `{username, password}` | `{token, user}` |
| POST | /api/auth/logout | 登出 | - | `{message}` |
| GET | /api/auth/me | ���前���户 | - | `{id, username, role}` |

### 4.2 员工管理

| 方法 | 路径 | 说明 | 请求体 | 响应 |
|-----|------|------|--------|------|
| GET | /api/employees | 员工列表 | `?page=1&limit=20&team=xxx&dept=xxx&search=xxx` | `{items, total}` |
| POST | /api/employees | 新增员工 | `{emp_no, name, team, dept, role}` | `{id}` |
| PUT | /api/employees/{id} | 修改员工 | `{name, team, dept...}` | `{id}` |
| DELETE | /api/employees/{id} | 删除员工 | - | `{message}` |
| POST | /api/employees/import | 导入员工 | `multipart/form-data` | `{count}` |
| GET | /api/employees/export | 导出员工 | - | 文件下载 |

### 4.3 班次类型管理

| 方法 | 路径 | 说明 | 请求体 | 响应 |
|-----|------|------|--------|------|
| GET | /api/shift-types | 班次列表 | - | `[{id, shift_name...}]` |
| POST | /api/shift-types | 新增班次 | `{shift_name, start_time...}` | `{id}` |
| PUT | /api/shift-types/{id} | 修改班次 | `{start_time, end_time...}` | `{id}` |
| DELETE | /api/shift-types/{id} | 删除班次 | - | `{message}` |

### 4.4 排班管理

| 方法 | 路径 | 说明 | 请求体 | 响应 |
|-----|------|------|--------|------|
| GET | /api/schedules | 排班列表 | `?date=2026-04-14&emp_id=1` | `[{id, emp_id...}]` |
| POST | /api/schedules | 新增排班 | `{emp_id, schedule_date, shift_type_id}` | `{id}` |
| PUT | /api/schedules/{id} | 修改排班 | `{shift_type_id, notes}` | `{id}` |
| DELETE | /api/schedules/{id} | 删除排班 | - | `{message}` |
| POST | /api/schedules/batch | 批量排班 | `{emp_ids[], shift_type_id, date}` | `{count}` |
| POST | /api/schedules/swap | 换班 | `{schedule_a_id, schedule_b_id}` | `{message}` |
| POST | /api/schedules/leave | 请假 | `{emp_id, date, days}` | `{id}` |
| POST | /api/schedules/timeoff | 公休 | `{emp_id, date, days}` | `{id}` |
| POST | /api/schedules/import-attendance-report | 导入考勤报表 | `file: .xlsx` | `{message, employees, schedules}` |

### 4.5 签到记录

| 方法 | 路径 | 说明 | 请求体 | 响应 |
|-----|------|------|--------|------|
| GET | /api/checkins | 签到列表 | `?date=2026-04-14&batch=xxx` | `{items, total}` |
| POST | /api/checkins/import | 导入签到 | `multipart/form-data` | `{count, batch}` |
| DELETE | /api/checkins/{id} | 删除记录 | - | `{message}` |
| DELETE | /api/checkins/import/{batch} | 删除批次 | - | `{count}` |

### 4.6 考勤报表

| 方法 | 路径 | 说明 | 请求体 | 响应 |
|-----|------|------|--------|------|
| GET | /api/reports/daily | 日报表 | `?date=2026-04-14&team=xxx&status=迟到` | `[{emp_name, status...}]` |
| GET | /api/reports/month | 月报表 | `?year_month=2026-04&dept=xxx` | `[{emp_name, days...}]` |
| GET | /api/reports/month-summary | 月度汇总 | `?year_month=2026-04` | `[{emp_name, hours...}]` |
| GET | /api/reports/export | 导出报表 | `?type=month&year_month=2026-04` | 文件下载 |

### 4.7 系统管理

| 方法 | 路径 | 说明 | 请求体 | 响应 |
|-----|------|------|--------|------|
| GET | /api/logs | 操作日志 | `?page=1&limit=20&user_id=1` | `{items, total}` |
| GET | /api/stats | 系统统计 | - | `{employee_count, today_attendance...}` |
| GET | /api/departments | 部门列表 | - | `[{dept, count}]` |
| GET | /api/teams | 班组列表 | - | `[{team, count}]` |

## 五、多维度查询与筛选

### 5.1 筛选条件

**员工筛选**：
- `emp_id` - 员工ID
- `emp_no` - 工号(模糊)
- `name` - 姓名(模糊)
- `team` - 班组
- `dept` - 归属部门
- `role` - 岗位角色
- `status` - 在职状态

**时间筛选**：
- `date` - 单个日期
- `start_date` / `end_date` - 日期范围
- `year_month` - 年月(2026-04)

**考勤状态筛选**：
- `status` - 正常/迟到/早退/缺勤/未排班/请假/公休/加班

**排班类型筛选**：
- `schedule_type` - 正常/换班/请假/公休/加班/旷工

### 5.2 报表字段

**日报表字段**：

| 字段 | 类型 | 说明 |
|-----|------|------|
| schedule_date | DATE | 日期 |
| emp_no | VARCHAR | ���号 |
| name | VARCHAR | 姓名 |
| team | VARCHAR | 班组 |
| dept | VARCHAR | 部门 |
| shift_name | VARCHAR | 班次名称 |
| scheduled_time | VARCHAR | 计划时间 |
| actual_checkin | DATETIME | 实际签到 |
| actual_checkout | DATETIME | 实际签退 |
| status | VARCHAR | 状态 |
| late_minutes | INTEGER | 迟到分钟 |
| early_minutes | INTEGER | 早退分钟 |
| actual_hours | DECIMAL | 实际工时 |

**月度汇总字段**：

| 字段 | 类型 | 说明 |
|-----|------|------|
| year_month | VARCHAR | 年月 |
| emp_no | VARCHAR | 工号 |
| name | VARCHAR | 姓名 |
| team | VARCHAR | 班组 |
| dept | VARCHAR | 部门 |
| scheduled_hours | DECIMAL | 计划工时 |
| actual_hours | DECIMAL | 实际工时 |
| overtime_hours | DECIMAL | 加班工时 |
| owed_hours | DECIMAL | 欠时工时 |
| normal_days | INTEGER | 正常天数 |
| late_days | INTEGER | 迟到天数 |
| early_days | INTEGER | 早退天数 |
| absent_days | INTEGER | 缺勤天数 |
| leave_days | INTEGER | 请假天数 |
| timeoff_days | INTEGER | 公休天数 |

## 六、核心业务逻辑

### 6.1 考勤计算

**业务规则**：

```
迟到判定: 签到时间 > 计划开始时间 则迟到分钟 = 签到时间 - 计划开始时间
早退判定: 签退时间 < 计划结束时间 则早退分钟 = 计划结束时间 - 签退时间
缺勤判定: 有排班无签到记录 = 缺勤
实际工时: 签退时间 - 签到时间
加班工时: max(0, 实际工时 - 计划工时)
欠时工时: max(0, 计划工时 - 实际工时 - 加班工时)
```

**计算流程**：

```python
def calculate_daily_attendance(emp_id: int, date: date):
    # 1. 获取当天排班
    schedule = get_schedule(emp_id, date)
    if not schedule:
        return {"status": "未排班"}

    # 2. 获取签到记录
    checkins = get_checkins(emp_id, date)
    if not checkins:
        if schedule.schedule_type in ["请假", "公休"]:
            return {"status": schedule.schedule_type}
        return {"status": "缺勤"}

    # 3. 计算迟到早退
    first_checkin = checkins.first()
    last_checkout = checkins.last()

    shift = schedule.shift_type
    late_minutes = max(0, (first_checkin.checkin_time - shift.start_time).minutes)
    early_minutes = max(0, (shift.end_time - last_checkout.checkout_time).minutes)

    # 4. 计算工时
    if first_checkin and last_checkout:
        actual_hours = (last_checkout.checkout_time - first_checkin.checkin_time).hours
    else:
        actual_hours = 0

    scheduled_hours = shift.work_hours
    overtime_hours = max(0, actual_hours - scheduled_hours)

    # 5. 确定状态
    if schedule.schedule_type == "请假":
        status = "请假"
    elif schedule.schedule_type == "公休":
        status = "公休"
    elif schedule.schedule_type == "加班":
        status = "加班"
    elif not first_checkin:
        status = "缺勤"
    elif late_minutes > 0:
        status = "迟到"
    elif early_minutes > 0:
        status = "早退"
    else:
        status = "正常"

    return {
        "status": status,
        "late_minutes": late_minutes,
        "early_minutes": early_minutes,
        "actual_hours": actual_hours,
        "scheduled_hours": scheduled_hours,
        "overtime_hours": overtime_hours,
        "actual_checkin": first_checkin.checkin_time,
        "actual_checkout": last_checkout.checkout_time
    }
```

### 6.2 月度汇总计算

```python
def calculate_monthly_summary(emp_id: int, year_month: str):
    daily_reports = get_daily_reports(emp_id, year_month)

    scheduled = sum(r.scheduled_hours for r in daily_reports)
    actual = sum(r.actual_hours for r in daily_reports)
    overtime = sum(r.overtime_hours for r in daily_reports)

    normal_days = count_by_status(daily_reports, "正常")
    late_days = count_by_status(daily_reports, "迟到")
    early_days = count_by_status(daily_reports, "早退")
    absent_days = count_by_status(daily_reports, "缺勤")
    leave_days = count_by_status(daily_reports, "请假")
    timeoff_days = count_by_status(daily_reports, "公休")

    owed_hours = max(0, scheduled - actual - overtime)

    return {
        "scheduled_hours": scheduled,
        "actual_hours": actual,
        "overtime_hours": overtime,
        "owed_hours": owed_hours,
        "normal_days": normal_days,
        "late_days": late_days,
        "early_days": early_days,
        "absent_days": absent_days,
        "leave_days": leave_days,
        "timeoff_days": timeoff_days
    }
```

### 6.3 换班逻辑

```python
def swap_shift(schedule_a_id: int, schedule_b_id: int, user_id: int):
    schedule_a = get_schedule(schedule_a_id)
    schedule_b = get_schedule(schedule_b_id)

    if not schedule_a or not schedule_b:
        raise Error("排班记录不存在")

    if schedule_a.schedule_date != schedule_b.schedule_date:
        raise Error("只能交换同一天的班次")

    if schedule_a.emp_id == schedule_b.emp_id:
        raise Error("不能与自己交换班次")

    # 交换班次
    temp_shift = schedule_a.shift_type_id
    schedule_a.shift_type_id = schedule_b.shift_type_id
    schedule_b.shift_type_id = temp_shift

    # 记录原班次
    schedule_a.original_shift_id = schedule_b.original_shift_id or schedule_b.shift_type_id
    schedule_b.original_shift_id = schedule_a.original_shift_id

    # 记录操作日志
    log_operation(user_id, "swap", "schedules",
                  {"a": schedule_a_id, "b": schedule_b_id})

    # 重新计算考勤
    recalculate_attendance(schedule_a.schedule_date)
    recalculate_attendance(schedule_b.schedule_date)

    return {"message": "换班成功"}
```

### 6.4 批量排班逻辑

```python
def batch_schedule(emp_ids: list, shift_type_id: int, date: date, user_id: int):
    success_count = 0

    for emp_id in emp_ids:
        existing = get_schedule(emp_id, date)
        if existing:
            existing.shift_type_id = shift_type_id
            existing.updated_at = NOW()
        else:
            create_schedule(emp_id, date, shift_type_id, user_id)
        success_count += 1

    # 重新计算当天考勤
    recalculate_attendance(date)

    return {"success_count": success_count}
```

## 七、前端设计

### 7.1 页面结构

```
/login                 - 登录页
/                      - 首页/仪表盘
/employees             - 员工管理
  /employees/list      - 员工列表
  /employees/add       - 新增员工
  /employees/edit/:id  - 编辑员工
  /employees/import    - 导入员工
/schedules             - 排班管理
  /schedules/daily     - 日排班表
  /schedules/month     - 月排班表
  /schedules/edit     - 排班编辑
  /schedules/swap      - 换班管理
  /schedules/leave     - 请假管理
/checkins             - 签到记录
  /checkins/list       - 记录列表
  /checkins/import     - 导入记录
/reports              - 考勤报表
  /reports/daily       - 日报表
  /reports/month      - 月度汇总
  /reports/export     - 导出中心
/system               - 系统管理
  /system/shifts      - 班次类型
  /system/users       - 用户管理
  /system/logs        - 操作日志
```

### 7.2 核心组件

| 组件 | 说明 |
|-----|------|
| ScheduleCalendar | 月排班日历组件 |
| DailyReportTable | 日报表表格 |
| MonthlySummaryTable | 月度汇总表格 |
| EmployeeImport | 员工导入组件 |
| CheckinImport | 签到导入组件 |
| ShiftSwapDialog | 换班对话框 |
| BatchScheduleDialog | 批量排班对话框 |
| ExportDialog | 导出配置对话框 |

### 7.3 筛选示例

```javascript
// 日报表筛选
const dailyParams = {
  date: "2026-04-14",
  team: "一班1组",
  dept: "客服中心",
  status: "迟到"
}

// 月度汇总筛选
const monthlyParams = {
  year_month: "2026-04",
  team: "一班1组",
  dept: "客服中心"
}
```

### 7.4 界面布局

```
┌────────────────────────────────────────────────────────────┐
│  排班签到报表系统                    [用户名] [登出]      │
├──────────┬─────────────────────────────────────────────────┤
│          │                                                 │
│ 仪表盘   │  ┌─────────────────────────────────────────┐  │
│ 员工管理 │  │                                         │  │
│ 排班管理 │  │           主要内容区域                   │  │
│ 考勤报表 │  │                                         │  │
│ 系统管理 │  │                                         │  │
│          │  └─────────────────────────────────────────┘  │
│          │                                                 │
└──────────┴─────────────────────────────────────────────────┘
```

## 八、导入/导出规则

### 8.1 考勤报表导入（替代原排班Excel导入）

通过 `POST /api/schedules/import-attendance-report` 上传考勤出勤报表(.xlsx)，自动解析排班及扩展指标。

**文件格式**：考勤系统导出的日报表，每行一个员工时段

**列结构**：

| 列 | 字段 | 说明 | 映射目标 |
|----|------|------|---------|
| A | 排班日期 | 如 `2026-06-22` | `schedule_date` |
| B | 区队名称 | 如 `热线运营组` | `employee.dept` |
| C | 班组名称 | 如 `一班1组` | `employee.team` |
| D | 姓名 | 员工姓名 | `employee.name` |
| E | 账号 | 员工工号 | `employee.emp_no`(优先匹配) |
| F | 班次名称 | 如 `中班9`、`行8.5` | `shift_name` |
| G | 时间范围 | 如 `08:30~13:00` | `time_segments`(每段) |
| M | 班次时长 | 每段工时(如 `4.5`) | `work_hours`(累加) |
| O | 遵时率 | 如 `88.89` | `punctuality_rate` |
| P | 通话时长(H) | 如 `2.53` | `call_duration`(累加) |
| Q | 整理时长(H) | 如 `0.48` | `organize_duration`(累加) |
| R | 工时利用率 | 如 `57.50%` | `utilization_rate` |
| S | 班表出勤率 | 如 `88.89%` | `attendance_rate` |

**处理逻辑**：
1. 按 `账号(E)+日期(A)` 分组，合并多时段班次
2. 匹配员工：账号 → 姓名 → 自动新建
3. 同组多段合并：工时累加，遵时率/利用率/出勤率按工时加权平均
4. `休息` → `schedule_type = "公休"`；`离职` → 跳过
5. 先清理导入日期范围内的旧排班，再批量新建
6. 导入完成自动触发考勤重算(`save_daily_report`)

> **签入签出报表口径**：`/api/checkins/report` 汇总与个人多维统计明细中的遵时率、工时利用率、班表出勤率不再使用导入值/导入值平均，改为系统重算：
> - 遵时率 = Σ实际工时 / Σ排班工时 × 100%（实际工时取考勤日报 `actual_hours`，即签入/签出与排班时段的交集工时）
> - 工时利用率 = (Σ通话时长 + Σ整理时长) / Σ实际工时 × 100%（通话/整理时长仍为导入值）
> - 班表出勤率 = 出勤天数 / 排班天数 × 100%（出勤天数=有签到记录的日期数，排班天数=`scheduled_hours>0` 的日期数）
> 单日明细同样按上述公式逐日重算，与汇总口径一致；`schedules` 表仍保留导入原值用于比对。

**time_segments JSON 扩展**：
```json
[
  {"start": "08:30", "end": "13:00", "work_hours": 4.5,
   "punctuality_rate": 88.89, "call_duration": 2.0,
   "organize_duration": 0.3, "utilization_rate": 57.50,
   "attendance_rate": 88.89},
  {"start": "15:30", "end": "20:00", "work_hours": 4.5,
   "punctuality_rate": 95.56, "call_duration": 2.5,
   "organize_duration": 0.4, "utilization_rate": 67.44,
   "attendance_rate": 95.56}
]
```

### 8.2 签到记录导入

**支持格式**：CSV (GBK/UTF-8编码自动识别)

**筛选规则**：
- 只导入部门：`广西分公司>>省中心>>客户服务营销中心`
- 其他部门员工自动跳过

**字段映射**：
| CSV列名 | 系统字段 | 说明 |
|--------|---------|-------|
| 账号 | emp_no | 员工工号 |
| 用户名 | name | 员工姓名 |
| 签入时间 | checkin_time | 签到时间 |
| 签出时间 | checkout_time | 签退时间 |
| 签入分机 | device_no | 设备号 |
| 所属部门全路径 | dept | 归属部门 |

### 8.3 报表导出

**支持格式**：Excel (.xlsx)、CSV

**模板格式**：

| 姓名 | 2026-04-01 | 2026-04-02 | ... |
|-----|------------|------------|-----|
| 张三 | 早班 | 中班 | ... |
| 李四 | 中班 | 晚班 | ... |

**导入流程**：
1. 解析Excel，第一行为日期
2. 匹配员工姓名
3. 匹配班次名称
4. 批量创建/更新排班
5. 自动计算考勤
6. 返回导入结果

### 8.4 报表导出

**支持格式**：Excel (.xlsx)、CSV

**导出选项**：
- 字段选择
- 日期范围
- 班组筛选
- 部门筛选
- 状态筛选

## 九、非功能需求

### 9.1 性能要求

| 指标 | 要求 |
|-----|------|
| 页面加载 | < 2秒 |
| API响应 | < 500ms |
| 批量导入 | 1000条/秒 |
| 支持并发 | 50用户 |

### 9.2 安全要求

- 密码bcrypt哈希存储
- JWT Token认证
- SQL注入防护
- XSS防护
- CORS配置

### 9.3 可用性要求

- 支持Chrome/Edge/Firefox
- 响应式布局
- 错误提示友好
- 操作日志完整

## 十、Docker 部署

### 10.1 目录结构

```
schedule-report-system/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml
└── .env
```

### 10.2 docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/schedule_db
      - SECRET_KEY=${SECRET_KEY}
      - ACCESS_TOKEN_EXPIRE_MINUTES=1440
    depends_on:
      - db
    volumes:
      - ./backend:/app
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=schedule_db
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  pgdata:
```

### 10.3 环境变量

```
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:pass@db:5432/schedule_db
POSTGRES_USER=user
POSTGRES_PASSWORD=pass
POSTGRES_DB=schedule_db
```

## 十一、开发计划

### 11.1 第一阶段：基础框架 (第1-2周)

| 任务 | 说明 |
|-----|------|
| 项目初始化 | 创建前后端项目结构 |
| Docker环境 | 配置docker-compose |
| 数据库模型 | 创建所有数据表 |
| 基础API | 认证、员工CRUD |
| 基础前端 | 登录页、布局 |

**交付物**：基础CRUD功能可用

### 11.2 第二阶段：核心功能 (第3-4周)

| 任务 | 说明 |
|-----|------|
| 排班管理 | 日/月排班表 |
| 班次管理 | 班次类型CRUD |
| 签到导入 | CSV导入功能 |
| 考勤计算 | 迟到/早退/缺勤判定 |

**交付物**：核心业务流程可用

### 11.3 第三阶段：扩展功能 (第5-6周)

| 任务 | 说明 |
|-----|------|
| 换班管理 | 换班功能 |
| 请假/公休 | 请假公休申请 |
| 批量排班 | 批量排班功能 |
| 操作日志 | 操作记录 |

**交付物**：扩展功能可用

### 11.4 第四阶段：报表统计 (第7-8周)

| 任务 | 说明 |
|-----|------|
| 日报表 | 日考勤报表 |
| 月度汇总 | 月度统计 |
| 多维度筛选 | 筛选功能 |
| 导出功能 | Excel/CSV导出 |

**交付物**：报表功能完整

### 11.5 第五阶段：完善 (第9周)

| 任务 | 说明 |
|-----|------|
| UI优化 | 界面优化 |
| 权限管理 | 角色权限 |
| 性能优化 | 缓存、索引 |
| 测试 | 集成测试 |

**交付物**：生产就绪

## 十二、排班时长与欠时统计说明

### 12.1 排班时长定义

| 概念 | 定义 |
|-----|------|
| 计划工时 | 排班班次设定的工作时长(如中班8小时) |
| 实际工时 | 实际签退时间 - 实际签到时间 |
| 加班工时 | max(0, 实际工时 - 计划工时) |
| 欠时工时 | max(0, 计划工时 - 实际工时 - 加班工时) |

### 12.2 月度统计示例

| 姓名 | 班组 | 部门 | 计划工时 | 实际工时 | 加班工时 | 欠时工时 | 正常 | 迟到 | 早退 | 缺勤 |
|-----|------|------|---------|---------|---------|---------|-----|-----|-----|-----|
| 陈坤兰 | 一班1组 | 客服中心 | 176 | 168 | 8 | 0 | 20 | 1 | 0 | 0 |
| 黄设咸 | 一班2组 | 客服中心 | 160 | 152 | 0 | 8 | 18 | 2 | 0 | 1 |

---

## 十三、权限系统 (RBAC)

### 13.1 概述

系统采用基于角色的权限控制（RBAC）。每个角色是一组权限的集合，用户通过关联角色获得权限。

```
用户 ──→ 角色 ──→ 权限集合
                    ├── employees.view
                    ├── employees.create
                    ├── schedules.upload
                    └── ...
```

### 13.2 默认角色

| 角色 | 说明 | 系统保护 |
|------|------|----------|
| `admin` | 超级管理员，拥有所有权限（跳过检查） | 是（不可删除/修改） |
| `manager` | 经理，可管理数据和导入 | 否 |
| `user` | 普通用户，默认只可查看数据 | 否 |

### 13.3 权限命名规则

权限键格式：`{page_key}.{action}`

| 页面 key | 页面显示名 | 可用操作 |
|----------|-----------|----------|
| `employees` | 员工管理 | view, create, edit, delete, upload |
| `schedules` | 排班管理 | view, create, edit, delete, upload |
| `checkins` | 签到记录 | view, delete, upload |
| `checkin_report` | 签入签出报表 | view |
| `reports` | 考勤报表 | view |
| `shift_types` | 班次管理 | view, create, edit, delete |
| `work_hour_settings` | 工时预警设置 | view, create, edit, delete |
| `system` | 系统管理 | view, clear_data |
| `users` | 用户管理 | view, manage |
| `roles` | 角色管理 | view, manage |

### 13.4 添加新页面

当需要新增一个页面时，按以下步骤操作：

**步骤1：注册权限**

在以下两个文件的 `PERMISSION_REGISTRY` 中添加条目：

`backend/app/core/permissions.py`：
```python
PERMISSION_REGISTRY = {
    # ... 已有页面 ...
    "your_page": {
        "label": "你的页面",
        "permissions": {
            "view": "查看",
            "create": "新增",
            "edit": "编辑",
            "delete": "删除",
        },
    },
}
```

`frontend/src/permissions.js`：
```javascript
export const PERMISSION_REGISTRY = {
  // ... 已有页面 ...
  your_page: {
    label: '你的页面',
    permissions: {
      view: '查看',
      create: '新增',
      edit: '编辑',
      delete: '删除',
    },
  },
}
```

**步骤2：添加路由**

`frontend/src/router/index.js`：
```javascript
{
  path: 'your-page',
  name: 'YourPage',
  component: () => import('../views/YourPage.vue'),
  meta: { permission: 'your_page.view' }
}
```

**步骤3：添加侧边栏**

`frontend/src/views/Main.vue`：
```html
<el-menu-item v-if="userStore.canView('your_page')" index="/your-page">
  <el-icon><YourIcon /></el-icon>
  <span>你的页面</span>
</el-menu-item>
```

**步骤4：后端 API 权限保护**

```python
# 在 API 端点中使用
from app.core.security import require_permission

@router.post("/api/your-page/items")
def create_item(..., current_user: dict = Depends(get_current_user)):
    require_permission(current_user, "your_page.create")
    # ...
```

**步骤5：前端按钮权限控制**

```html
<el-button v-if="userStore.hasPermission('your_page.create')">
  新增
</el-button>
```

完成以上步骤后：
- 角色管理页面自动显示新页面的权限复选框
- 默认角色自动获得相应权限
- 路由守卫自动拦截无权限用户

### 13.5 默认权限分配逻辑

```python
def get_default_permissions(role_name):
    if role_name == "admin":
        return {all_permissions: True}     # admin 全部权限
    
    admin_only_views = {"system", "users", "roles"}
    admin_only_actions = {"clear_data", "manage"}
    
    for each permission key:
        if action == "view":
            # 非 admin-only 页面默认可查看
            result[key] = page not in admin_only_views
        elif action in admin_only_actions:
            result[key] = False            # 只有 admin 能管理/清除
        else:
            result[key] = role_name == "manager"  # 仅 manager 有编辑/上传权限
```

### 13.6 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/roles/all | 获取所有角色列表 |
| GET | /api/roles | 分页获取角色 |
| POST | /api/roles | 新增角色 |
| PUT | /api/roles/{id} | 修改角色（系统角色不可修改） |
| DELETE | /api/roles/{id} | 删除角色（有用户关联或系统角色不可删除） |
| GET | /api/roles/permissions | 获取权限注册表 |
| GET | /api/users/roles | 获取角色下拉列表 |

---

## 十四、版本记录

| 版本 | 日期 | 说明 |
|-----|------|------|
| v1.0 | 2026-04-16 | 初始版本 |
| v1.1 | 2026-04-24 | 新增员工导入功能 |
| v1.2 | 2026-06-23 | 新增考勤报表导入接口，替代原排班导入；新增遵时率/通话时长/整理时长/工时利用率/班表出勤率字段 |
| v1.3 | 2026-08-17 | 签入签出报表遵时率/工时利用率/班表出勤率改为系统重算（汇总与逐日明细同口径，见 8.1） |

---

## 十五、使用指南

### 14.1 数据导入流程

系统支持三种数据的导入，按顺序操作：

#### 步骤1：导入员工（可选但推荐）

如果需要使用真实工号，建议先导入员工表：

1. 进入「员工管理」页面
2. 点击「导入员工」按钮
3. 上传员工Excel文件

**员工Excel格式要求**：

| 工号 | 姓名 | 班组 | 部门 | 岗位 | 状态 |
|-----|------|------|------|------|------|
| KF77130169 | 陈坤兰 | 一班1组 | 客服中心 | 组长 | 在职 |
| KF77130247 | 张三 | 一班2组 | 客服中心 | 组员 | 在职 |

- 工号、姓名：必填
- 班组、部门、岗位、状态：可选

#### 步骤2：导入考勤报表

1. 进入「排班管理」页面
2. 点击「导入考勤报表」按钮
3. 上传考勤出勤报表Excel文件(.xlsx)

**报表格式**：考勤系统导出的日报表，每行一个员工时段

**关键列**：

| 列 | 内容 | 说明 |
|----|------|------|
| A 排班日期 | `2026-06-22` | 排班日期 |
| E 账号 | `KF77130173` | 员工工号(优先匹配) |
| F 班次名称 | `中班9` | 班次 |
| G 时间范围 | `08:30~13:00` | 时段(多段自动合并) |
| M 班次时长 | `4.5` | 工时 |
| O 遵时率 | `88.89` | 遵时率(%) |
| P 通话时长 | `2.53` | 通话时长(H) |
| Q 整理时长 | `0.48` | 整理时长(H) |
| R 工时利用率 | `57.50%` | 工时利用率(%) |
| S 班表出勤率 | `88.89%` | 班表出勤率(%) |

#### 步骤3：导入签到记录

1. 进入「签到记录」页面
2. 点击「导入签到」按钮
3. 上传签到CSV文件

**签到CSV格式要求**：

| 账号 | 用户名 | 签入时间 | 签出时间 | 所属部门全路径 |
|-----|--------|---------|---------|---------------|
| KF77130169 | 陈坤兰 | 2026-04-14 08:30:00 | 2026-04-14 17:30:00 | 广西分公司>>省中心>>客户服务营销中心 |

- 签入时间必填
- 系统自动过滤非目标部门数据

### 15.2 考勤计算逻辑

1. 排班表导入后，系统记录每个员工的排班信息
2. 签到记录导入后，系统自动匹配签到与排班
3. 按姓名匹配（有工号时优先工号匹配）
4. 计算实际工时：累加所有签到段时长
5. 自动生成日报表和月汇总

### 15.3 报表维度

- **日报表**：按天查看考勤明细
- **月度汇总**：按人按月统计工时
- **自定义时间段**：跨日期范围统计
- **班组排名**：按班组统计汇总