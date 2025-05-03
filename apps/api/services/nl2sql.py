import os, textwrap
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

_SYSTEM = """
You are an API that strictly outputs one and only one valid, complete SQL query for each input.
- The query must be valid PostgreSQL syntax.
- Never output multiple SQL queries.
- Never output explanations, comments, or anything else besides the SQL.
- Never merge multiple queries together.
- Always focus on the most relevant interpretation of the user’s question.
- If the user’s request could generate multiple queries, choose only the most appropriate one.
- Always ensure the output is a single standalone SQL query.
- Never write mutating statements (INSERT/UPDATE/DELETE), temp tables, or CTEs.
"""

def _tables_schema() -> str:
    return textwrap.dedent(
        """
        plans(id, name, price, created_at)
        users(id, email, name, password_hash, created_at)
        projects(id, user_id, name, description, created_at)
        subscriptions(id, user_id, plan_id, status, started_at, ended_at)
        payments(id, user_id, amount, status, paid_at)
        """
    )


async def to_sql(question: str) -> str:
    chat = [
        {"role": "system", "content": _SYSTEM},
        {
            "role": "user",
            "content": f"Schema:\n{_tables_schema()}\n\nQuestion: {question}",
        },
    ]
    resp = await client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=chat,
        max_tokens=128,
        temperature=0,
    )
    return resp.choices[0].message.content.strip("` ").split(";")[0]
