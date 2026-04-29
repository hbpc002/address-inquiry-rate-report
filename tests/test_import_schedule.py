import sys
import io
import json
import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'backend'
sys.path.insert(0, str(BASE))

from app.models.database import SessionLocal, engine, Base
from app.models.employee import Employee
from app.models.schedule import Schedule
from app.models.shift_type import ShiftType


def test_shift_types_schema():
    """测试 shift_types 表结构是否正确（time_segments 列）"""
    # 直接连接实际的数据库文件
    conn = sqlite3.connect('/workspace/schedule-report-system/backend/schedule.db')
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(shift_types)")
    cols = {col[1]: col[2] for col in cursor.fetchall()}
    conn.close()
    
    # 检查 time_segments 列存在
    assert 'time_segments' in cols, f"shift_types表缺少time_segments列，现有列: {list(cols.keys())}"
    print("✓ shift_types 表结构正确")


def test_import_schedule_excel():
    """测试排班导入逻辑"""
    # 读取排班文件
    schedule_file = Path('/workspace/file/2026年4月热线班表排班20260414更新（调度版）.xlsx')
    
    if not schedule_file.exists():
        print(f"跳过: 排班文件不存在")
        return
    
    with open(schedule_file, 'rb') as f:
        contents = f.read()
    
    if not contents:
        print("失败: 文件为空")
        return
    
    try:
        xlsx = pd.ExcelFile(io.BytesIO(contents))
        sheet_names = xlsx.sheet_names
    except Exception:
        xlsx = pd.ExcelFile(io.BytesIO(contents), engine='openpyxl')
        sheet_names = xlsx.sheet_names
    
    if not sheet_names:
        print("失败: 文件中没有sheet")
        return
    
    valid_sheets = [sn for sn in sheet_names 
                 if not any(kw in sn for kw in ['工时', '人员分组', '人员'])
                 and any(kw in sn for kw in ['组长', '组员', '新人'])]
    
    if not valid_sheets:
        print(f"失败: 没有有效的sheet，现有: {sheet_names}")
        return
    
    print(f"✓ 有效sheets: {valid_sheets}")
    
    # 统计人数
    total_employees = 0
    for sheet_name in valid_sheets:
        df = pd.read_excel(xlsx, sheet_name=sheet_name)
        for idx, row in df.iterrows():
            if idx == 0:
                continue
            col_b = row.get('Unnamed: 1') or row.get('姓名')
            if pd.isna(col_b):
                continue
            col_b = str(col_b).strip()
            if col_b and col_b not in ['日期', '序号', '班组', '姓名']:
                total_employees += 1
    
    print(f"✓ 员工总数: {total_employees}")


if __name__ == '__main__':
    test_shift_types_schema()
    test_import_schedule_excel()