-- Optional starter seed for keyword_filters, matching your original spec.
-- Edit freely -- this becomes editable from the Settings dashboard page once built.
-- Run after schema.sql: psql $DATABASE_URL -f backend/db/seed.sql

INSERT INTO keyword_filters (pipeline, keyword, category) VALUES
    ('professional', 'Data Engineer', 'role'),
    ('professional', 'Data Analyst', 'role'),
    ('professional', 'Data Scientist', 'role'),
    ('professional', 'AI Engineer', 'role'),
    ('professional', 'ML Engineer', 'role'),
    ('professional', 'Machine Learning Engineer', 'role'),
    ('professional', 'Analytics Engineer', 'role'),
    ('professional', 'AI/ML Engineer', 'role'),
    ('professional', 'python', 'skill'),
    ('professional', 'sql', 'skill'),
    ('professional', 'databricks', 'skill'),
    ('professional', 'snowflake', 'skill'),
    ('professional', 'spark', 'skill'),
    ('professional', 'airflow', 'skill'),
    ('professional', 'pyspark', 'skill');
