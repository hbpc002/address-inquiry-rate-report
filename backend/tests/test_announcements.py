import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@localhost:5432/schedule_test')

from fastapi.testclient import TestClient
from app.models.database import Base, engine, SessionLocal, init_db
from app.models.announcement import Announcement
from app.models.employee import Employee
from app.models.checkin import Checkin
from app.models.daily_report import DailyReport
from app.models.schedule import Schedule
from app.models.shift_type import ShiftType
from app.main import app
from app.core.security import get_current_user
from sqlalchemy import text
from datetime import date, datetime, time


_admin_user = {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "is_system": True,
    "permissions": "{}",
}


def override_get_current_user():
    return _admin_user


app.dependency_overrides[get_current_user] = override_get_current_user
client = TestClient(app)


def setup_module():
    Base.metadata.drop_all(bind=engine)
    init_db()


def teardown_module():
    app.dependency_overrides.clear()


def _clean_announcements(db):
    db.execute(text("DELETE FROM announcements"))
    db.commit()


class TestAnnouncementAPI:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_announcements(db)
        finally:
            db.close()

    def test_create_changelog(self):
        resp = client.post("/api/announcements", json={
            "type": "更新日志",
            "title": "v1.2.0",
            "content": "新增仪表盘数据更新日期显示 / 新增公告功能",
            "is_active": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "更新日志"
        assert data["title"] == "v1.2.0"

    def test_get_changelog(self):
        client.post("/api/announcements", json={
            "type": "更新日志", "title": "v1.0", "content": "初始版本", "is_active": True,
        })
        client.post("/api/announcements", json={
            "type": "更新日志", "title": "v1.1", "content": "新增功能", "is_active": True,
        })
        resp = client.get("/api/announcements/changelog?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["title"] == "v1.1"

    def test_changelog_excludes_announcement_type(self):
        client.post("/api/announcements", json={
            "type": "更新日志", "title": "日志", "content": "日志内容", "is_active": True,
        })
        client.post("/api/announcements", json={
            "type": "更新日志", "title": "日志2", "content": "其他", "is_active": True,
        })
        resp = client.get("/api/announcements/changelog")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_list_announcements(self):
        client.post("/api/announcements", json={
            "type": "更新日志", "title": "日志1", "content": "内容1", "is_active": True,
        })
        client.post("/api/announcements", json={
            "type": "更新日志", "title": "日志2", "content": "日志内容", "is_active": True,
        })
        resp = client.get("/api/announcements")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_announcements_filter_type(self):
        client.post("/api/announcements", json={
            "type": "更新日志", "title": "日志1", "content": "内容1", "is_active": True,
        })
        client.post("/api/announcements", json={
            "type": "更新日志", "title": "日志2", "content": "内容", "is_active": True,
        })
        resp = client.get("/api/announcements?type=更新日志")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_update_announcement(self):
        create_resp = client.post("/api/announcements", json={
            "type": "公告", "title": "原标题", "content": "原内容", "is_active": True,
        })
        aid = create_resp.json()["id"]

        resp = client.put(f"/api/announcements/{aid}", json={
            "title": "新标题",
            "content": "新内容",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "新标题"
        assert data["content"] == "新内容"

    def test_update_announcement_not_found(self):
        resp = client.put("/api/announcements/99999", json={"title": "不存在"})
        assert resp.status_code == 404

    def test_delete_announcement(self):
        create_resp = client.post("/api/announcements", json={
            "type": "公告", "title": "待删除", "content": "内容", "is_active": True,
        })
        aid = create_resp.json()["id"]

        resp = client.delete(f"/api/announcements/{aid}")
        assert resp.status_code == 200

        resp = client.get("/api/announcements")
        assert resp.json()["total"] == 0

    def test_delete_announcement_not_found(self):
        resp = client.delete("/api/announcements/99999")
        assert resp.status_code == 404

    def test_stats_returns_latest_data_date(self):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "latest_data_date" in data
        assert "employee_count" in data

    def test_create_announcement_updates_created_at(self):
        import time
        resp1 = client.post("/api/announcements", json={
            "type": "更新日志", "title": "第一条", "content": "内容", "is_active": True,
        })
        time.sleep(0.01)
        resp2 = client.post("/api/announcements", json={
            "type": "更新日志", "title": "第二条", "content": "内容", "is_active": True,
        })
        assert resp2.json()["created_at"] > resp1.json()["created_at"]


class TestDashboardStats:

    def setup_method(self):
        db = SessionLocal()
        try:
            for table in ["announcements", "schedules", "checkins", "daily_reports", "shift_types", "employees"]:
                db.execute(text(f"DELETE FROM {table}"))
            db.commit()
        finally:
            db.close()

    def _seed_employee(self, db, emp_no="E001", name="测试员工", team="一班1组", dept="热线运营组", status="在职"):
        emp = Employee(emp_no=emp_no, name=name, team=team, dept=dept, role="组员", status=status)
        db.add(emp)
        db.flush()
        return emp

    def _seed_checkin(self, db, emp_no, checkin_date):
        ck = Checkin(
            emp_no=emp_no,
            name="测试员工",
            checkin_time=datetime.combine(checkin_date, time(8, 0)),
            checkout_time=datetime.combine(checkin_date, time(17, 0)),
            dept="热线运营组",
            import_batch="test-batch",
        )
        db.add(ck)
        db.flush()
        return ck

    def _seed_report(self, db, emp_id, schedule_date, status, actual_hours=8.0):
        report = DailyReport(
            emp_id=emp_id,
            schedule_date=schedule_date,
            status=status,
            actual_hours=actual_hours,
            scheduled_hours=8.0,
            late_minutes=5 if status == "迟到" else 0,
            early_minutes=5 if status == "早退" else 0,
        )
        db.add(report)
        db.flush()
        return report

    def test_stats_no_data_returns_none_date(self):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["latest_data_date"] is None
        assert data["employee_count"] == 0
        assert data["latest_attendance"] == 0
        assert data["latest_late"] == 0
        assert data["latest_absent"] == 0
        assert data["latest_leave"] == 0
        assert data["latest_timeoff"] == 0

    def test_stats_returns_latest_date_from_checkins(self):
        db = SessionLocal()
        try:
            emp = self._seed_employee(db)
            self._seed_checkin(db, emp.emp_no, date(2026, 5, 28))
            self._seed_checkin(db, emp.emp_no, date(2026, 5, 29))
            self._seed_report(db, emp.id, date(2026, 5, 29), "正常")
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["latest_data_date"] == "2026-05-29"
        assert data["employee_count"] == 1

    def test_stats_counts_attendance_by_status(self):
        db = SessionLocal()
        try:
            e1 = self._seed_employee(db, "E001", "员工1")
            e2 = self._seed_employee(db, "E002", "员工2")
            e3 = self._seed_employee(db, "E003", "员工3")
            e4 = self._seed_employee(db, "E004", "员工4")
            e5 = self._seed_employee(db, "E005", "员工5")
            latest = date(2026, 5, 30)
            for e in [e1, e2, e3, e4, e5]:
                self._seed_checkin(db, e.emp_no, latest)
            self._seed_report(db, e1.id, latest, "正常")
            self._seed_report(db, e2.id, latest, "迟到")
            self._seed_report(db, e3.id, latest, "缺勤")
            self._seed_report(db, e4.id, latest, "请假")
            self._seed_report(db, e5.id, latest, "公休")
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/stats")
        data = resp.json()
        assert data["latest_data_date"] == "2026-05-30"
        assert data["latest_attendance"] == 1
        assert data["latest_late"] == 1
        assert data["latest_absent"] == 1
        assert data["latest_leave"] == 1
        assert data["latest_timeoff"] == 1

    def test_stats_only_counts_latest_date(self):
        db = SessionLocal()
        try:
            emp = self._seed_employee(db)
            self._seed_checkin(db, emp.emp_no, date(2026, 5, 29))
            self._seed_checkin(db, emp.emp_no, date(2026, 5, 30))
            self._seed_report(db, emp.id, date(2026, 5, 30), "迟到")
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/stats")
        data = resp.json()
        assert data["latest_data_date"] == "2026-05-30"
        assert data["latest_attendance"] == 0
        assert data["latest_late"] == 1

    def test_stats_date_from_checkin_not_report(self):
        db = SessionLocal()
        try:
            emp = self._seed_employee(db)
            self._seed_checkin(db, emp.emp_no, date(2026, 6, 1))
            self._seed_report(db, emp.id, date(2026, 5, 31), "正常")
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/stats")
        data = resp.json()
        assert data["latest_data_date"] == "2026-06-01"

    def test_stats_employee_count_excludes_inactive(self):
        db = SessionLocal()
        try:
            self._seed_employee(db, "E001", "在职员工")
            self._seed_employee(db, "E002", "离职员工", status="离职")
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/stats")
        data = resp.json()
        assert data["employee_count"] == 1

    def test_stats_monthly_counts_current_month(self):
        db = SessionLocal()
        try:
            emp = self._seed_employee(db)
            today = date.today()
            self._seed_report(db, emp.id, today, "正常", actual_hours=8.0)
            self._seed_report(db, emp.id, today, "迟到", actual_hours=7.5)
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/stats")
        data = resp.json()
        assert data["monthly_normal_days"] == 1
        assert data["monthly_late_days"] == 1
        assert data["monthly_actual_hours"] > 0

    def test_daily_trend_returns_daily_breakdown(self):
        db = SessionLocal()
        try:
            emp = self._seed_employee(db)
            d1 = date(2026, 5, 15)
            d2 = date(2026, 5, 16)
            self._seed_report(db, emp.id, d1, "正常", actual_hours=9.0)
            self._seed_report(db, emp.id, d2, "迟到", actual_hours=7.5)
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/daily-trend?year_month=2026-05")
        assert resp.status_code == 200
        data = resp.json()
        dates = [d["date"] for d in data]
        assert "2026-05-15" in dates
        assert "2026-05-16" in dates

    def test_daily_trend_hour_buckets(self):
        db = SessionLocal()
        try:
            emp = self._seed_employee(db)
            d = date(2026, 5, 20)
            self._seed_report(db, emp.id, d, "正常", actual_hours=10.0)
            self._seed_report(db, emp.id, d, "正常", actual_hours=8.5)
            self._seed_report(db, emp.id, d, "正常", actual_hours=7.2)
            self._seed_report(db, emp.id, d, "正常", actual_hours=4.0)
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/daily-trend?year_month=2026-05")
        data = resp.json()
        day = next(d for d in data if d["date"] == "2026-05-20")
        assert day["long_hours"] == 1
        assert day["normal_hours_count"] == 1
        assert day["slight_short"] == 1
        assert day["short_hours"] == 1

    def test_consecutive_overtime_distribution(self):
        db = SessionLocal()
        try:
            e1 = self._seed_employee(db, "E001", "员工1")
            e2 = self._seed_employee(db, "E002", "员工2")
            for emp in [e1, e2]:
                for day_offset in range(3):
                    d = date(2026, 5, 10 + day_offset)
                    self._seed_report(db, emp.id, d, "正常", actual_hours=10.0)
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/consecutive-overtime?year_month=2026-05")
        assert resp.status_code == 200
        data = resp.json()
        total = sum(item["count"] for item in data)
        assert total == 2

    def test_shift_distribution_returns_counts(self):
        db = SessionLocal()
        try:
            shift = ShiftType(
                shift_name="早班",
                time_segments=[{"start": "08:00", "end": "12:00"}],
                work_hours=8.0,
                color="#409EFF",
            )
            db.add(shift)
            db.flush()

            emp = self._seed_employee(db)
            d = date(2026, 5, 15)
            sched = Schedule(
                emp_id=emp.id, schedule_date=d, shift_type_id=shift.id,
                shift_name="早班", work_hours=8.0,
            )
            db.add(sched)
            db.commit()
        finally:
            db.close()

        resp = client.get("/api/shift-distribution?year_month=2026-05")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["shift_name"] == "早班"
        assert data[0]["count"] == 1

    def test_consecutive_overtime_no_data(self):
        resp = client.get("/api/consecutive-overtime?year_month=2026-05")
        assert resp.status_code == 200
        data = resp.json()
        for item in data:
            assert item["count"] == 0

    def test_daily_trend_empty_month(self):
        resp = client.get("/api/daily-trend?year_month=2026-05")
        assert resp.status_code == 200
        assert resp.json() == []
