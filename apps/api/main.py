import asyncpg
from apps.api.services.nl2sql import to_sql
from services.validator import validate_sql
#from services.validator import _tables_schema
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Callable
import redis.asyncio as redis
import os
from jose import jwt, JWTError
#from utils import get_database_url  # or wherever you place it

from fastapi.concurrency import run_in_threadpool
from fastapi import FastAPI, Depends, HTTPException, Response
import pandas as pd
import time

from services.workspace import get_user_conn
from services.viz import df_to_png, cache_key
#from services.cache import get_png, set_png
from services.schema_introspection import fetch_tables_schema,get_cached_schema
#from services.schema_introspection import get_cached_schema

import pandas as pd, duckdb

import posthog
posthog.project_api_key = os.getenv("POSTHOG_API_KEY")
posthog.host = os.getenv("POSTHOG_HOST")

app = FastAPI()

# Clerk Settings
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")
CLERK_JWT_ISSUER = "https://clerk."  # Adjust if needed

# Redis Connection
rds = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)



# Incoming request model
class AskPayload(BaseModel):
    user_id: str
    question: str

# Rate Limit Middleware: 5 queries per minute per user
async def rate_limit(request: Request, call_next: Callable):
    if request.url.path != "/ask":
        return await call_next(request)

    auth = request.headers.get("authorization", "")
    user = auth or "anon"
    key = f"rate:{user}"

    current = await rds.incr(key)
    if current == 1:
        await rds.expire(key, 60)

    if current > 5:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit 5 QPM"},
        )

    return await call_next(request)

app.middleware("http")(rate_limit)

async def clerk_guard(request: Request) -> str:
    # 1) auth bypass for local dev
    if os.getenv("CLERK_DEV_BYPASS") == "1":
        uid = "dev-user"
    else:
        token = request.headers.get("authorization")
        if not token:
            raise HTTPException(status_code=401, detail="Missing bearer token")
        try:
            payload = jwt.decode(
                token,
                CLERK_PUBLISHABLE_KEY,
                issuer=CLERK_JWT_ISSUER,
                options={"verify_aud": False}
            )
            uid = payload["sub"]
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid Clerk token")

    # 2) stash the Clerk user ID for downstream dependencies:
    request.state.uid = uid

    # 3) also stash the Slack workspace/team id (Slackbot adds this header):
    request.state.slack_team_id = request.headers.get("x-slack-team", "")

    return uid


# Healthcheck
@app.get("/healthz")
def health_check():
    return {"status": "ok"}

# Main /ask endpoint
#@app.post("/ask")
#async def ask(payload: AskPayload, uid: str = Depends(clerk_guard)):
#    return {"answer": f"👋 Hi <@{uid}>! You asked: \"{payload.question}\""}
@app.post("/ask")
async def ask(
    payload: AskPayload,
    request: Request,
    clerk_sub: str               = Depends(clerk_guard),
    conn:     asyncpg.Connection = Depends(get_user_conn),
    ):     # bring in the Request
    start = time.perf_counter()

    # 0) Introspect the customer's schema once per request (or use your TTL cache)
    #schema_str = await fetch_tables_schema(conn)
    dsn = request.state.dsn
    schema_str = await get_cached_schema(conn, dsn)
    # 1) NL → SQL with the live schema
    raw_sql, source = await to_sql(payload.question, schema_str)

    # 2) Validate against that same schema
    try:
        sql = validate_sql(raw_sql, schema_str)
    except ValueError as e:
        # guardrails or syntax failure
        raise HTTPException(status_code=400, detail=str(e))

    # 3) Run the query on the injected connection
    rows = await conn.fetch(sql)

    # 4) Build a <=20-row preview
    if not rows:
        answer = "∅ No rows."
    else:
        lines = [" | ".join(str(v) for v in rec.values()) for rec in rows[:20]]
        answer = f"```\n{'\n'.join(lines)}\n```"

    # 5) Telemetry
    lat_ms = (time.perf_counter() - start) * 1000
    posthog.capture(
        clerk_sub,
        "query_executed",
        {"lat_ms": lat_ms, "cached": False, "source": source},
    )

    return {"answer": answer}



@app.post("/chart")
async def chart(
    payload: AskPayload,
    request: Request,
    clerk_sub: str             = Depends(clerk_guard),
    conn:     asyncpg.Connection = Depends(get_user_conn),
):
    t0 = time.perf_counter()
    print("⚡ Step 1: received", time.perf_counter() - t0)

    # ← fetch the live schema for this customer
    dsn = request.state.dsn
    schema_str = await get_cached_schema(conn, dsn)

    # 1) NL → SQL against the dynamic schema
    raw_sql, source = await to_sql(payload.question, schema_str)
    # 2) Validate against that same schema
    try:
        sql = validate_sql(raw_sql, schema_str)
    except ValueError as e:
        # guardrails or syntax failure
        raise HTTPException(status_code=400, detail=str(e))
    print("⚡ Step 2: to_sql done", time.perf_counter() - t0)

    # 3) Run it on the injected connection
    print("⚡ Step 3: executing query", time.perf_counter() - t0)
    rows = await conn.fetch(sql)
    print("⚡ Step 4: Fetched rows", time.perf_counter() - t0)

    if not rows:
        raise HTTPException(404, "No data to plot")

    df = pd.DataFrame(rows)
    print("⚡ Step 5: DataFrame built", time.perf_counter() - t0)

    # 4) Generate the PNG in a threadpool
    png = await run_in_threadpool(df_to_png, df)
    print("⚡ Step 6: PNG generated", time.perf_counter() - t0)

    # 5) Telemetry
    lat_ms = (time.perf_counter() - t0) * 1000
    posthog.capture(clerk_sub, "query_executed", {
        "lat_ms": lat_ms,
        "cached": False,
        "source": source,
    })

    return Response(content=png, media_type="image/png")

# from cryptography.fernet import Fernet

# @app.on_event("startup")
# async def startup_event():
#     print("🛫 Starting up with FERNET_KEY=", os.getenv("FERNET_KEY"))
#     key = os.getenv("FERNET_KEY").encode()
#     cipher = Fernet(key)
#     # Replace the URL below with your actual DSN (read-only user)
#     db_plaintext_dsn = os.getenv("DATABASE_URL_RO").encode("utf-8")
#     plaintext_dsn = b"postgresql://askdb_ro:askdb_ro_pwd@localhost:5432/askdb"

#     token = cipher.encrypt(db_plaintext_dsn)
#     print(token.decode())  # copy this value for db_url_enc
#     print(cipher.encrypt(plaintext_dsn).decode())
    
