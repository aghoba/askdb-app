from fastapi import HTTPException
from fastapi import Request
from utils import get_control_pool, decrypt_dsn
import asyncpg
async def get_workspace(slack_team_id: str, clerk_sub: str):
    pool = await get_control_pool()
    row = await pool.fetchrow(
        "SELECT * FROM workspaces WHERE slack_team_id=$1",
        slack_team_id
    )
    if not row or row["clerk_id"] != clerk_sub:
        raise HTTPException(403, "Workspace not onboarded")
    return row

async def get_user_conn(request: Request):
    # 1) grab both bits from request.state
    clerk_sub    = request.state.uid
    slack_team_id = request.state.slack_team_id

    # 2) lookup control-plane workspace
    pool = await get_control_pool()
    row = await pool.fetchrow(
        "SELECT * FROM workspaces WHERE slack_team_id=$1", slack_team_id
    )
    if not row or row["clerk_id"] != clerk_sub:
        raise HTTPException(403, "Workspace not onboarded")

    # 3) decrypt and connect
    dsn = decrypt_dsn(row["db_url_enc"])
    # stash it so handlers can see it
    request.state.dsn = dsn
    
    print(row["db_url_enc"])
    print(dsn)
    conn = await asyncpg.connect(dsn)
    try:
        yield conn
    finally:
        await conn.close()

