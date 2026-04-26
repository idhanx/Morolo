# 🔐 Morolo — PII Governance for Indian Documents

> Automated PII detection and redaction system for Indian Government IDs with OpenMetadata integration

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![OpenMetadata 1.3.3](https://img.shields.io/badge/OpenMetadata-1.3.3-blue)](https://www.open-metadata.org/)

---

## 📋 Overview

Morolo is a PII governance system designed to detect and redact sensitive information from Indian documents. It integrates with OpenMetadata for metadata management and provides risk scoring for compliance purposes.

### What It Does

- Detects Indian Government IDs (Aadhaar, PAN, Driving License) plus email and phone numbers
- Calculates risk scores based on detected PII types
- Integrates with OpenMetadata for metadata tracking
- Provides document redaction capabilities
- Offers REST API for document processing

### What It Doesn't Do

- This is a proof-of-concept/hackathon project, not production-ready
- Detection accuracy varies based on document quality
- No real-time processing (uses async task queue)
- Limited to text-based documents (OCR quality dependent)

---

## 🚀 Quick Start

### Prerequisites

```bash
docker --version        # 20.10+
docker-compose --version  # 2.0+
```

### 1. Clone Repository

```bash
git clone https://github.com/idhanx/Morolo.git
cd Morolo
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and set:
# - OM_TOKEN (get from OpenMetadata UI)
# - JWT_SECRET_KEY (generate with: openssl rand -hex 32)
```

### 3. Start Services

```bash
# Start OpenMetadata infrastructure first
docker-compose -f docker-compose-postgres.yml up -d

# Wait for services to be healthy (~60 seconds)
sleep 60

# Start application services
docker-compose up -d

# Check status
docker-compose ps
```

### 4. Test the System

```bash
# Check health
curl http://localhost:8000/health

# Upload a document (you'll need a PDF with PII)
curl -X POST "http://localhost:8000/upload" \
  -F "file=@your_document.pdf" \
  -F "redaction_level=FULL"

# Check status (replace {doc_id} with response from upload)
curl "http://localhost:8000/status/{doc_id}"
```

### 5. Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| FastAPI Docs | http://localhost:8000/docs | None |
| OpenMetadata | http://localhost:8585 | admin / admin |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |

---

## 🏗️ Architecture

### Components

```
┌─────────────────────────────────────────┐
│ FastAPI Backend                          │
│ - Document upload                        │
│ - PII detection (Presidio)               │
│ - Risk scoring                           │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ Celery Worker                            │
│ - Async document processing              │
│ - Redaction                              │
│ - OpenMetadata integration               │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ Storage & Metadata                       │
│ - PostgreSQL (metadata)                  │
│ - MinIO (documents)                      │
│ - OpenMetadata (governance)              │
└─────────────────────────────────────────┘
```

### Technology Stack

- **Backend**: FastAPI (Python)
- **PII Detection**: Microsoft Presidio with custom recognizers
- **Task Queue**: Celery + Redis
- **Database**: PostgreSQL
- **Storage**: MinIO (S3-compatible)
- **Metadata**: OpenMetadata 1.3.3
- **Frontend**: Next.js (basic UI)

---

## 🔌 API Reference

### Upload Document

```bash
POST /upload
Content-Type: multipart/form-data

Parameters:
- file: PDF/DOCX/PNG/JPG (max 10MB)
- redaction_level: LIGHT|FULL|SYNTHETIC|NONE

Response:
{
  "doc_id": "uuid",
  "filename": "document.pdf",
  "status": "PENDING"
}
```

### Check Status

```bash
GET /status/{doc_id}

Response:
{
  "doc_id": "uuid",
  "status": "PII_DETECTED",
  "risk_score": 85.0,
  "risk_band": "HIGH",
  "pii_summary": {
    "AADHAAR": 1,
    "EMAIL": 2
  }
}
```

### Get Risk Score

```bash
GET /risk/{doc_id}

Response:
{
  "risk_score": 85.0,
  "risk_band": "HIGH",
  "entity_breakdown": {...}
}
```

### Download Documents

```bash
# Original document
GET /documents/{doc_id}/download?format=original

# Redacted document
GET /documents/{doc_id}/download?format=redacted
```

---

## 🔍 PII Detection

### Supported Entity Types

| Entity Type | Detection Method | Notes |
|-------------|------------------|-------|
| Aadhaar | Regex pattern | 12-digit format (spaced/hyphenated) |
| PAN | Regex pattern | 10-character alphanumeric |
| Driving License | Regex pattern | State-based format |
| Email | Presidio built-in | Standard email detection |
| Phone | Presidio built-in | Indian phone formats |

### Risk Scoring

Risk scores are calculated based on:
- Type of PII detected (Aadhaar has highest weight)
- Number of entities found
- Diversity of PII types
- Confidence scores

**Risk Bands:**
- LOW (<5): Minimal PII
- MEDIUM (5-15): Some PII detected
- HIGH (15-30): Government ID detected
- CRITICAL (≥30): Multiple government IDs

---

## 🔗 OpenMetadata Integration

### What's Integrated

- **Container Entities**: Documents are registered as Container entities
- **Custom Properties**: Risk score, risk band, detected PII types
- **Classifications**: Hierarchical PII classifications (when working)
- **Lineage**: Tracks original → redacted transformation

### Known Limitations

- Classification tagging via API has compatibility issues with OM v1.3.3
- Manual tagging in OM UI works as workaround
- Lineage tracking is basic (no complex transformations)

---

## 🔧 Troubleshooting

### Services Won't Start

```bash
# Check Docker is running
docker ps

# View logs
docker-compose logs backend
docker-compose logs -f celery_worker

# Restart everything
docker-compose down
docker-compose -f docker-compose-postgres.yml down
docker-compose -f docker-compose-postgres.yml up -d
sleep 60
docker-compose up -d
```

### Network Errors

The docker-compose files use a shared network. Make sure:
1. Start `docker-compose-postgres.yml` first
2. Wait for services to be healthy
3. Then start `docker-compose.yml`

### PII Not Detected

- Ensure document has clear text (not scanned images)
- For scanned PDFs, OCR quality matters (300+ DPI recommended)
- Check confidence threshold in `.env` (default: 0.7)

### OpenMetadata Connection Failed

- Verify OM_TOKEN is set correctly in `.env`
- Check OpenMetadata is running: `curl http://localhost:8585/api/v1/health-check`
- System will work without OM (graceful degradation)

---

## ⚠️ Known Issues & Limitations

### Current Limitations

1. **Not Production Ready**: This is a hackathon/proof-of-concept project
2. **No Authentication**: API endpoints are open (add auth for production)
3. **Limited Error Handling**: Some edge cases not covered
4. **OCR Quality**: Depends on Tesseract, may miss text in poor scans
5. **Classification Tagging**: API compatibility issue with OM v1.3.3
6. **No Real-time Updates**: Uses polling, not WebSockets
7. **Single Server**: Not designed for horizontal scaling
8. **Basic Frontend**: Minimal UI, needs improvement

### Security Considerations

- Default credentials in `.env.example` are for development only
- No rate limiting on API endpoints
- No input validation for file types
- No virus scanning on uploads
- Audit logging is basic

### Performance Notes

- Document processing is async (10-30 seconds typical)
- Large documents (>5MB) may timeout
- Concurrent uploads limited by Celery worker count
- No caching implemented

---

## 📦 Deployment

### Development Only

This project is configured for local development. For production deployment, you would need:

- Proper authentication and authorization
- SSL/TLS certificates
- Managed databases (not Docker containers)
- Load balancing
- Monitoring and alerting
- Backup and disaster recovery
- Security hardening
- Rate limiting
- Input validation
- Virus scanning

---

## 🧪 Testing

### Manual Testing

```bash
# Run unit tests
docker-compose exec backend pytest backend/tests/unit/ -v

# Check specific component
docker-compose exec backend python -c "
from backend.services.pii_detector import PIIDetector
detector = PIIDetector()
print('PII Detector initialized')
"
```

### Integration Testing

```bash
# Test database connection
docker-compose exec backend python -c "
from backend.core.database import get_db_engine
engine = get_db_engine()
print('Database connected')
"

# Test MinIO connection
docker-compose exec backend python -c "
from backend.core.storage import get_storage_client
client = get_storage_client()
print('MinIO connected')
"
```

---

## 📁 Project Structure

```
Morolo/
├── backend/                 # FastAPI application
│   ├── api/                 # REST endpoints
│   ├── services/            # Business logic
│   ├── models/              # Database models
│   ├── tasks/               # Celery tasks
│   └── tests/               # Unit tests
├── frontend/                # Next.js UI (basic)
├── mcp-server/              # MCP interface (experimental)
├── docker-compose.yml       # Application services
├── docker-compose-postgres.yml  # OpenMetadata stack
└── .env.example             # Configuration template
```

---

## 🤝 Contributing

This is a hackathon project. Contributions welcome but note the limitations above.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- **Microsoft Presidio** - PII detection framework
- **OpenMetadata** - Metadata governance platform
- **Tesseract** - OCR engine
- **FastAPI** - Web framework

---

## 📞 Support

For issues or questions:
- Check logs: `docker-compose logs [service]`
- Review troubleshooting section above
- Create GitHub issue with details

---

**Morolo** - PII Governance for Indian Documents

*Note: This is a proof-of-concept project developed for a hackathon. It demonstrates PII detection and OpenMetadata integration but is not production-ready.*
