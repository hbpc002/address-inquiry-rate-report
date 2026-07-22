"""Seed field annotations for reports."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("DATABASE_URL", os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:admin123%40kf@localhost:5432/schedule_dev"
))

from app.models.database import SessionLocal
from app.models.field_annotation import FieldAnnotation

SEED_DATA = [
    # === Daily Report ===
    {"report_type": "daily", "field_path": "scheduled_hours", "field_label": "排班工时",
     "source": "排班表(schedules)中班次类型的额定工时",
     "formula": "班次类型配置的工作时长(work_hours)，多时段累加",
     "description": "单位为小时，精确到0.5小时", "sort_order": 1},
    {"report_type": "daily", "field_path": "actual_hours", "field_label": "实际工时",
     "source": "员工签到记录(checkins)的签到/签退时间",
     "formula": "∑(排班时段内签到-签退的重叠工时)，仅计算排班时段内的重叠部分",
     "description": "单位为小时，精确到0.5小时", "sort_order": 2},
    {"report_type": "daily", "field_path": "actual_checkin", "field_label": "实际签到",
     "source": "员工签到记录(checkins)的签到时间",
     "formula": "当日签到记录中最早的一次签到时间",
     "description": "按当日实际签到时间展示", "sort_order": 3},
    {"report_type": "daily", "field_path": "actual_checkout", "field_label": "实际签退",
     "source": "员工签到记录(checkins)的签退时间",
     "formula": "当日签到记录中最晚的一次签退时间",
     "description": "按当日实际签退时间展示", "sort_order": 4},
    {"report_type": "daily", "field_path": "status", "field_label": "状态",
     "source": "考勤计算逻辑自动判定",
     "formula": "根据排班和签到匹配结果判定：正常/迟到/早退/缺勤/请假/休息",
     "description": "迟到阈值为30分钟，早退阈值为30分钟", "sort_order": 5},
    {"report_type": "daily", "field_path": "late_minutes", "field_label": "迟到(分)",
     "source": "签到时间 vs 排班开始时间",
     "formula": "max(0, 实际签到时间 - 排班开始时间)，小于阈值记为0",
     "description": "单位为分钟", "sort_order": 6},
    {"report_type": "daily", "field_path": "early_minutes", "field_label": "早退(分)",
     "source": "签退时间 vs 排班结束时间",
     "formula": "max(0, 排班结束时间 - 实际签退时间)，小于阈值记为0",
     "description": "单位为分钟", "sort_order": 7},
    {"report_type": "daily", "field_path": "overtime_hours", "field_label": "加班",
     "source": "考勤计算逻辑",
     "formula": "max(0, 实际工时 - 排班工时)",
     "description": "单位为小时，超出排班工时的部分", "sort_order": 8},

    # === Monthly Summary ===
    {"report_type": "monthly", "field_path": "scheduled_hours", "field_label": "计划工时",
     "source": "每日排班工时(scheduled_hours)的月度汇总",
     "formula": "∑(当月每日排班工时)",
     "description": "单位为小时", "sort_order": 10},
    {"report_type": "monthly", "field_path": "actual_hours", "field_label": "实际工时",
     "source": "每日实际工时(actual_hours)的月度汇总",
     "formula": "∑(当月每日实际工时，仅计算排班时段内的重叠工时)",
     "description": "单位为小时", "sort_order": 11},
    {"report_type": "monthly", "field_path": "overtime_hours", "field_label": "加班",
     "source": "每日加班工时(overtime_hours)的月度汇总",
     "formula": "∑(当月每日加班工时)，其中每日加班 = max(0, 实际工时 - 排班工时)",
     "description": "单位为小时", "sort_order": 12},
    {"report_type": "monthly", "field_path": "owed_hours", "field_label": "欠时",
     "source": "排班工时与实际工时的差额",
     "formula": "max(0, 计划工时 - 实际工时 - 加班工时)",
     "description": "单位为小时", "sort_order": 13},
    {"report_type": "monthly", "field_path": "normal_days", "field_label": "正常",
     "source": "每日考勤状态统计",
     "formula": "当月状态为"正常"的天数",
     "description": "单位为天", "sort_order": 14},
    {"report_type": "monthly", "field_path": "late_days", "field_label": "迟到",
     "source": "每日考勤状态统计",
     "formula": "当月状态为"迟到"的天数",
     "description": "单位为天", "sort_order": 15},
    {"report_type": "monthly", "field_path": "early_days", "field_label": "早退",
     "source": "每日考勤状态统计",
     "formula": "当月状态为"早退"的天数",
     "description": "单位为天", "sort_order": 16},
    {"report_type": "monthly", "field_path": "absent_days", "field_label": "缺勤",
     "source": "每日考勤状态统计",
     "formula": "当月状态为"缺勤"的天数",
     "description": "单位为天", "sort_order": 17},
    {"report_type": "monthly", "field_path": "leave_days", "field_label": "请假",
     "source": "每日考勤状态统计",
     "formula": "当月状态为"请假"的天数",
     "description": "单位为天", "sort_order": 18},
    {"report_type": "monthly", "field_path": "timeoff_days", "field_label": "休息",
     "source": "每日考勤状态统计",
     "formula": "当月状态为"公休"的天数",
     "description": "单位为天", "sort_order": 19},

    # === Workload Report ===
    {"report_type": "workload", "field_path": "_ti_dan_lv", "field_label": "提单率",
     "source": "工作量模块(workloads)中的工单量和通话量",
     "formula": "工单生成总量 / 呼入通话次数",
     "description": "反映客服人员的话务转工单比例", "sort_order": 20},
    {"report_type": "workload", "field_path": "_call_hourly_rate", "field_label": "接话小时量",
     "source": "工作量模块中的通话次数和工作时长",
     "formula": "呼入通话次数 / 工作总时长(小时)",
     "description": "反映每工作小时的接话效率", "sort_order": 21},
    {"report_type": "workload", "field_path": "_call_salary", "field_label": "接话绩效(预测)",
     "source": "绩效配置(salary_config)中的单价系数",
     "formula": "接话小时量 × 接话绩效单价系数",
     "description": "预测值，仅供参考", "sort_order": 22},
    {"report_type": "workload", "field_path": "_sat_salary", "field_label": "满意度绩效(预测)",
     "source": "绩效配置中的满意度单价系数",
     "formula": "满意度达成情况 × 满意度绩效单价系数",
     "description": "预测值，仅供参考", "sort_order": 23},
    {"report_type": "workload", "field_path": "_total_salary", "field_label": "合计绩效(预测)",
     "source": "接话绩效与满意度绩效之和",
     "formula": "接话绩效(预测) + 满意度绩效(预测)",
     "description": "预测值，仅供参考", "sort_order": 24},
]


def seed():
    db = SessionLocal()
    try:
        existing = db.query(FieldAnnotation).count()
        if existing > 0:
            print(f"字段批注已存在 {existing} 条，跳过种子数据")
            return

        for item in SEED_DATA:
            annotation = FieldAnnotation(**item)
            db.add(annotation)
        db.commit()
        print(f"已插入 {len(SEED_DATA)} 条字段批注数据")
    except Exception as e:
        db.rollback()
        print(f"种子数据写入失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
