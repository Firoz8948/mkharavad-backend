-- M Kharavad Company — PostgreSQL setup (run as superuser postgres)

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mkharavad') THEN
    CREATE ROLE mkharavad WITH LOGIN PASSWORD 'mkharavad';
  ELSE
    ALTER ROLE mkharavad WITH LOGIN PASSWORD 'mkharavad';
  END IF;
END
$$;

SELECT 'CREATE DATABASE mkharavad OWNER mkharavad'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mkharavad')\gexec

GRANT ALL PRIVILEGES ON DATABASE mkharavad TO mkharavad;
