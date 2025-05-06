-- compose/init/02_ro_user.sql
CREATE ROLE askdb_ro LOGIN PASSWORD 'askdb_ro_pwd';

GRANT CONNECT ON DATABASE askdb TO askdb_ro;
GRANT USAGE   ON SCHEMA  public TO askdb_ro;

-- existing tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO askdb_ro;
-- future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO askdb_ro;
