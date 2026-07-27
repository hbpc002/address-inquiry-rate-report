from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models.user import User
    from app.models.role import Role
    from app.models.employee import Employee
    from app.models.shift_type import ShiftType
    from app.models.schedule import Schedule
    from app.models.checkin import Checkin
    from app.models.daily_report import DailyReport
    from app.models.monthly_report import MonthlyReport
    from app.models.operation_log import OperationLog
    from app.models.work_hour_threshold import WorkHourThreshold
    from app.models.attendance_config import AttendanceConfig
    from app.models.announcement import Announcement
    from app.models.workload import Workload
    from app.models.field_annotation import FieldAnnotation

    Base.metadata.create_all(bind=engine)
    _migrate_db()
    _init_default_data()


def _migrate_db():
    from sqlalchemy import inspect as sa_inspect, text
    from app.models.user import User
    from app.models.role import Role

    db = SessionLocal()
    try:
        inspector = sa_inspect(engine)
        tables = inspector.get_table_names()

        if 'users' in tables:
            existing_columns = [col['name'] for col in inspector.get_columns('users')]
            column_defaults = {
                'id': 'INTEGER',
                'username': 'VARCHAR(50)',
                'password_hash': 'VARCHAR(255)',
                'display_name': 'VARCHAR(50)',
                'role': "VARCHAR(20) DEFAULT 'user'",
                'role_id': 'INTEGER',
                'is_active': 'BOOLEAN DEFAULT TRUE',
                'created_at': 'TIMESTAMP',
                'updated_at': 'TIMESTAMP'
            }
            for col_name, col_def in column_defaults.items():
                if col_name not in existing_columns:
                    sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"
                    try:
                        db.execute(text(sql))
                        print(f"Added column {col_name} to users")
                    except Exception as e:
                        print(f"Failed to add column {col_name}: {e}")

        if 'schedules' in tables:
            schedule_cols = {col['name'] for col in inspector.get_columns('schedules')}
            schedule_migrations = [
                ('shift_name', 'VARCHAR(50)'),
                ('time_segments', 'JSON'),
                ('work_hours', 'DECIMAL(4,1)'),
                ('is_night', 'BOOLEAN DEFAULT FALSE'),
                ('punctuality_rate', 'DECIMAL(7,4)'),
                ('call_duration', 'DECIMAL(4,1)'),
                ('organize_duration', 'DECIMAL(4,1)'),
                ('utilization_rate', 'DECIMAL(7,4)'),
                ('attendance_rate', 'DECIMAL(7,4)'),
            ]
            for col_name, col_def in schedule_migrations:
                if col_name not in schedule_cols:
                    sql = f"ALTER TABLE schedules ADD COLUMN {col_name} {col_def}"
                    try:
                        db.execute(text(sql))
                        print(f"Added column {col_name} to schedules")
                    except Exception as e:
                        print(f"Failed to add column {col_name}: {e}")

            schedule_type_changes = [
                ('punctuality_rate', 'DECIMAL(7,4)'),
                ('utilization_rate', 'DECIMAL(7,4)'),
                ('attendance_rate', 'DECIMAL(7,4)'),
            ]
            for col_name, col_def in schedule_type_changes:
                if col_name in schedule_cols:
                    try:
                        db.execute(text(f"ALTER TABLE schedules ALTER COLUMN {col_name} TYPE {col_def}"))
                        print(f"Altered schedules.{col_name} to {col_def}")
                    except Exception as e:
                        print(f"Failed to alter {col_name}: {e}")

        if 'shift_types' in tables:
            shift_type_cols = {col['name']: col for col in inspector.get_columns('shift_types')}
            shift_name_col = shift_type_cols.get('shift_name')
            if shift_name_col and str(shift_name_col.get('type')) == 'VARCHAR(20)':
                try:
                    db.execute(text("ALTER TABLE shift_types ALTER COLUMN shift_name TYPE VARCHAR(100)"))
                    print("Altered shift_types.shift_name to VARCHAR(100)")
                except Exception as e:
                    print(f"Failed to alter shift_name column: {e}")

        if 'employees' in tables:
            emp_cols = {col['name'] for col in inspector.get_columns('employees')}
            if 'deleted_at' not in emp_cols:
                try:
                    db.execute(text("ALTER TABLE employees ADD COLUMN deleted_at TIMESTAMP"))
                    print("Added column deleted_at to employees")
                except Exception as e:
                    print(f"Failed to add column deleted_at: {e}")
            if 'hire_date' not in emp_cols:
                try:
                    db.execute(text("ALTER TABLE employees ADD COLUMN hire_date DATE"))
                    print("Added column hire_date to employees")
                except Exception as e:
                    print(f"Failed to add column hire_date: {e}")

        if 'daily_reports' in tables:
            report_cols = {col['name'] for col in inspector.get_columns('daily_reports')}
            if 'segment_details' not in report_cols:
                col_def = 'JSON'
                try:
                    db.execute(text(f"ALTER TABLE daily_reports ADD COLUMN segment_details {col_def}"))
                    print("Added column segment_details to daily_reports")
                except Exception as e:
                    print(f"Failed to add column segment_details: {e}")

        db.commit()
    except Exception as e:
        print(f"Migration error: {e}")
        db.rollback()
    finally:
        db.close()


