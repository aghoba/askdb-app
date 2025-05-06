import os
import io
import httpx
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from fastapi import FastAPI, Request
from dotenv import load_dotenv

# somewhere at top of file
CHART_TIMEOUT = httpx.Timeout(
    # keep your connect timeout small so you don’t wait forever to establish a socket
    connect=5.0,
    # but allow plenty of time for the server to respond
    read=120.0,
    write=60.0,
    pool=1.0
)

# Load local .env.dev if running in dev
load_dotenv(".env.dev")

slack_app = AsyncApp(
    token=os.getenv("SLACK_BOT_TOKEN"),
    signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
)
@slack_app.error
async def custom_error_handler(error, body, logger):
    logger.exception("Uncaught exception in Slack handler")
    logger.error("Request body: %r", body)

askdb_api_url = os.getenv("ASKDB_API_URL", "http://127.0.0.1:8001/ask")
askdb_chart_api_url = os.getenv("ASKDB_CHART_API_URL", "http://127.0.0.1:8001/chart")
@slack_app.command("/askdb")
async def handle_askdb(ack, body, respond):
    await ack()
    print("🔖 Slack team_id:", body.get("team_id"))
    user_id = body.get("user_id")
    question = body.get("text")

    if not user_id or not question:
        await respond("⚠️ Missing user ID or question.")
        return

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # resp = await client.post(
            #     askdb_api_url,
            #     json={"user_id": user_id, "question": question},
            #     headers={"Authorization": body.get("token", "dummy-token")},
            # )
            resp = await client.post(
            askdb_api_url,
            json={"user_id": user_id, "question": question},
            headers={
            "Authorization": body.get("token", ""),          # your auth-bypass header if dev
            "x-slack-team": body["team_id"],                 # ⚡ send the Slack team
            },)
    except httpx.RequestError as e:
        await respond(f"🚨 Error reaching AskDB API: {e}")
        return
    if resp.status_code == 401:
        await respond("🔒 Authorization error. Please sign in.")
        return
    if resp.status_code == 429:
        await respond("⏳ Rate limit exceeded. Please wait a minute and try again.")
        return
    if resp.status_code != 200:
        try:
            error_detail = resp.json().get("detail", "Unknown error.")
        except Exception:
            error_detail = resp.text
        return await respond(f"⚠️ {error_detail}")

    try:
        answer = resp.json().get("answer", "🤖 Sorry, no answer available.")
    except Exception:
        answer = "🤖 Sorry, invalid response from server."

    await respond(answer)

# Create FastAPI app
api = FastAPI()

# Create Slack request handler
handler = AsyncSlackRequestHandler(slack_app)

@api.post("/slack/events")
async def slack_events(req: Request):
    return await handler.handle(req)

# --- NEW chart command --------------------------------------------

@slack_app.command("/askdb-chart")
async def handle_chart(ack, body, respond):
    await ack()

    channel_id = body["channel_id"]
    question   = body.get("text", "Show MRR by month")
    user_id    = body["user_id"]

    # join
    try:
        join_resp = await slack_app.client.conversations_join(channel=channel_id)
        #print("join response:", join_resp)
    except Exception as e:
        print("join failed:", e)

    # 2) Hit your /chart endpoint…
    async with httpx.AsyncClient(timeout=CHART_TIMEOUT) as client:
        # resp = await client.post(
        #     askdb_chart_api_url,
        #     json={"user_id": user_id, "question": question},
        #     headers={"Authorization": body.get("token", "")},
        # )
        resp = await client.post(
            askdb_chart_api_url,
            json={"user_id": user_id, "question": question},
            headers={
            "Authorization": body.get("token", ""),          # your auth-bypass header if dev
            "x-slack-team": body["team_id"],                 # ⚡ send the Slack team
            },)
    # if resp.status_code != 200:
    #     return await respond(f"Chart error: {resp.text}")
    if resp.status_code != 200:
        try:
            error_detail = resp.json().get("detail", "Unknown error.")
        except Exception:
            error_detail = resp.text
        return await respond(f"⚠️ {error_detail}")
        
    # 3) Upload via the v2 API
    fileobj = io.BytesIO(resp.content)
    fileobj.name = "chart.png"
    fileobj.seek(0)    # ← rewind back to the start!

    try:
        upload_resp = await slack_app.client.files_upload_v2(
            channel=body["channel_id"],  
            file=fileobj,
            filename="chart.png",
            title=question[:80],
        )
        #print("upload response:", upload_resp)
    except Exception as e:
        await respond(f"❌ Slack upload failed: {e}")


# -------------------------------------------------------------------