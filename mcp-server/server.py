"""
Morolo MCP Server — AI Agent interface for PII document catalog.

Exposes three tools:
  - get_document_risk_score(doc_id)
  - list_pii_entities(doc_id)
  - query_pii_documents(risk_band, limit)

Usage:
    pip install mcp asyncpg
    python mcp-server/server.py

This enables AI agents to query Morolo's PII catalog via MCP:
  "Show me all HIGH risk documents with Aadhaar numbers"
"""

import asyncio
import json
import os
from typing import Any

import asyncpg
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://morolo:morolo_password@localhost:5432/morolo_db",
)

app = Server("morolo-pii-catalog")


async def get_db_connection():
    """Get a database connection."""
    # Convert asyncpg URL format
    url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    return await asyncpg.connect(url)


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="get_document_risk_score",
            description=(
                "Get the PII risk score and breakdown for a specific document. "
                "Returns risk score (0-100), risk band (LOW/MEDIUM/HIGH/CRITICAL), "
                "and per-type PII breakdown."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "Document UUID",
                    }
                },
                "required": ["doc_id"],
            },
        ),
        Tool(
            name="list_pii_entities",
            description=(
                "List all detected PII entities in a document. "
                "Returns entity type, offsets, confidence, and subtype."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "Document UUID",
                    }
                },
                "required": ["doc_id"],
            },
        ),
        Tool(
            name="query_pii_documents",
            description=(
                "Query documents by risk band. "
                "Returns a list of documents matching the specified risk level. "
                "Useful for finding all HIGH or CRITICAL risk documents."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "risk_band": {
                        "type": "string",
                        "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                        "description": "Risk band to filter by",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of results",
                    },
                },
                "required": ["risk_band"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    conn = await get_db_connection()

    try:
        if name == "get_document_risk_score":
            doc_id = arguments["doc_id"]
            row = await conn.fetchrow(
                """
                SELECT id, filename, risk_score, risk_band, status, created_at
                FROM document_jobs
                WHERE id = $1::uuid
                """,
                doc_id,
            )

            if not row:
                return [TextContent(type="text", text=f"Document {doc_id} not found")]

            # Get PII breakdown
            entities = await conn.fetch(
                """
                SELECT entity_type, COUNT(*) as count, AVG(confidence) as avg_confidence
                FROM pii_entities
                WHERE job_id = $1::uuid
                GROUP BY entity_type
                ORDER BY count DESC
                """,
                doc_id,
            )

            result = {
                "doc_id": str(row["id"]),
                "filename": row["filename"],
                "risk_score": float(row["risk_score"] or 0),
                "risk_band": row["risk_band"],
                "status": row["status"],
                "pii_breakdown": {
                    e["entity_type"]: {
                        "count": e["count"],
                        "avg_confidence": round(float(e["avg_confidence"]), 3),
                    }
                    for e in entities
                },
            }

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "list_pii_entities":
            doc_id = arguments["doc_id"]
            entities = await conn.fetch(
                """
                SELECT entity_type, start_offset, end_offset, confidence, subtype
                FROM pii_entities
                WHERE job_id = $1::uuid
                ORDER BY start_offset
                """,
                doc_id,
            )

            result = [
                {
                    "entity_type": e["entity_type"],
                    "start_offset": e["start_offset"],
                    "end_offset": e["end_offset"],
                    "confidence": round(float(e["confidence"]), 3),
                    "subtype": e["subtype"],
                }
                for e in entities
            ]

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "query_pii_documents":
            risk_band = arguments["risk_band"]
            limit = min(arguments.get("limit", 10), 100)

            rows = await conn.fetch(
                """
                SELECT id, filename, risk_score, risk_band, status, created_at,
                       om_entity_fqn
                FROM document_jobs
                WHERE risk_band = $1
                ORDER BY risk_score DESC, created_at DESC
                LIMIT $2
                """,
                risk_band,
                limit,
            )

            result = [
                {
                    "doc_id": str(r["id"]),
                    "filename": r["filename"],
                    "risk_score": float(r["risk_score"] or 0),
                    "risk_band": r["risk_band"],
                    "status": r["status"],
                    "om_entity_fqn": r["om_entity_fqn"],
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                }
                for r in rows
            ]

            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"risk_band": risk_band, "count": len(result), "documents": result},
                        indent=2,
                    ),
                )
            ]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    finally:
        await conn.close()


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
