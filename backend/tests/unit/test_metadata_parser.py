"""Unit tests for RedactionMetadataParser and RedactionMetadataPrettyPrinter."""

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.api.schemas import PIIInstanceRecord, RedactionMetadata
from backend.core.types import RedactionLevel
from backend.services.metadata_parser import (
    RedactionMetadataParser,
    RedactionMetadataPrettyPrinter,
)


def test_pretty_printer_produces_valid_json(sample_redaction_metadata):
    """Test that pretty printer produces valid JSON."""
    json_str = RedactionMetadataPrettyPrinter.pretty_print(sample_redaction_metadata)
    
    # Should be valid JSON
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)
    assert "document_id" in parsed
    assert "filename" in parsed


def test_pretty_printer_uses_sorted_keys(sample_redaction_metadata):
    """Test that pretty printer sorts keys alphabetically."""
    json_str = RedactionMetadataPrettyPrinter.pretty_print(sample_redaction_metadata)
    
    # Parse and check key order
    lines = json_str.split("\n")
    keys = [line.split(":")[0].strip().strip('"') for line in lines if ":" in line]
    
    # Keys should be sorted (ignoring nested objects)
    top_level_keys = [k for k in keys if k and not k.startswith(" ")]
    assert top_level_keys == sorted(top_level_keys)


def test_parser_round_trip(sample_redaction_metadata):
    """Test that parse(pretty_print(metadata)) == metadata."""
    # Serialize
    json_str = RedactionMetadataPrettyPrinter.pretty_print(sample_redaction_metadata)
    
    # Deserialize
    parsed = RedactionMetadataParser.parse(json_str)
    
    # Should match original
    assert parsed.document_id == sample_redaction_metadata.document_id
    assert parsed.filename == sample_redaction_metadata.filename
    assert parsed.redaction_level == sample_redaction_metadata.redaction_level
    assert parsed.total_entities_redacted == sample_redaction_metadata.total_entities_redacted
    assert parsed.risk_score_before == sample_redaction_metadata.risk_score_before
    assert parsed.risk_score_after == sample_redaction_metadata.risk_score_after


def test_parser_handles_invalid_json():
    """Test that parser raises ValidationError on invalid JSON."""
    with pytest.raises(Exception):  # ValidationError or JSONDecodeError
        RedactionMetadataParser.parse("not valid json")


def test_parser_handles_missing_required_fields():
    """Test that parser raises ValidationError on missing required fields."""
    invalid_json = json.dumps({
        "document_id": str(uuid4()),
        # Missing filename, redaction_level, etc.
    })
    
    with pytest.raises(Exception):  # ValidationError
        RedactionMetadataParser.parse(invalid_json)


def test_pretty_printer_handles_empty_pii_instances():
    """Test that pretty printer handles empty PII instances list."""
    metadata = RedactionMetadata(
        document_id=uuid4(),
        filename="test.pdf",
        redaction_level=RedactionLevel.FULL,
        timestamp=datetime.now(timezone.utc),
        pii_instances=[],  # Empty list
        total_entities_redacted=0,
        risk_score_before=0.0,
        risk_score_after=0.0,
    )
    
    json_str = RedactionMetadataPrettyPrinter.pretty_print(metadata)
    parsed = json.loads(json_str)
    
    assert parsed["pii_instances"] == []
    assert parsed["total_entities_redacted"] == 0
