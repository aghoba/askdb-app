-- compose/init/03_workspaces.sql
CREATE TABLE workspaces (
  id             SERIAL   PRIMARY KEY,
  slack_team_id  TEXT     UNIQUE NOT NULL,
  clerk_id       TEXT     UNIQUE NOT NULL,
  db_url_enc     TEXT     NOT NULL,         -- encrypted DSN
  created_at     TIMESTAMP DEFAULT now()
);
