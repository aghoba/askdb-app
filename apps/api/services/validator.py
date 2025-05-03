"""
apps/api/services/validator.py
──────────────────────────────
Validate that an LLM-generated SQL query is
• syntactically valid Postgres,
• strictly a single SELECT,
• touches only whitelisted tables.

Raises ValueError on any violation and
returns the (trimmed) SQL string on success.
"""

import sqlglot
from guardrails import Guard
from pydantic import BaseModel

# ── allow-list & schema whitelist ────────────────────────────────────────────
ALLOWED_STATEMENTS = {"SELECT"}

KNOWN_TABLES = {
    "plans",
    "users",
    "projects",
    "subscriptions",
    "payments",
}


# ── tiny Pydantic model so Guardrails can re-ask / coerce consistently ──────
class _SQL(BaseModel):
    sql: str


# ── main entrypoint ──────────────────────────────────────────────────────────
def validate_sql(sql: str) -> str:
    """
    Validate *sql* and return the cleaned string.
    Raises ValueError on any safety or syntax issue.
    """
    # Strip markdown fences or stray back-ticks
    sql = sql.strip().strip("`")

    # 0) Prevent multiple statements
    if ";" in sql and not sql.strip().endswith(";"):
        raise ValueError("❌ Multiple SQL statements detected")

    # 1. Ensure it ends with a semicolon
    if not sql.endswith(";"):
        sql += ";"

    # 2) Parse with SQLGlot (Postgres dialect)
    try:
        parsed = sqlglot.parse_one(sql, dialect="postgres")
    except sqlglot.errors.ParseError as exc:
        raise ValueError("❌ SQL syntax error") from exc

    # 3) Ensure it’s a pure SELECT
    if parsed.key.upper() not in ALLOWED_STATEMENTS:
        raise ValueError("❌ Only SELECT statements are allowed")

    # 4) Table whitelist
    tables_in_query = {t.name for t in parsed.find_all(sqlglot.expressions.Table)}
    unknown = tables_in_query - KNOWN_TABLES
    if unknown:
        raise ValueError(f"❌ Unknown tables: {', '.join(sorted(unknown))}")

    # 5) Final Guardrails pass
    guard = Guard.from_pydantic(_SQL)
    outcome = guard.parse(sql)
    if outcome.validated_output:
        return outcome.validated_output["sql"]

    return sql

