#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

import pandas as pd
from datetime import datetime
from app.models.database import SessionLocal
from app.models.employee import Employee
from app.models.schedule import Schedule
from app.models.shift_type import ShiftType
from app.models.checkin import Checkin
import uuid

def import_employees_from_excel():
    """从排班表Excel导入员工"""
    db = SessionLocal()
    try:
        df = pd.read_excel('/workspace/file/2026年4月热线班表排班20260414更新（调度版）.xlsx')

        # 分析列结构
        # 日期在第0列，姓名在第1列，从第2列开始是日期
        # 结构: 日期, Unnamed:1, 20260401, 20260402, ...

        employees = set()
        for idx, row in df.iterrows():
            name = row.get('Unnamed: 1')
            if pd.isna(name) or idx == 0:  # 跳过标题行
                continue

            # 班组从日期列推断
            team = str(row.get('日期', ''))
            if pd.isna(team):
                team = '未分组'

            employees.add((name, team))

        print(f"=== 导入员工: {len(employees)} 人 ===")
        count = 0
        for name, team in employees:
            emp_no = f"E{hash(name) % 100000:05d}"
            existing = db.query(Employee).filter(Employee.name == name).first()
            if existing:
                continue

            emp = Employee(
                emp_no=emp_no,
                name=name,
                team=team,
                dept='客服中心',
                role='组员',
                status='在职'
            )
            db.add(emp)
            count += 1
            print(f"  添加: {name} - {team}")

        db.commit()
        print(f"共添加 {count} 名员工")
    finally:
        db.close()


def import_schedules_from_excel():
    """从排班表Excel导入排班"""
    db = SessionLocal()
    try:
        df = pd.read_excel('/workspace/file/2026年4月热线班表排班20260414更新（调度版）.xlsx')

        # 获取所有员工
        employees = {e.name: e for e in db.query(Employee).all()}

        # 获取班次映射
        shift_map = {s.shift_name: s for s in db.query(ShiftType).all()}

        # 解析日期列
        date_columns = [c for c in df.columns if str(c).startswith('2026')]

        print(f"=== 导入排班: {len(date_columns)} 天 ===")

        for col in date_columns[:3]:  # 导入前3天测试
            schedule_date = datetime.strptime(str(col), '%Y%m%d').date()
            print(f"  日期: {schedule_date}")

            for idx, row in df.iterrows():
                if idx == 0:  # 跳过标题行
                    continue

                name = row.get('Unnamed: 1')
                if pd.isna(name):
                    continue

                shift_name = row.get(col)
                if pd.isna(shift_name):
                    continue

                shift_name = str(shift_name).strip()

                # 匹配班次
                shift_type = None
                for st in shift_map.values():
                    if st.shift_name in shift_name or shift_name in st.shift_name:
                        shift_type = st
                        break

                if not shift_type:
                    # 尝试匹配
                    if '行政' in shift_name:
                        shift_type = shift_map.get('行政班')
                    elif '中班' in shift_name:
                        shift_type = shift_map.get('中班')
                    elif '早班' in shift_name:
                        shift_type = shift_map.get('早班')
                    elif '晚班' in shift_name:
                        shift_type = shift_map.get('晚班')

                emp = employees.get(name)
                if not emp:
                    continue

                existing = db.query(Schedule).filter(
                    Schedule.emp_id == emp.id,
                    Schedule.schedule_date == schedule_date
                ).first()

                if existing:
                    continue

                if shift_type:
                    schedule = Schedule(
                        emp_id=emp.id,
                        schedule_date=schedule_date,
                        shift_type_id=shift_type.id,
                        schedule_type='正常'
                    )
                    db.add(schedule)
                    print(f"    {name}: {shift_type.shift_name}")

        db.commit()
        print("排班导入完成")
    finally:
        db.close()


def import_checkins_from_csv():
    """从CSV导入签到记录"""
    db = SessionLocal()
    try:
        df = pd.read_csv('/workspace/file/签入签出查询_KF77100064_20260414160757697.csv', encoding='gbk')

        batch = str(uuid.uuid4())[:8]
        print(f"=== 导入签到记录: {len(df)} 条 ===")

        count = 0
        for _, row in df.iterrows():
            emp_no = str(row.get('账号', '')).strip()
            name = str(row.get('用户名', '')).strip()
            checkin_time_str = str(row.get('签入时间', '')).strip()
            checkout_time_str = str(row.get('签出时间', '')).strip()

            if not emp_no or not checkin_time_str:
                continue

            try:
                checkin_time = datetime.strptime(checkin_time_str, '%Y-%m-%d %H:%M:%S')
                checkout_time = None
                if checkout_time_str and checkout_time_str != 'nan':
                    try:
                        checkout_time = datetime.strptime(checkout_time_str, '%Y-%m-%d %H:%M:%S')
                    except:
                        pass

                device_no = str(row.get('签入分机', '')).strip()
                if device_no.startswith('='):
                    device_no = device_no[2:-1]

                dept = str(row.get('所属部门全路径', '')).strip()

                checkin = Checkin(
                    emp_no=emp_no,
                    name=name,
                    checkin_time=checkin_time,
                    checkout_time=checkout_time,
                    device_no=device_no,
                    dept=dept,
                    import_batch=batch
                )
                db.add(checkin)
                count += 1
                if count <= 10:
                    print(f"  {emp_no} {name}: {checkin_time}")
            except Exception as e:
                continue

        db.commit()
        print(f"共导入 {count} 条签到记录 (批次: {batch})")
    finally:
        db.close()


if __name__ == '__main__':
    print("=== 导入员工数据 ===")
    import_employees_from_excel()

    print("\n=== 导入排班数据 ===")
    import_schedules_from_excel()

    print("\n=== 导入签到记录 ===")
    import_checkins_from_csv()

    print("\n=== 导入完成 ===")