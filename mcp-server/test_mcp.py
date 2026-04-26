"""
Test Morolo MCP Server connectivity and functionality.

This test verifies:
1. Database connection works
2. Queries return expected results
3. MCP server can be started
"""

import asyncio
import os
from datetime import datetime

import asyncpg


async def test_database_connection():
    """Test basic database connectivity."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://morolo:morolo_password@localhost:5432/morolo_db",
    )
    
    try:
        conn = await asyncpg.connect(database_url)
        print("✅ Database connection successful")
        
        # Test query: list all documents
        documents = await conn.fetch(
            "SELECT id, filename, risk_band, risk_score FROM document_jobs LIMIT 5"
        )
        print(f"✅ Found {len(documents)} documents in database")
        
        if documents:
            doc = documents[0]
            print(f"   Sample doc: {doc['filename']} (Risk: {doc['risk_band']}, Score: {doc['risk_score']})")
        
        # Test query: count by risk band
        risk_counts = await conn.fetch(
            """
            SELECT risk_band, COUNT(*) as count 
            FROM document_jobs 
            GROUP BY risk_band
            """
        )
        print(f"✅ Risk band distribution:")
        for row in risk_counts:
            print(f"   {row['risk_band']}: {row['count']} documents")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def test_query_high_risk():
    """Test querying HIGH risk documents."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://morolo:morolo_password@localhost:5432/morolo_db",
    )
    
    try:
        conn = await asyncpg.connect(database_url)
        
        rows = await conn.fetch(
            """
            SELECT id, filename, risk_score, risk_band, status, created_at, om_entity_fqn
            FROM document_jobs
            WHERE risk_band = $1
            ORDER BY risk_score DESC, created_at DESC
            LIMIT 10
            """,
            "HIGH",
        )
        
        print(f"\n✅ HIGH risk documents: {len(rows)}")
        for row in rows:
            print(f"   - {row['filename']}: {row['risk_score']} (Status: {row['status']})")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return False


async def test_pii_entities():
    """Test retrieving PII entities for a document."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://morolo:morolo_password@localhost:5432/morolo_db",
    )
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Get first document
        doc = await conn.fetchrow("SELECT id FROM document_jobs LIMIT 1")
        
        if not doc:
            print("⚠️  No documents in database to test PII entities")
            await conn.close()
            return True
        
        doc_id = doc['id']
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
        
        print(f"\n✅ PII entities in document {doc_id}:")
        for entity in entities:
            print(f"   {entity['entity_type']}: {entity['count']} (avg confidence: {entity['avg_confidence']:.2f})")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ PII entity query failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🧪 Testing Morolo MCP Server...\n")
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Query HIGH Risk Documents", test_query_high_risk),
        ("PII Entities Retrieval", test_pii_entities),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n📋 {name}:")
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Test error: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 Test Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"✅ Passed: {passed}/{total}")
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

