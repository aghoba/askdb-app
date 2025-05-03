import asyncpg
from apps.api.services.nl2sql import to_sql
from services.validator import validate_sql
from services.validator import _tables_schema
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Callable
import redis.asyncio as redis
import os
from jose import jwt, JWTError
from utils import get_database_url  # or wherever you place it

from fastapi.concurrency import run_in_threadpool
from fastapi import FastAPI, Depends, HTTPException, Response
import pandas as pd
import asyncpg
import time

from services.viz import df_to_png, cache_key
#from services.cache import get_png, set_png
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

# Clerk Guard: validates Authorization token
async def clerk_guard(request: Request):
    if os.getenv("CLERK_DEV_BYPASS") == "1":
        return "dev-user"         # <- anything that identifies the caller
    token = request.headers.get("authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    try:
        payload = jwt.decode(
            token,
            CLERK_PUBLISHABLE_KEY,
            issuer=CLERK_JWT_ISSUER,
            options={"verify_aud": False}  # Clerk doesn't require 'aud' usually
        )
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid Clerk token")

# Healthcheck
@app.get("/healthz")
def health_check():
    return {"status": "ok"}

# Main /ask endpoint
#@app.post("/ask")
#async def ask(payload: AskPayload, uid: str = Depends(clerk_guard)):
#    return {"answer": f"👋 Hi <@{uid}>! You asked: \"{payload.question}\""}
@app.post("/ask")
async def ask(payload: AskPayload, uid: str = Depends(clerk_guard)):
    start = time.perf_counter()


    # 1) NL → SQL
    raw_sql, source = await to_sql(payload.question, _tables_schema())
    
    # 2) Validate / sanitize
    try:
        sql = validate_sql(raw_sql)
    except ValueError as e:
        print(f"❌ Error handling /ask: {e}")   # <-- ADD THIS LINE
        raise HTTPException(status_code=400, detail=str(e))  # 👈 Return the actual error message

    # 3) Run it
    #conn = await asyncpg.connect(os.getenv("DATABASE_URL"))

    conn = await asyncpg.connect(get_database_url())
    rows = await conn.fetch(sql)
    await conn.close()

    # 4) Render simple preview (≤20 rows)
    if not rows:
        answer = "∅ No rows."
    else:
        cols = rows[0].keys()
        preview = "\n".join(
            " | ".join(str(row[c]) for c in cols) for row in rows[:20]
        )
        answer = f"```{preview}```"
    # … your existing logic …
    lat_ms = (time.perf_counter() - start) * 1000
    posthog.capture(uid, "query_executed",
                {"lat_ms": lat_ms, 
                 "cached": False,
                 "source": source})
    return {"answer": answer}



@app.post("/chart")
async def chart(payload: AskPayload, uid: str = Depends(clerk_guard)):
    t0 = time.perf_counter()
    print("⚡ Step 1: received", time.perf_counter() - t0)

    raw_sql, source = await to_sql(payload.question, _tables_schema())
    sql = validate_sql(raw_sql)
    print("⚡ Step 2: to_sql done", time.perf_counter() - t0)

    conn = await asyncpg.connect(get_database_url())
    print("⚡ Step 3: DB connect", time.perf_counter() - t0)

    rows = await conn.fetch(sql)
    await conn.close()
    print("⚡ Step 4: Fetched rows", time.perf_counter() - t0)

    if not rows:
        raise HTTPException(404, "No data to plot")

    df = pd.DataFrame(rows)
    print("⚡ Step 5: DataFrame built", time.perf_counter() - t0)

    # Offload the blocking PNG generation into a threadpool:
    png = await run_in_threadpool(df_to_png, df)
    print("⚡ Step 6: PNG generated", time.perf_counter() - t0)
    lat_ms = (time.perf_counter() - t0) * 1000
    posthog.capture(uid, "query_executed",
                {"lat_ms": lat_ms, 
                 "cached": False,
                "source": source  # ← hf or gpt4
                })
    return Response(content=png, media_type="image/png")
