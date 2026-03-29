-- Database schema for GameInsights API cache

CREATE TABLE IF NOT EXISTS game_cache (
    cache_key TEXT PRIMARY KEY,
    endpoint TEXT NOT NULL,
    identifier TEXT NOT NULL,
    region TEXT NOT NULL,
    language TEXT NOT NULL,
    data JSONB NOT NULL,
    cached_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ttl_seconds INT NOT NULL
);

-- Index for cache expiry queries
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'idx_game_cache_expiry' AND n.nspname = 'public'
    ) THEN
        CREATE INDEX idx_game_cache_expiry ON game_cache(cached_at + (ttl_seconds || ' seconds')::interval);
    END IF;
END$$;

-- Index for endpoint-based queries
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'idx_game_cache_endpoint' AND n.nspname = 'public'
    ) THEN
        CREATE INDEX idx_game_cache_endpoint ON game_cache(endpoint);
    END IF;
END$$;
