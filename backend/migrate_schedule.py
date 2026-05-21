"""数据库迁移脚本：为 schedules 表添加班次信息字段"""
import sys
sys.path.insert(0, '.')

import sqlite3


def run_migration():
    conn = sqlite3.connect('/workspace/schedule-report-system/backend/schedule.db')
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(schedules)")
    existing_cols = {col[1] for col in cursor.fetchall()}

    migrations = [
        ("shift_name", "VARCHAR(50)"),
        ("time_segments", "TEXT"),
        ("work_hours", "DECIMAL(4,1)"),
        ("is_night", "BOOLEAN DEFAULT 0"),
    ]

    for col_name, col_type in migrations:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE schedules ADD COLUMN {col_name} {col_type}")
            print(f"  + 添加列 {col_name} ({col_type})")

    conn.commit()
    conn.close()
    print("迁移完成")


if __name__ == "__main__":
    run_migration()