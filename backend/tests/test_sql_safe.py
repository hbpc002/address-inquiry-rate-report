from app.agent.sql_safe import validate_sql


def test_valid_select_passes():
    out = validate_sql("SELECT * FROM employees")
    assert out.lower().startswith("select")
    # 未显式 LIMIT 时自动追加
    assert "limit 200" in out.lower()


def test_explicit_limit_kept():
    out = validate_sql("SELECT id FROM employees LIMIT 10")
    assert "limit 10" in out.lower()
    assert out.lower().count("limit") == 1


def test_non_select_rejected():
    for sql in ("UPDATE employees SET name='x'", "DELETE FROM employees", "INSERT INTO employees VALUES(1)"):
        try:
            validate_sql(sql)
            assert False, f"应拒绝: {sql}"
        except ValueError:
            pass


def test_write_keyword_rejected():
    try:
        validate_sql("SELECT * FROM employees; DROP TABLE employees")
        assert False
    except ValueError:
        pass


def test_comment_rejected():
    try:
        validate_sql("SELECT 1 -- comment")
        assert False
    except ValueError:
        pass


def test_forbidden_keyword_rejected():
    try:
        validate_sql("SELECT * FROM employees WHERE name = 'a'; CREATE TABLE x(b int)")
        assert False
    except ValueError:
        pass
