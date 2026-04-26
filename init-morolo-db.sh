#!/bin/bash
# Manual Database Initialization Script for Morolo
# Use this if the automatic initialization via docker-compose doesn't work

set -e

echo "🔧 Initializing Morolo Database..."

# Database credentials
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="password"
POSTGRES_HOST="localhost"
POSTGRES_PORT="5432"
MOROLO_USER="morolo"
MOROLO_PASSWORD="morolo_password"
MOROLO_DB="morolo_db"

echo "📋 Step 1: Creating morolo user..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -p "$POSTGRES_PORT" << EOF
-- Create morolo role/user
CREATE ROLE $MOROLO_USER WITH LOGIN PASSWORD '$MOROLO_PASSWORD' CREATEDB;
EOF

echo "✅ Morolo user created"

echo "📋 Step 2: Creating morolo database..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -p "$POSTGRES_PORT" << EOF
-- Create Morolo database
CREATE DATABASE $MOROLO_DB OWNER $MOROLO_USER;
EOF

echo "✅ Morolo database created"

echo "📋 Step 3: Creating extensions..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -p "$POSTGRES_PORT" -d "$MOROLO_DB" << EOF
-- UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
EOF

echo "✅ Extensions created"

echo "📋 Step 4: Creating tables..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -p "$POSTGRES_PORT" -d "$MOROLO_DB" << EOF
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_document_jobs_status ON document_jobs(status);
CREATE INDEX IF NOT EXISTS idx_document_jobs_risk_band ON document_jobs(risk_band);
CREATE INDEX IF NOT EXISTS idx_document_jobs_created_at ON document_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_pii_entities_job_id ON pii_entities(job_id);
CREATE INDEX IF NOT EXISTS idx_pii_entities_entity_type ON pii_entities(entity_type);
EOF

echo "✅ Tables created"

echo "📋 Step 5: Granting permissions..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -p "$POSTGRES_PORT" -d "$MOROLO_DB" << EOF
-- Grant privileges
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $MOROLO_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $MOROLO_USER;
GRANT USAGE ON SCHEMA public TO $MOROLO_USER;

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $MOROLO_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $MOROLO_USER;
EOF

echo "✅ Permissions granted"

echo ""
echo "🎉 Database initialization complete!"
echo ""
echo "Test connection with:"
echo "  psql postgresql://$MOROLO_USER:$MOROLO_PASSWORD@localhost:5432/$MOROLO_DB"
