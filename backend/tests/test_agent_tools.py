import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@127.0.0.1:5432/schedule_test')

from app.models.database import Base, engine, SessionLocal, init_db
from app.main import app


def setup_module():
    Base.metadata.drop_all(bind=engine)
    init_db()


def teardown_module():
    pass


def test_report_tools_return_json_on_empty_db():
    db = SessionLocal()
    try:
        from app.agent.tools import make_tools
        tools = make_tools(db)
        assert len(tools) >= 6
        by_name = {t.name: t for t in tools}
        # 空库下返回空列表的 JSON
        res = by_name["query_team_ranking"].invoke({"year_month": "2026-07"})
        assert json.loads(res) == []
        res2 = by_name["query_dashboard_stats"].invoke({"year_month": "2026-07"})
        data = json.loads(res2)
        assert "employee_count" in data
    finally:
        db.close()


def test_run_sql_readonly_executes():
    db = SessionLocal()
    try:
        from app.agent.tools import make_tools
        tools = make_tools(db)
        by_name = {t.name: t for t in tools}
        res = by_name["run_sql"].invoke({"sql_query": "SELECT 1 AS n"})
        data = json.loads(res)
        assert data["row_count"] == 1
        assert data["rows"][0]["n"] == 1
    finally:
        db.close()


def test_run_sql_rejects_write():
    db = SessionLocal()
    try:
        from app.agent.tools import make_tools
        tools = make_tools(db)
        by_name = {t.name: t for t in tools}
        try:
            by_name["run_sql"].invoke({"sql_query": "DROP TABLE employees"})
            assert False
        except ValueError:
            pass
    finally:
        db.close()
