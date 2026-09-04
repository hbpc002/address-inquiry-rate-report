"""text-to-SQL 安全护栏：仅允许单条只读 SELECT，拦截一切写/危险操作。"""
import re

FORBIDDEN_KEYWORDS = (
    "insert", "update", "delete", "drop", "alter", "create", "truncate",
    "grant", "revoke", "merge", "replace", "call", "exec", "execute",
    "commit", "rollback", "savepoint", "vacuum", "analyze", "cluster",
    "comment", "copy", "lock", "reindex", "reset", "set", "show",
    "explain", "pragma", "into", "with",
)

MAX_ROWS = 200


def validate_sql(sql: str) -> str:
    if not sql or not sql.strip():
        raise ValueError("SQL 不能为空")

    stripped = sql.strip()
    # 去掉字符串字面量，避免其中的内容干扰关键字检测
    no_str = re.sub(r"'(?:[^']|'')*'", "''", stripped, flags=re.IGNORECASE)

    # 去注释
    if "--" in no_str or "/*" in no_str:
        raise ValueError("不允许 SQL 注释")

    # 仅允许单条语句
    if ";" in no_str.rstrip(";").strip():
        raise ValueError("仅允许单条 SQL 语句")

    body = stripped.rstrip(";").strip()
    m = re.match(r"\s*(\w+)", body, re.IGNORECASE)
    first_kw = m.group(1).lower() if m else ""
    if first_kw != "select":
        raise ValueError("仅允许 SELECT 查询")

    # 关键字检测在去字符串字面量的版本上进行，避免字面量里的词干扰
    low = no_str.lower()
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(r"\b" + kw + r"\b", low):
            raise ValueError(f"禁止的关键字: {kw}")

    # 未显式 LIMIT 时自动追加上限，避免一次性拉取过多数据
    if not re.search(r"\blimit\s+\d+", low):
        body = f"{body} LIMIT {MAX_ROWS}"
    return body
