-- Roles for the operating database. Locally a superuser runs this; on Neon
-- `operating-db provision` creates the same roles through the migrator.
--
-- operating_migrator  owns the schema and runs migrations only.
-- operating_api       the API at runtime: no superuser, no BYPASSRLS, owns nothing.
-- operating_publisher sweeps and marks the outbox across workspaces; nothing else.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'operating_migrator') THEN
        CREATE ROLE operating_migrator LOGIN NOSUPERUSER NOCREATEROLE NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'operating_api') THEN
        CREATE ROLE operating_api LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'operating_publisher') THEN
        CREATE ROLE operating_publisher LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOINHERIT;
    END IF;
END
$$;
