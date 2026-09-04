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


def test_string_literals_preserved():
    """返回的 SQL 应保留字符串字面量的原始内容（不能被替换为空串）。"""
    out = validate_sql("SELECT * FROM daily_reports WHERE schedule_date BETWEEN '2026-08-29' AND '2026-09-04'")
    assert "'2026-08-29'" in out
    assert "'2026-09-04'" in out


def test_keyword_inside_literal_not_rejected():
    """字符串字面量里的关键词不应被误判为写语句。"""
    # 'with' 在字面量内出现；SELECT 里虽含 with 词，但不构成 WITH 子句
    out = validate_sql("SELECT name FROM employees WHERE remark = 'with a friend'")
    assert out.lower().startswith("select")
