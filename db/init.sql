-- AI Memory Engine Database Schema
-- PostgreSQL initialization script

CREATE TABLE IF NOT EXISTS user_profile (
    id SERIAL PRIMARY KEY,
    profile_data JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS interests (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(200) NOT NULL,
    category VARCHAR(100),
    intensity FLOAT DEFAULT 0,
    mention_count INT DEFAULT 0,
    first_seen TIMESTAMPTZ,
    last_seen TIMESTAMPTZ,
    trend VARCHAR(20) DEFAULT 'stable',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interests_topic ON interests(topic);
CREATE INDEX IF NOT EXISTS idx_interests_category ON interests(category);
CREATE INDEX IF NOT EXISTS idx_interests_intensity ON interests(intensity DESC);

CREATE TABLE IF NOT EXISTS suggestions (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    related_interests INT[],
    source_context TEXT,
    feedback VARCHAR(20),
    feedback_note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_suggestions_category ON suggestions(category);
CREATE INDEX IF NOT EXISTS idx_suggestions_feedback ON suggestions(feedback);
CREATE INDEX IF NOT EXISTS idx_suggestions_created ON suggestions(created_at DESC);

CREATE TABLE IF NOT EXISTS decisions (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(500),
    decision VARCHAR(50),
    context TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decisions_topic ON decisions(topic);
CREATE INDEX IF NOT EXISTS idx_decisions_created ON decisions(created_at DESC);

CREATE TABLE IF NOT EXISTS ingest_log (
    id SERIAL PRIMARY KEY,
    source VARCHAR(100),
    item_count INT,
    vector_count INT,
    status VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ingest_log_source ON ingest_log(source);
CREATE INDEX IF NOT EXISTS idx_ingest_log_status ON ingest_log(status);
CREATE INDEX IF NOT EXISTS idx_ingest_log_created ON ingest_log(created_at DESC);

-- Initialize default user profile
INSERT INTO user_profile (profile_data) 
VALUES ('{"interests":[],"patterns":{},"preferences":{}}')
ON CONFLICT DO NOTHING;

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to user_profile
CREATE TRIGGER update_user_profile_updated_at 
    BEFORE UPDATE ON user_profile
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
