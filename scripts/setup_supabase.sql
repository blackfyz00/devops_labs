-- ============================================================================
-- Quotes Scraper: Supabase setup
--
-- Run this script once in the Supabase SQL editor.
--
-- After running it:
--   1. Open Dashboard -> Integrations -> Queues -> Settings and enable
--      "Expose Queues via PostgREST". This creates the pgmq_public schema
--      with the send/read/archive wrapper functions used by the backend.
--   2. In the same settings page, grant the anon role the permissions used by
--      the backend (send: Select+Insert, read: Select+Update,
--      archive: Select+Delete). If the backend uses a service_role key, the
--      defaults are normally sufficient.
-- ============================================================================

-- 1. Queue -------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pgmq;

-- Idempotent: pgmq.create returns false when the queue already exists.
SELECT pgmq.create('scraper_jobs');

-- 2. Job tables --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_status (
    id UUID PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'queued',
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS job_results (
    id UUID PRIMARY KEY REFERENCES job_status(id),
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS job_status_status_idx ON job_status (status);
CREATE INDEX IF NOT EXISTS job_results_created_at_idx ON job_results (created_at);

-- 3. Table grants ------------------------------------------------------------
GRANT ALL ON TABLE job_status TO anon, authenticated, service_role;
GRANT ALL ON TABLE job_results TO anon, authenticated, service_role;

-- 4. Row Level Security ------------------------------------------------------
ALTER TABLE job_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow service role full access" ON job_status;
CREATE POLICY "Allow service role full access" ON job_status
    FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow service role full access" ON job_results;
CREATE POLICY "Allow service role full access" ON job_results
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- The backend uses SUPABASE_ANON_KEY, so the anon role needs access too.
-- For production, remove these policies and use a service_role key.
DROP POLICY IF EXISTS "Allow anon full access" ON job_status;
CREATE POLICY "Allow anon full access" ON job_status
    FOR ALL TO anon USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow anon full access" ON job_results;
CREATE POLICY "Allow anon full access" ON job_results
    FOR ALL TO anon USING (true) WITH CHECK (true);

-- 5. Queue permissions -------------------------------------------------------
ALTER TABLE pgmq.q_scraper_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE pgmq.a_scraper_jobs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow queue access" ON pgmq.q_scraper_jobs;
CREATE POLICY "Allow queue access" ON pgmq.q_scraper_jobs
    FOR ALL TO anon, authenticated, service_role
    USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow archive access" ON pgmq.a_scraper_jobs;
CREATE POLICY "Allow archive access" ON pgmq.a_scraper_jobs
    FOR ALL TO anon, authenticated, service_role
    USING (true) WITH CHECK (true);

GRANT USAGE ON SCHEMA pgmq TO anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLE pgmq.q_scraper_jobs TO anon, authenticated, service_role;
GRANT SELECT, INSERT, DELETE
    ON TABLE pgmq.a_scraper_jobs TO anon, authenticated, service_role;

-- pgmq_public wrappers are created when "Expose Queues via PostgREST" is
-- enabled. If they already exist, grant execute permissions to the API roles.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'pgmq_public') THEN
        EXECUTE 'GRANT USAGE ON SCHEMA pgmq_public TO anon, authenticated, service_role';
        EXECUTE 'GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA pgmq_public '
                'TO anon, authenticated, service_role';
    END IF;
END
$$;

-- 6. Supabase Cron keepalive (optional) --------------------------------------
-- Run after the backend is deployed. Replace the URL and secret.
-- Requires the pg_cron and pg_net extensions (available on Supabase).
--
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
-- CREATE EXTENSION IF NOT EXISTS pg_net;
--
-- SELECT cron.schedule(
--     'keepalive',
--     '*/5 * * * *',
--     $$SELECT net.http_post(
--         url := 'YOUR_RENDER_URL/health',
--         headers := '{"Authorization": "Bearer YOUR_INTERNAL_SECRET"}'::jsonb
--     )$$
-- );
