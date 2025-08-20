-- PostgreSQL initialization script for Face AI Django application
-- This script runs when the PostgreSQL container starts for the first time

-- Create database if it doesn't exist
-- Note: The database is already created by POSTGRES_DB environment variable
-- This script is for additional setup if needed

-- Create extensions that might be needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create additional schemas if needed
-- CREATE SCHEMA IF NOT EXISTS face_ai;
-- CREATE SCHEMA IF NOT EXISTS video_processing;

-- Grant permissions
-- GRANT ALL PRIVILEGES ON SCHEMA face_ai TO face_ai_user;
-- GRANT ALL PRIVILEGES ON SCHEMA video_processing TO face_ai_user;

-- Set timezone
SET timezone = 'UTC';

-- Log the initialization
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL database initialized successfully for Face AI application';
    RAISE NOTICE 'Database: %', current_database();
    RAISE NOTICE 'User: %', current_user;
    RAISE NOTICE 'Timezone: %', current_setting('timezone');
END $$;
