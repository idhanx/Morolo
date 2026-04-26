-- Initialize Morolo database with required extensions and tables

-- UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Cryptographic functions (for SHA-256 hashing)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create morolo role/user
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = 'morolo') THEN
    CREATE ROLE morolo WITH LOGIN PASSWORD 'morolo_password' CREATEDB;
  END IF;
END
$$;

-- Create OpenMetadata database if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'openmetadata_db') THEN
    CREATE DATABASE openmetadata_db;
  END IF;
END
$$;

-- Create Morolo database if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'morolo_db') THEN
    CREATE DATABASE morolo_db;
  END IF;
END
$$;

-- Grant privileges on openmetadata_db to morolo
GRANT ALL PRIVILEGES ON DATABASE openmetadata_db TO morolo;

-- Grant privileges on morolo_db to morolo
GRANT ALL PRIVILEGES ON DATABASE morolo_db TO morolo;

-- Connect to morolo_db for table creation (done via environment in docker-compose)
-- Tables will be created by Alembic migrations when backend starts
-- But we can create them here as fallback

-- Create document_jobs table
CREATE TABLE IF NOT EXISTS document_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    file_hash VARCHAR(256),
    file_size BIGINT,
    content_type VARCHAR(100),
    storage_key VARCHAR(512),
    status VARCHAR(50) DEFAULT 'uploaded',
    scan_type VARCHAR(50) DEFAULT 'TEXT',
    risk_score FLOAT,
    risk_band VARCHAR(20),
    om_entity_fqn VARCHAR(512),
    redacted_storage_key VARCHAR(512),
    redacted_om_entity_fqn VARCHAR(512),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create pii_entities table
CREATE TABLE IF NOT EXISTS pii_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES document_jobs(id) ON DELETE CASCADE,
    entity_type VARCHAR(50),
    start_offset INTEGER,
    end_offset INTEGER,
    confidence FLOAT,
    subtype VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255),
    action VARCHAR(50),
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    details TEXT,
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_document_jobs_status ON document_jobs(status);
CREATE INDEX IF NOT EXISTS idx_document_jobs_risk_band ON document_jobs(risk_band);
CREATE INDEX IF NOT EXISTS idx_document_jobs_created_at ON document_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_pii_entities_job_id ON pii_entities(job_id);
CREATE INDEX IF NOT EXISTS idx_pii_entities_entity_type ON pii_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- Grant all privileges to morolo user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO morolo;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO morolo;
GRANT USAGE ON SCHEMA public TO morolo;

-- Set default privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO morolo;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO morolo;
