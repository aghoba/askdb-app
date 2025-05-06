import os, httpx, backoff
import re
from .validator import validate_sql
from .gpt4_fallback import gpt4_to_sql

HF_URL = os.getenv("HF_ENDPOINT_URL")
HF_TOKEN = os.getenv("HF_ACCESS_TOKEN")
GPT4_DEV_MODE = os.getenv("GPT4_DEV") == "1"

async def _sqlcoder(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(
            HF_URL,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {HF_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"inputs": prompt, "parameters": {}},
        )
    try:
        r.raise_for_status()
    except Exception:
        print("📥 HF response content (error):")
        print(r.text)
        raise

    # Raw response from HF
    raw_output = r.json()[0]["generated_text"]
    print("📤 SQLCoder raw output:")
    print(raw_output)

    # Extract SQL only from [SQL] ... marker
    match = re.search(r"\[SQL\](.*)", raw_output, re.DOTALL)
    if not match:
        raise ValueError("❌ Could not extract SQL from SQLCoder output")

    return match.group(1).strip()

@backoff.on_exception(backoff.expo, httpx.HTTPError, max_time=30)
async def to_sql(question: str, schema: str) -> tuple[str, str]:
    prompt = f"""### Task
    Generate a SQL query to answer [QUESTION]{question}[/QUESTION]

    ### Database Schema
    The query will run on a database with the following schema:
    {schema}

    ### Answer
    Given the database schema, here is the SQL query that [QUESTION]{question}[/QUESTION]
    [SQL]
    """

    try:
        if GPT4_DEV_MODE:
            # Dev: Try GPT-4 first, fallback to HF if it fails
            raw = await gpt4_to_sql(question, schema)
            print("GPT4 used")
            return raw, "gpt4"
        else:
            # Prod: Try HF first, fallback to GPT-4   
            raw = await _sqlcoder(prompt)
            print("hs_sqlcoder used")
            return raw, "sqlcoder"
    except Exception as e:
        print(f"⚠️ Primary model failed: {e}")
        try:
            if GPT4_DEV_MODE:
                raw = await _sqlcoder(prompt)
                print("hs_sqlcoder used")
                return raw, "sqlcoder"
            else:
                raw = await gpt4_to_sql(question, schema)
                print("GPT4 used")
                return raw, "gpt4"
        except Exception as final:
            print("❌ Both models failed.")
            raise final
