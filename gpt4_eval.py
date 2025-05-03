import os
import re
import yaml
import json
import asyncio
from openai import AsyncOpenAI
from apps.api.services.gpt4_fallback import gpt4_to_sql
from apps.api.services.validator import _tables_schema

# 1. Fail early if API key is missing
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable")

client = AsyncOpenAI(api_key=api_key)

async def ask_gpt4_eval(expected_sql: str, generated_sql: str) -> str:
    prompt = ("""
        You are a SQL evaluator. Compare the following two SQL queries.
        Tell me if they are semantically equivalent (i.e. return the same result) assuming the same schema.
        Respond with one of: \"MATCH\", \"DIFFERENT\", and explain why in 1-2 sentences.
              - Bear in mind the Generated one (second one), 
                schema was known before generating the SQL.
              - So it is a match if the second one is more detailed (but also correct).
        )."""
        f"Expected SQL:\n{expected_sql}\n\n"
        f"Generated SQL:\n{generated_sql}\n"
    )
    resp = await client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=150,
    )
    return resp.choices[0].message.content.strip()

async def evaluate_batch(concurrency: int = 5):
    # Load all questions & precompute schema
    with open("apps/api/tests/eval_large.yaml") as f:
        questions = yaml.safe_load(f)
    schema = _tables_schema()

    semaphore = asyncio.Semaphore(concurrency)
    results = []

    async def process_item(i, item):
        try:
            question = re.sub(r"\s*\(variation \d+\)$", "", item["question"])
            generated_sql = await gpt4_to_sql(question, schema)
            # throttle concurrent GPT calls
            async with semaphore:
                gpt_eval = await ask_gpt4_eval(item["expected_sql"], generated_sql)
            print(f"[{i+1}] ✅ {gpt_eval}")
            return {
                "question":       question,
                "expected_sql":   item["expected_sql"],
                "generated_sql":  generated_sql,
                "gpt_eval":       gpt_eval
            }
        except Exception as e:
            print(f"[{i+1}] ❌ Error: {e}")
            return {
                "question":       question,
                "expected_sql":   item["expected_sql"],
                "generated_sql":  None,
                "gpt_eval":       f"ERROR: {e}"
            }

    # Fire off all tasks
    tasks = [
        asyncio.create_task(process_item(i, item))
        for i, item in enumerate(questions)
    ]

    # Gather results
    for task in asyncio.as_completed(tasks):
        results.append(await task)

    # Save results
    with open("eval_results.json", "w") as out_f:
        json.dump(results, out_f, indent=2)

if __name__ == "__main__":
    asyncio.run(evaluate_batch())
