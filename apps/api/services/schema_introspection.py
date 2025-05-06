import asyncpg
from collections import defaultdict
import time

async def fetch_tables_schema(conn: asyncpg.Connection) -> str:
    """
    Returns a newline-separated string like:
      users(id, email, name, …)
      plans(id, price, …)
    for every table in public.schema, ordered alphabetically.
    """
    rows = await conn.fetch(
        """
        SELECT table_name, column_name
          FROM information_schema.columns
         WHERE table_schema = 'public'
         ORDER BY table_name, ordinal_position
        """
    )
    tables: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        tables[r["table_name"]].append(r["column_name"])
    # build lines
    lines = [
        f"{tbl}({', '.join(cols)})"
        for tbl, cols in sorted(tables.items())
    ]
    return "\n".join(lines)

# In-process cache: { dsn_str: (schema_text, timestamp) }
_schema_cache: dict[str, tuple[str, float]] = {}

async def get_cached_schema(conn: asyncpg.Connection, dsn: str, ttl: int = 300) -> str:
    """
    Return the cached schema for this DSN, refreshing if older than `ttl` seconds.
    """
    entry = _schema_cache.get(dsn)
    if entry:
        schema_text, last_fetched = entry
        if time.time() - last_fetched < ttl:
            return schema_text

    # Cache miss or expired → re‐introspect
    schema_text = await fetch_tables_schema(conn)
    _schema_cache[dsn] = (schema_text, time.time())
    return schema_text

