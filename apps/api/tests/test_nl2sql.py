import pytest, asyncio
from apps.api.services.gpt4_fallback import to_sql
from services.validator import validate_sql

# 30-question golden set
QUESTIONS = [
    # ── plans ───────────────────────────────────────────────
    "Show all plans.",
    "Show plans priced above $50.",
    "List the top 3 most expensive plans.",
    "Show all plans sorted by price descending.",
    # ── users ───────────────────────────────────────────────
    "List every user email.",
    "Show first 5 users ordered by created date.",
    "List users without projects.",
    "Show users without payments.",
    # ── subscriptions ───────────────────────────────────────
    "List all active subscriptions.",
    "Show subscriptions started in the last 7 days.",
    "Show subscriptions ending this month.",
    "Show users on trial plans.",
    "Show subscriptions with missing end date.",
    "Show number of subscriptions by status.",
    # ── payments ────────────────────────────────────────────
    "List payments above $10.",
    "Show payments marked as paid.",
    "Show latest payment for each user.",
    "Show total payments grouped by status.",
    "Show dollar amount of each payment with user email.",
    "Show payment count per user.",
    # ── projects ────────────────────────────────────────────
    "Show projects created this year.",
    "List projects with descriptions containing 'project'.",
    "Show count of projects per user.",
    "Show users with more than one project.",
    # ── joins / combined ────────────────────────────────────
    "Show users and their plan names.",
    "Show total revenue per plan.",
    "Show average payment amount per plan.",
    "Show users with active subscriptions.",
    "Show oldest subscription per user.",
    "Show count of users per plan.",
]

@pytest.mark.asyncio
@pytest.mark.parametrize("q", QUESTIONS)
async def test_sql_snapshot(snapshot, q):
    """NL → SQL → validated SQL should stay stable."""
    sql = validate_sql(await to_sql(q))
    snapshot.assert_match(sql, q) # <-- FIX: Pass the question as snapshot name
    
