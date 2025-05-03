-- apps/db/init.sql  (create this new file anywhere you like; we'll mount it)
CREATE TABLE organizations (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    org_id      INT REFERENCES organizations(id),
    email       TEXT NOT NULL UNIQUE,
    full_name   TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE subscriptions (
    id          SERIAL PRIMARY KEY,
    org_id      INT REFERENCES organizations(id),
    plan        TEXT,
    status      TEXT,
    started_at  TIMESTAMPTZ,
    ends_at     TIMESTAMPTZ
);

CREATE TABLE metrics (
    id          SERIAL PRIMARY KEY,
    org_id      INT REFERENCES organizations(id),
    name        TEXT,
    description TEXT
);

CREATE TABLE events (
    id          SERIAL PRIMARY KEY,
    metric_id   INT REFERENCES metrics(id),
    value       NUMERIC,
    event_time  TIMESTAMPTZ DEFAULT NOW()
);

-- a couple of seed rows so tests don’t return ∅
INSERT INTO organizations (name) VALUES ('Acme Inc.'), ('Globex LLC');
INSERT INTO subscriptions (org_id, plan, status, started_at)
VALUES (1, 'pro', 'active', NOW()), (2, 'starter', 'trial', NOW());
