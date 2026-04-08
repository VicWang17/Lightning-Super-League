-- Initial database setup
-- This script runs when the MySQL container starts for the first time

USE lightning_league;

-- Create basic tables (placeholder for future migrations)
-- Actual tables will be created via Alembic migrations

-- Example: Create a test table
CREATE TABLE IF NOT EXISTS health_check (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO health_check (message) VALUES ('Database initialized successfully');
