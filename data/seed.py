from faker import Faker
import psycopg2
import random
from datetime import datetime, timedelta

# ---- Configuration ----
DB_URL = "postgresql://askdb:askdb@localhost:5432/askdb"
NUM_USERS = 50
MAX_PROJECTS_PER_USER = 3
MAX_PAYMENTS_PER_USER = 5

# ---- Setup ----
fake = Faker()
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# 1. Seed plans
plans = [
    ("Free", 0.00),
    ("Basic", 19.99),
    ("Pro", 49.99),
    ("Enterprise", 199.99),
]
plan_ids = []
for name, price in plans:
    # if it already exists, grab its id; otherwise insert it
    cur.execute("SELECT id FROM plans WHERE name = %s", (name,))
    row = cur.fetchone()
    if row:
        plan_ids.append(row[0])
    else:
        cur.execute(
            "INSERT INTO plans (name, price) VALUES (%s, %s) RETURNING id",
            (name, price)
        )
        plan_ids.append(cur.fetchone()[0])

# 2. Seed users
user_ids = []
for _ in range(NUM_USERS):
    email = fake.unique.email()
    name = fake.name()
    password_hash = fake.sha256()
    created_at = fake.date_time_between(start_date="-1y", end_date="now")
    cur.execute(
        "INSERT INTO users (email, name, password_hash, created_at) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (email, name, password_hash, created_at)
    )
    user_ids.append((cur.fetchone()[0], created_at))

# 3. Seed projects
for user_id, user_created in user_ids:
    num_projects = random.randint(1, MAX_PROJECTS_PER_USER)  # at least 1
    for _ in range(num_projects):
        proj_name = fake.bs().title()
        description = fake.paragraph(nb_sentences=3)
        created_at = fake.date_time_between(start_date=user_created, end_date="now")
        cur.execute(
            "INSERT INTO projects (user_id, name, description, created_at) "
            "VALUES (%s, %s, %s, %s)",
            (user_id, proj_name, description, created_at)
        )

# 4. Seed subscriptions
subscription_records = []
for user_id, user_created in user_ids:
    plan_index = random.randint(0, len(plan_ids) - 1)
    plan_id = plan_ids[plan_index]
    plan_name, plan_price = plans[plan_index]

    started_at = fake.date_time_between(start_date=user_created, end_date="now")
    status = random.choices(["active", "cancelled"], weights=[70, 30])[0]
    ended_at = (started_at + timedelta(days=random.randint(7, 180))
                if status == "cancelled" else None)
    cur.execute(
        "INSERT INTO subscriptions (user_id, plan_id, status, started_at, ended_at) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (user_id, plan_id, status, started_at, ended_at)
    )
    subscription_id = cur.fetchone()[0]
    subscription_records.append((subscription_id, user_id, started_at, plan_price))

# 5. Seed payments
for sub_id, user_id, started_at, amount in subscription_records:
    if amount == 0:
        continue  # Skip payments for Free plans
    num_payments = random.randint(1, MAX_PAYMENTS_PER_USER)  # at least 1
    for i in range(num_payments):
        paid_at = started_at + timedelta(days=30 * i + random.randint(0, 5))
        status = random.choice(["paid", "failed", "refunded"])
        cur.execute(
            "INSERT INTO payments (user_id, amount, status, paid_at) "
            "VALUES (%s, %s, %s, %s)",
            (user_id, amount, status, paid_at)
        )

# Commit and close
conn.commit()
cur.close()
conn.close()

print(f"Seeded {len(plan_ids)} plans, {len(user_ids)} users, projects, subscriptions, and payments.")
