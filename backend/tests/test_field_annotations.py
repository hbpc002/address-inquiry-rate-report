import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@localhost:5432/schedule_test')

from app.models.database import Base, engine, SessionLocal, init_db
from app.models.field_annotation import FieldAnnotation
from sqlalchemy import text


def setup_module():
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception:
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.commit()
    init_db()


def get_admin_token():
    return "test-admin-token"


def test_create_field_annotation():
    db = SessionLocal()
    try:
        annotation = FieldAnnotation(
            report_type="daily",
            field_path="actual_hours",
            field_label="实际工时",
            source="签到记录",
            formula="签退-签到",
            description="仅计算排班时段内的重叠工时",
            sort_order=1,
        )
        db.add(annotation)
        db.commit()
        db.refresh(annotation)

        assert annotation.id is not None
        assert annotation.report_type == "daily"
        assert annotation.field_path == "actual_hours"
        assert annotation.field_label == "实际工时"
        assert annotation.source == "签到记录"
        assert annotation.formula == "签退-签到"
        assert annotation.description == "仅计算排班时段内的重叠工时"
        assert annotation.sort_order == 1
    finally:
        db.close()


def test_query_by_report_type():
    db = SessionLocal()
    try:
        results = db.query(FieldAnnotation).filter(
            FieldAnnotation.report_type == "daily"
        ).all()
        assert len(results) >= 1
        for r in results:
            assert r.report_type == "daily"
    finally:
        db.close()


def test_update_field_annotation():
    db = SessionLocal()
    try:
        annotation = db.query(FieldAnnotation).filter(
            FieldAnnotation.field_path == "actual_hours"
        ).first()
        assert annotation is not None

        annotation.source = "员工签到记录"
        annotation.formula = "∑(签退时间 - 签到时间)，仅计算排班时段重叠部分"
        db.commit()

        updated = db.query(FieldAnnotation).filter(
            FieldAnnotation.id == annotation.id
        ).first()
        assert updated.source == "员工签到记录"
        assert "重叠" in updated.formula
    finally:
        db.close()


def test_delete_field_annotation():
    db = SessionLocal()
    try:
        annotation = FieldAnnotation(
            report_type="monthly",
            field_path="test_delete",
            field_label="测试删除",
            sort_order=99,
        )
        db.add(annotation)
        db.commit()
        db.refresh(annotation)
        ann_id = annotation.id

        db.delete(annotation)
        db.commit()

        deleted = db.query(FieldAnnotation).filter(
            FieldAnnotation.id == ann_id
        ).first()
        assert deleted is None
    finally:
        db.close()


def test_multiple_report_types():
    db = SessionLocal()
    try:
        types = ["daily", "monthly", "workload", "checkin", "efficiency"]
        for t in types:
            ann = FieldAnnotation(
                report_type=t,
                field_path=f"test_{t}",
                field_label=f"测试{t}",
                sort_order=0,
            )
            db.add(ann)
        db.commit()

        for t in types:
            count = db.query(FieldAnnotation).filter(
                FieldAnnotation.report_type == t
            ).count()
            assert count >= 1
    finally:
        db.close()


def test_default_values():
    db = SessionLocal()
    try:
        annotation = FieldAnnotation(
            report_type="daily",
            field_path="field_with_defaults",
            field_label="默认值测试",
        )
        db.add(annotation)
        db.commit()

        assert annotation.source == ""
        assert annotation.formula == ""
        assert annotation.description == ""
        assert annotation.sort_order == 0
    finally:
        db.close()


def test_checkin_annotations_seeded():
    db = SessionLocal()
    try:
        results = db.query(FieldAnnotation).filter(
            FieldAnnotation.report_type == "checkin"
        ).order_by(FieldAnnotation.sort_order, FieldAnnotation.id).all()
        assert len(results) >= 10
        for r in results:
            assert r.report_type == "checkin"
        paths = [r.field_path for r in results]
        assert "emp_no" in paths
        assert "checkin_count" in paths
        assert "total_hours" in paths
        assert "avg_punctuality_rate" in paths
    finally:
        db.close()


def test_checkin_detail_annotations_seeded():
    db = SessionLocal()
    try:
        results = db.query(FieldAnnotation).filter(
            FieldAnnotation.report_type == "checkin_detail"
        ).order_by(FieldAnnotation.sort_order, FieldAnnotation.id).all()
        assert len(results) >= 10
        for r in results:
            assert r.report_type == "checkin_detail"
        paths = [r.field_path for r in results]
        assert "date" in paths or "scheduled_hours" in paths
        assert "summary_total_hours" in paths
    finally:
        db.close()


def test_checkin_detail_summary_prefix():
    db = SessionLocal()
    try:
        results = db.query(FieldAnnotation).filter(
            FieldAnnotation.report_type == "checkin_detail",
            FieldAnnotation.field_path.like("summary_%")
        ).all()
        assert len(results) >= 5
        for r in results:
            assert r.field_path.startswith("summary_")
    finally:
        db.close()


def test_sort_order():
    db = SessionLocal()
    try:
        items = db.query(FieldAnnotation).filter(
            FieldAnnotation.report_type == "daily"
        ).order_by(FieldAnnotation.sort_order, FieldAnnotation.id).all()

        sort_values = [i.sort_order for i in items]
        assert sort_values == sorted(sort_values)
    finally:
        db.close()
