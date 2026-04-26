# Morolo MCP Server

AI agents can query Morolo's PII document catalog via the Model Context Protocol (MCP).

## Tools

### `get_document_risk_score`
Get risk score and PII breakdown for a specific document.

```json
{
  "doc_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

Returns:
```json
{
  "doc_id": "550e8400-...",
  "filename": "aadhaar_sample.pdf",
  "risk_score": 78.5,
  "risk_band": "HIGH",
  "pii_breakdown": {
    "AADHAAR": {"count": 1, "avg_confidence": 0.95},
    "PAN": {"count": 1, "avg_confidence": 0.92}
  }
}
```

### `list_pii_entities`
List all detected PII entities in a document.

```json
{"doc_id": "550e8400-..."}
```

### `query_pii_documents`
Find all documents with a specific risk level.

```json
{"risk_band": "HIGH", "limit": 10}
```

Returns all HIGH risk documents ordered by risk score descending.

## Setup

```bash
pip install mcp asyncpg

# Set database URL
export DATABASE_URL="postgresql://morolo:morolo_password@localhost:5432/morolo_db"

# Start server
python mcp-server/server.py
```

## Use Cases

- "Show me all HIGH risk documents uploaded this week"
- "Which documents contain Aadhaar numbers?"
- "What's the risk score for document X?"
- "List all PII entities in the employee verification form"

This enables natural language governance queries over Morolo's document catalog.