def _init_default_data():
    from app.models.user import User
    from app.models.role import Role
    from app.core.security import get_password_hash
    from app.core.permissions import get_default_permissions
    import json
    _seed_field_annotations()


def _seed_field_annotations():
    from app.models.field_annotation import FieldAnnotation

    seed = [
        {"report_type": "daily", "field_path": "schedule_date", "field_label": "日期",
         "source": "排班表(schedules)的排班日期", "description": "考勤报表统计的日期"},
        {"report_type": "daily", "field_path": "emp_no", "field_label": "工号",
         "source": "员工表(employees)的员工编号", "description": "员工唯一标识"},
        {"report_type": "daily", "field_path": "name", "field_label": "姓名",
         "source": "员工表(employees)的姓名", "description": "员工姓名"},
        {"report_type": "daily", "field_path": "team", "field_label": "班组",
         "source": "员工表(employees)的所属班组", "description": "员工所属班组"},
        {"report_type": "daily", "field_path": "dept", "field_label": "部门",
         "source": "员工表(employees)的所属部门", "description": "员工所属部门"},
        {"report_type": "daily", "field_path": "schedule_type", "field_label": "排班类型",
         "source": "排班表(schedules)的排班类型", "description": "排班类型（正常班/公休/请假等）"},
        {"report_type": "daily", "field_path": "scheduled_hours", "field_label": "排班工时",
         "source": "排班表(schedules)中班次类型的额定工时",
         "formula": "班次类型配置的工作时长(work_hours)，多时段累加",
         "description": "单位为小时，精确到0.5小时"},
        {"report_type": "daily", "field_path": "scheduled_start", "field_label": "计划开始",
         "source": "排班表(schedules)中班次类型的开始时间", "description": "排班计划规定的上班时间"},
        {"report_type": "daily", "field_path": "scheduled_end", "field_label": "计划结束",
         "source": "排班表(schedules)中班次类型的结束时间", "description": "排班计划规定的下班时间"},
        {"report_type": "daily", "field_path": "actual_checkin", "field_label": "实际签到",
         "source": "员工签到记录(checkins)的签到时间", "description": "当日第一次签到时间"},
        {"report_type": "daily", "field_path": "actual_checkout", "field_label": "实际签退",
         "source": "员工签到记录(checkins)的签退时间", "description": "当日最后一次签退时间"},
        {"report_type": "daily", "field_path": "status", "field_label": "状态",
         "source": "考勤计算逻辑自动判定",
         "formula": "根据排班和签到匹配结果判定：正常/迟到/早退/缺勤/请假/休息",
         "description": "迟到阈值30分钟，早退阈值30分钟"},
        {"report_type": "daily", "field_path": "late_minutes", "field_label": "迟到(分)",
         "source": "签到时间 vs 排班开始时间",
         "formula": "max(0, 实际签到时间 - 排班开始时间)，小于阈值记为0",
         "description": "单位为分钟"},
        {"report_type": "daily", "field_path": "early_minutes", "field_label": "早退(分)",
         "source": "签退时间 vs 排班结束时间",
         "formula": "max(0, 排班结束时间 - 实际签退时间)，小于阈值记为0",
         "description": "单位为分钟"},
        {"report_type": "daily", "field_path": "actual_hours", "field_label": "实际工时",
         "source": "员工签到记录(checkins)的签到/签退时间",
         "formula": "∑(排班时段内签退-签到)，仅计算排班时段内的重叠部分",
         "description": "单位为小时，精确到0.5小时"},
        {"report_type": "daily", "field_path": "overtime_hours", "field_label": "加班",
         "source": "考勤计算逻辑", "formula": "max(0, 实际工时 - 排班工时)",
         "description": "单位为小时，超出排班工时的部分"},

        {"report_type": "monthly", "field_path": "emp_no", "field_label": "工号",
         "source": "员工表(employees)", "description": "员工唯一标识"},
        {"report_type": "monthly", "field_path": "name", "field_label": "姓名",
         "source": "员工表(employees)", "description": "员工姓名"},
        {"report_type": "monthly", "field_path": "team", "field_label": "班组",
         "source": "员工表(employees)", "description": "员工所属班组"},
        {"report_type": "monthly", "field_path": "dept", "field_label": "部门",
         "source": "员工表(employees)", "description": "员工所属部门"},
        {"report_type": "monthly", "field_path": "scheduled_hours", "field_label": "计划工时",
         "source": "每日排班工时(scheduled_hours)的月度汇总",
         "formula": "∑(当月每日排班工时)", "description": "单位为小时"},
        {"report_type": "monthly", "field_path": "actual_hours", "field_label": "实际工时",
         "source": "每日实际工时(actual_hours)的月度汇总",
         "formula": "∑(当月每日实际工时，仅计算排班时段内的重叠工时)"},
        {"report_type": "monthly", "field_path": "overtime_hours", "field_label": "加班",
         "source": "每日加班工时(overtime_hours)的月度汇总",
         "formula": "∑(当月每日加班工时)，每日加班 = max(0, 实际工时 - 排班工时)"},
        {"report_type": "monthly", "field_path": "owed_hours", "field_label": "欠时",
         "source": "排班工时与实际工时的差额",
         "formula": "max(0, 计划工时 - 实际工时 - 加班工时)"},
        {"report_type": "monthly", "field_path": "normal_days", "field_label": "正常",
         "source": "每日考勤状态统计", "formula": "当月状态为正常的次数"},
        {"report_type": "monthly", "field_path": "late_days", "field_label": "迟到",
         "source": "每日考勤状态统计", "formula": "当月状态为迟到的次数"},
        {"report_type": "monthly", "field_path": "early_days", "field_label": "早退",
         "source": "每日考勤状态统计", "formula": "当月状态为早退的次数"},
        {"report_type": "monthly", "field_path": "absent_days", "field_label": "缺勤",
         "source": "每日考勤状态统计", "formula": "当月状态为缺勤的次数"},
        {"report_type": "monthly", "field_path": "leave_days", "field_label": "请假",
         "source": "每日考勤状态统计", "formula": "当月状态为请假的次数"},
        {"report_type": "monthly", "field_path": "timeoff_days", "field_label": "休息",
         "source": "每日考勤状态统计", "formula": "当月状态为公休的次数"},
        {"report_type": "monthly", "field_path": "work_days", "field_label": "出勤天数",
         "source": "每月出勤统计", "formula": "当月出勤天数（不含缺勤/请假/休息）"},

        {"report_type": "workload", "field_path": "account", "field_label": "账号",
         "source": "工作量数据(workloads)", "description": "员工登录账号"},
        {"report_type": "workload", "field_path": "name", "field_label": "姓名",
         "source": "员工表(employees)", "description": "员工姓名"},
        {"report_type": "workload", "field_path": "emp_no", "field_label": "工号",
         "source": "员工表(employees)", "description": "员工唯一标识"},
        {"report_type": "workload", "field_path": "team_desc", "field_label": "班组",
         "source": "员工表(employees)", "description": "员工所属班组"},
        {"report_type": "workload", "field_path": "date_count", "field_label": "天数",
         "source": "工作量数据统计", "description": "统计天数"},
        {"report_type": "workload", "field_path": "总体-签入次数", "field_label": "签入次数",
         "source": "工作量模块(workloads)的原始指标",
         "description": "员工在统计周期内的系统签入次数"},
        {"report_type": "workload", "field_path": "总体-签出次数", "field_label": "签出次数",
         "source": "工作量模块(workloads)的原始指标",
         "description": "员工在统计周期内的系统签出次数"},
        {"report_type": "workload", "field_path": "总体-工作总时长(秒)", "field_label": "工作总时长(秒)",
         "source": "工作量模块(workloads)的原始指标",
         "description": "员工在统计周期内的总工作时长，单位为秒"},
        {"report_type": "workload", "field_path": "总体-工时利用率", "field_label": "工时利用率",
         "source": "工作量模块(workloads)的派生指标",
         "formula": "实际工作时长 / 总签入时长",
         "description": "反映工作时间利用效率，值为百分比"},
        {"report_type": "workload", "field_path": "呼入人工服务-人工服务-通话次数", "field_label": "通话次数",
         "source": "工作量模块(workloads)的原始指标",
         "description": "呼入人工服务接通并处理的电话数量"},
        {"report_type": "workload", "field_path": "呼入人工服务-人工服务-通话总时长(秒)", "field_label": "通话总时长(秒)",
         "source": "工作量模块(workloads)的原始指标",
         "description": "呼入人工服务通话累计时长，单位为秒"},
        {"report_type": "workload", "field_path": "呼入人工服务-人工服务-通话均长(秒)", "field_label": "通话均长(秒)",
         "source": "工作量模块(workloads)的派生指标",
         "formula": "通话总时长 / 通话次数", "description": "每次通话的平均时长，单位为秒"},
        {"report_type": "workload", "field_path": "呼入人工服务-人工服务-服务后整理总时长(秒)", "field_label": "服务后整理总时长(秒)",
         "source": "工作量模块(workloads)的原始指标",
         "description": "通话结束后处理后续工作的累计时长，单位为秒"},
        {"report_type": "workload", "field_path": "呼入人工服务-人工服务-呼入等待应答时长", "field_label": "呼入等待应答时长",
         "source": "工作量模块(workloads)的原始指标",
         "description": "客户呼入后等待客服应答的时长"},
        {"report_type": "workload", "field_path": "人工服务-满意度-满意率", "field_label": "满意率",
         "source": "工作量模块(workloads)的派生指标",
         "formula": "(非常满意量 + 满意量) / (非常满意+满意+一般+不满意+非常不满意)"},
        {"report_type": "workload", "field_path": "呼入人工服务-解决率-解决率", "field_label": "解决率",
         "source": "工作量模块(workloads)的派生指标",
         "formula": "已解决问题数量 / 总接入问题数量"},
        {"report_type": "workload", "field_path": "呼入人工服务-工单-生成总量", "field_label": "提单量",
         "source": "工作量模块(workloads)的原始指标",
         "description": "话务流转生成的工单总数"},
        {"report_type": "workload", "field_path": "呼入人工服务-工单-其中:咨询工单量", "field_label": "咨询工单量",
         "source": "工作量模块(workloads)的原始指标", "description": "咨询类工单的数量"},
        {"report_type": "workload", "field_path": "呼入人工服务-工单-其中:投诉工单", "field_label": "投诉工单",
         "source": "工作量模块(workloads)的原始指标", "description": "投诉类工单的数量"},
        {"report_type": "workload", "field_path": "呼出服务-人工呼出呼叫量", "field_label": "人工呼出呼叫量",
         "source": "工作量模块(workloads)的原始指标",
         "description": "员工主动外呼的电话数量"},
        {"report_type": "workload", "field_path": "呼出服务-通话总时长(秒)", "field_label": "呼出通话总时长(秒)",
         "source": "工作量模块(workloads)的原始指标",
         "description": "外呼通话累计时长，单位为秒"},
        {"report_type": "workload", "field_path": "服务量合计-通话量", "field_label": "通话量",
         "source": "工作量模块(workloads)的派生指标",
         "formula": "呼入通话次数 + 呼出呼叫量"},
        {"report_type": "workload", "field_path": "操作次数及时长-示忙次数", "field_label": "示忙次数",
         "source": "工作量模块(workloads)的原始指标",
         "description": "员工设置示忙状态的次数"},
        {"report_type": "workload", "field_path": "操作次数及时长-休息时长(秒)", "field_label": "休息时长(秒)",
         "source": "工作量模块(workloads)的原始指标",
         "description": "员工在休息状态下的累计时长，单位为秒"},
        {"report_type": "workload", "field_path": "操作次数及时长-呼入-静音次数", "field_label": "静音次数",
         "source": "工作量模块(workloads)的原始指标",
         "description": "通话过程中员工静音操作的次数"},
        {"report_type": "workload", "field_path": "操作次数及时长-整理次数", "field_label": "整理次数",
         "source": "工作量模块(workloads)的原始指标",
         "description": "通话结束后进入整理状态的次数"},
        {"report_type": "workload", "field_path": "呼入人工服务-满意度-非常满意量", "field_label": "非常满意量",
         "source": "工作量模块(workloads)的原始指标", "description": "客户评价为非常满意的数量"},
        {"report_type": "workload", "field_path": "呼入人工服务-满意度-满意量", "field_label": "满意量",
         "source": "工作量模块(workloads)的原始指标", "description": "客户评价为满意的数量"},
        {"report_type": "workload", "field_path": "呼入人工服务-满意度-一般量", "field_label": "一般量",
         "source": "工作量模块(workloads)的原始指标", "description": "客户评价为一般的数量"},
        {"report_type": "workload", "field_path": "呼入人工服务-满意度-不满意量", "field_label": "不满意量",
         "source": "工作量模块(workloads)的原始指标", "description": "客户评价为不满意的数量"},
        {"report_type": "workload", "field_path": "呼入人工服务-满意度-非常不满意量", "field_label": "非常不满意量",
         "source": "工作量模块(workloads)的原始指标", "description": "客户评价为非常不满意的数量"},

        {"report_type": "workload", "field_path": "_ti_dan_lv", "field_label": "提单率",
         "source": "工单量 + 通话量计算",
         "formula": "工单生成总量 / 呼入通话次数",
         "description": "反映客服人员的话务转工单比例"},
        {"report_type": "workload", "field_path": "_call_hourly_rate", "field_label": "接话小时量",
         "source": "通话次数 + 工作时长计算",
         "formula": "呼入通话次数 / (工作总时长(秒) / 3600)"},
        {"report_type": "workload", "field_path": "_call_salary", "field_label": "接话绩效(预测)",
         "source": "绩效配置(salary_config)中的单价系数",
         "formula": "接话小时量 × 接话绩效单价系数", "description": "预测值，仅供参考"},
        {"report_type": "workload", "field_path": "_sat_salary", "field_label": "满意度绩效(预测)",
         "source": "绩效配置中的满意度单价系数",
         "formula": "满意度达标情况 × 满意度绩效单价系数", "description": "预测值，仅供参考"},
        {"report_type": "workload", "field_path": "_total_salary", "field_label": "合计绩效(预测)",
         "source": "接话绩效 + 满意度绩效",
         "formula": "接话绩效(预测) + 满意度绩效(预测)", "description": "预测值，仅供参考"},
        {"report_type": "workload", "field_path": "_sat_diff", "field_label": "满意度差额",
         "source": "绩效配置(salary_config)满意度差额系数",
         "formula": "(E+F+G+H+I)×coeff_a - (E+F)×coeff_b",
         "description": "E=非常满意 F=满意 G=一般 H=不满意 I=非常不满意"},

        {"report_type": "checkin", "field_path": "emp_no", "field_label": "账号",
         "source": "员工表(employees)", "description": "员工工号"},
        {"report_type": "checkin", "field_path": "name", "field_label": "用户名",
         "source": "员工表(employees)", "description": "员工姓名"},
        {"report_type": "checkin", "field_path": "dept", "field_label": "所属部门",
         "source": "员工表(employees)", "description": "员工所属部门"},
        {"report_type": "checkin", "field_path": "team", "field_label": "班组",
         "source": "员工表(employees)", "description": "员工所属班组"},
        {"report_type": "checkin", "field_path": "checkin_count", "field_label": "签入次数",
         "source": "签到记录(checkins)统计", "description": "统计周期内的签到次数"},
        {"report_type": "checkin", "field_path": "total_hours", "field_label": "工作时长",
         "source": "签到记录(checkins)的签入/签出时间",
         "formula": "∑(签退时间 - 签到时间)"},
        {"report_type": "checkin", "field_path": "hour_status_text", "field_label": "工时状态",
         "source": "根据工作时长与工时阈值对比判定",
         "formula": "超长/过短/正常，阈值在工时预警设置中配置"},
        {"report_type": "checkin", "field_path": "avg_punctuality_rate", "field_label": "遵时率",
         "source": "排班导入数据中的扩展指标",
         "description": "反映员工遵守排班时间的比例"},
        {"report_type": "checkin", "field_path": "total_call_duration", "field_label": "通话时长",
         "source": "排班导入数据中的扩展指标", "description": "通话累计时长，单位为小时"},
        {"report_type": "checkin", "field_path": "total_organize_duration", "field_label": "整理时长",
         "source": "排班导入数据中的扩展指标", "description": "服务后整理累计时长，单位为小时"},
        {"report_type": "checkin", "field_path": "avg_utilization_rate", "field_label": "工时利用率",
         "source": "排班导入数据中的扩展指标",
         "formula": "(通话时长 + 整理时长) / 工作时长"},
        {"report_type": "checkin", "field_path": "avg_attendance_rate", "field_label": "班表出勤率",
         "source": "排班导入数据中的扩展指标",
         "description": "反映员工按排班出勤的比例"},

        {"report_type": "efficiency", "field_path": "attendance_rate", "field_label": "出勤率",
         "source": "考勤日报表统计", "formula": "出勤天数 / 应出勤天数"},
        {"report_type": "efficiency", "field_path": "efficiency_rate", "field_label": "工时效率",
         "source": "考勤日报表统计", "formula": "实际工时 / 计划工时"},
        {"report_type": "efficiency", "field_path": "scheduled_hours", "field_label": "计划工时",
         "source": "排班表月度汇总"},
        {"report_type": "efficiency", "field_path": "actual_hours", "field_label": "实际工时",
         "source": "签到记录月度汇总"},
        {"report_type": "efficiency", "field_path": "overtime_hours", "field_label": "加班",
         "source": "考勤计算逻辑", "formula": "max(0, 实际工时 - 计划工时)"},
        {"report_type": "efficiency", "field_path": "work_days", "field_label": "出勤天数",
         "source": "考勤日报表统计"},
        {"report_type": "efficiency", "field_path": "warning_type", "field_label": "预警类型",
         "source": "系统根据阈值自动判定",
         "description": "如低出勤率、低工时效率、高迟到次数等"},
        {"report_type": "efficiency", "field_path": "year_month", "field_label": "月份",
         "source": "考勤报表统计周期", "description": "格式 YYYY-MM"},

        {"report_type": "ranking", "field_path": "emp_count", "field_label": "人数",
         "source": "员工表(employees)按班组统计", "description": "班组员工总数"},
        {"report_type": "ranking", "field_path": "total_scheduled", "field_label": "计划工时",
         "source": "班组排班工时汇总", "description": "单位为小时"},
        {"report_type": "ranking", "field_path": "total_actual", "field_label": "实际工时",
         "source": "班组签到工时汇总", "description": "单位为小时"},
        {"report_type": "ranking", "field_path": "total_overtime", "field_label": "加班工时",
         "source": "班组加班工时汇总", "description": "单位为小时"},
        {"report_type": "ranking", "field_path": "avg_attendance", "field_label": "平均出勤率",
         "source": "班组出勤率平均值",
         "formula": "∑(个人出勤率) / 班组人数"},
        {"report_type": "ranking", "field_path": "late_count", "field_label": "迟到次数",
         "source": "班组迟到统计汇总", "description": "单位为次"},
        {"report_type": "ranking", "field_path": "absent_count", "field_label": "缺勤次数",
         "source": "班组缺勤统计汇总", "description": "单位为次"},
    ]

    db = SessionLocal()
    try:
        existing = db.query(FieldAnnotation).count()
        if existing == 0:
            for item in seed:
                db.add(FieldAnnotation(**item))
            db.commit()
            print(f"已插入 {len(seed)} 条字段批注")
    except Exception as e:
        db.rollback()
        print(f"字段批注初始化失败: {e}")
    finally:
        db.close()