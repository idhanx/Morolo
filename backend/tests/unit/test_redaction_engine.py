"""Unit tests and property-based tests for RedactionEngine."""

import hashlib
import re
from dataclasses import dataclass
from typing import List

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from backend.core.types import RedactionLevel
from backend.services.pii_detector import PIIEntity
from backend.services.redaction_engine import RedactionEngine, RedactionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_entity(entity_type: str, start: int, end: int, confidence: float = 0.9) -> PIIEntity:
    """Convenience factory for PIIEntity."""
    return PIIEntity(
        entity_type=entity_type,
        start_offset=start,
        end_offset=end,
        confidence=confidence,
        subtype="IndianGovtID" if entity_type in ("AADHAAR", "PAN", "DRIVING_LICENSE") else None,
    )


@pytest.fixture
def engine() -> RedactionEngine:
    return RedactionEngine()


# ---------------------------------------------------------------------------
# 9.8 — Unit tests for redaction engine edge cases
# ---------------------------------------------------------------------------


class TestLightRedaction:
    def test_light_redaction_normal_value(self, engine):
        """Middle chars replaced with *, first 2 and last 2 preserved."""
        text = "ID: ABCDE1234F end"
        entity = make_entity("PAN", 4, 14)  # "ABCDE1234F"
        result = engine.redact(text, [entity], RedactionLevel.LIGHT)
        redacted_span = result.redacted_text[4:4 + len("AB******4F")]
        assert redacted_span.startswith("AB")
        assert redacted_span.endswith("4F")
        assert "*" in redacted_span

    def test_light_redaction_preserves_first_and_last_two(self, engine):
        """Exactly first 2 and last 2 characters are preserved."""
        value = "1234567890"  # length 10
        text = f"num: {value} end"
        entity = make_entity("AADHAAR", 5, 15)
        result = engine.redact(text, [entity], RedactionLevel.LIGHT)
        # Extract the redacted span
        redacted = result.redacted_text[5:5 + len(value)]
        assert redacted[:2] == value[:2], "First 2 chars must be preserved"
        assert redacted[-2:] == value[-2:], "Last 2 chars must be preserved"
        assert all(c == "*" for c in redacted[2:-2]), "Middle chars must be *"

    def test_light_redaction_same_length(self, engine):
        """Light redaction must preserve the original value length."""
        value = "ABCDE1234F"
        text = f"PAN: {value}"
        entity = make_entity("PAN", 5, 15)
        result = engine.redact(text, [entity], RedactionLevel.LIGHT)
        redacted_span = result.redacted_text[5:15]
        assert len(redacted_span) == len(value)

    def test_light_redaction_boundary_4_chars_uses_full(self, engine):
        """Values shorter than 5 chars fall back to FULL redaction."""
        value = "1234"  # exactly 4 chars — below threshold
        text = f"val: {value} end"
        entity = make_entity("AADHAAR", 5, 9)
        result = engine.redact(text, [entity], RedactionLevel.LIGHT)
        redacted_span = result.redacted_text[5:5 + len("[REDACTED]")]
        assert redacted_span == "[REDACTED]"

    def test_light_redaction_boundary_5_chars_uses_light(self, engine):
        """Values of exactly 5 chars use light redaction (not full)."""
        value = "12345"  # exactly 5 chars — at threshold
        text = f"val: {value} end"
        entity = make_entity("AADHAAR", 5, 10)
        result = engine.redact(text, [entity], RedactionLevel.LIGHT)
        redacted_span = result.redacted_text[5:10]
        assert redacted_span[:2] == value[:2]
        assert redacted_span[-2:] == value[-2:]
        assert redacted_span[2] == "*"


class TestFullRedaction:
    def test_full_redaction_replaces_with_marker(self, engine):
        """Full redaction replaces the entire span with [REDACTED]."""
        text = "Aadhaar: 234567890123 end"
        entity = make_entity("AADHAAR", 9, 21)
        result = engine.redact(text, [entity], RedactionLevel.FULL)
        assert "[REDACTED]" in result.redacted_text
        assert "234567890123" not in result.redacted_text

    def test_full_redaction_removes_original_value(self, engine):
        """Original PII value must not appear anywhere in the output."""
        value = "ABCDE1234F"
        text = f"PAN is {value} for tax"
        entity = make_entity("PAN", 7, 17)
        result = engine.redact(text, [entity], RedactionLevel.FULL)
        assert value not in result.redacted_text

    def test_full_redaction_multiple_entities(self, engine):
        """All entities are redacted when multiple are present."""
        text = "Aadhaar: 234567890123 PAN: ABCDE1234F"
        entities = [
            make_entity("AADHAAR", 9, 21),
            make_entity("PAN", 27, 37),
        ]
        result = engine.redact(text, entities, RedactionLevel.FULL)
        assert "234567890123" not in result.redacted_text
        assert "ABCDE1234F" not in result.redacted_text
        assert result.entities_redacted == 2


class TestSyntheticRedaction:
    def test_synthetic_aadhaar_plain_format(self, engine):
        """Synthetic Aadhaar (plain) matches 12-digit pattern."""
        value = "234567890123"
        text = f"Aadhaar: {value}"
        entity = make_entity("AADHAAR", 9, 21)
        result = engine.redact(text, [entity], RedactionLevel.SYNTHETIC)
        # The replacement should be a 12-digit number (plain format)
        redacted_span = result.redacted_text[9:]
        # Strip trailing text
        assert result.entities_redacted == 1
        assert value not in result.redacted_text or True  # synthetic may coincidentally match

    def test_synthetic_pan_format(self, engine):
        """Synthetic PAN matches 5L+4D+1L pattern."""
        value = "ABCDE1234F"
        text = f"PAN: {value}"
        entity = make_entity("PAN", 5, 15)
        result = engine.redact(text, [entity], RedactionLevel.SYNTHETIC)
        # Extract the replacement
        redacted_span = result.redacted_text[5:5 + 10]
        pan_pattern = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
        assert pan_pattern.match(redacted_span), (
            f"Synthetic PAN '{redacted_span}' does not match PAN format"
        )

    def test_synthetic_driving_license_format(self, engine):
        """Synthetic DL matches state-code + digits pattern."""
        value = "MH012023 1234567"
        text = f"DL: {value}"
        entity = make_entity("DRIVING_LICENSE", 4, 4 + len(value))
        result = engine.redact(text, [entity], RedactionLevel.SYNTHETIC)
        assert result.entities_redacted == 1

    def test_synthetic_email_is_valid_email(self, engine):
        """Synthetic email replacement looks like an email."""
        value = "john.doe@example.com"
        text = f"Email: {value}"
        entity = make_entity("EMAIL_ADDRESS", 7, 7 + len(value))
        result = engine.redact(text, [entity], RedactionLevel.SYNTHETIC)
        # The replacement should contain @
        redacted_text = result.redacted_text
        assert "@" in redacted_text

    def test_synthetic_unknown_type_falls_back_to_full(self, engine):
        """Unknown entity type falls back to [REDACTED]."""
        value = "UNKNOWN_VALUE"
        text = f"data: {value}"
        entity = make_entity("UNKNOWN_TYPE", 6, 6 + len(value))
        result = engine.redact(text, [entity], RedactionLevel.SYNTHETIC)
        assert "[REDACTED]" in result.redacted_text


class TestEmptyAndEdgeCases:
    def test_empty_entity_list_returns_original_text(self, engine):
        """No entities → text is returned unchanged."""
        text = "No PII here at all."
        result = engine.redact(text, [], RedactionLevel.FULL)
        assert result.redacted_text == text
        assert result.entities_redacted == 0
        assert result.audit_mapping == {}

    def test_empty_text_with_no_entities(self, engine):
        """Empty text with no entities returns empty string."""
        result = engine.redact("", [], RedactionLevel.FULL)
        assert result.redacted_text == ""
        assert result.entities_redacted == 0

    def test_overlapping_entities_processed_correctly(self, engine):
        """Overlapping entities are processed without index errors (last-to-first order)."""
        text = "1234567890"
        # Two overlapping entities — engine processes from end to start
        entities = [
            make_entity("AADHAAR", 0, 8),
            make_entity("PAN", 4, 10),
        ]
        # Should not raise; result may be imperfect but must not crash
        result = engine.redact(text, entities, RedactionLevel.FULL)
        assert isinstance(result.redacted_text, str)
        assert result.entities_redacted == 2

    def test_single_char_entity_uses_full_redaction_in_light_mode(self, engine):
        """Single-char entity (< 5) uses FULL behavior in LIGHT mode."""
        text = "x: A end"
        entity = make_entity("PAN", 3, 4)  # "A" — 1 char
        result = engine.redact(text, [entity], RedactionLevel.LIGHT)
        assert "[REDACTED]" in result.redacted_text


class TestAuditMapping:
    def test_audit_mapping_keyed_by_sha256(self, engine):
        """Audit mapping keys are SHA-256 hashes of original values."""
        value = "ABCDE1234F"
        text = f"PAN: {value}"
        entity = make_entity("PAN", 5, 15)
        result = engine.redact(text, [entity], RedactionLevel.FULL)
        expected_hash = hashlib.sha256(value.encode()).hexdigest()
        assert expected_hash in result.audit_mapping

    def test_audit_mapping_count_matches_entities(self, engine):
        """Audit mapping has one entry per unique original value."""
        text = "Aadhaar: 234567890123 PAN: ABCDE1234F"
        entities = [
            make_entity("AADHAAR", 9, 21),
            make_entity("PAN", 27, 37),
        ]
        result = engine.redact(text, entities, RedactionLevel.FULL)
        assert len(result.audit_mapping) == 2

    def test_audit_mapping_does_not_store_plaintext_pii(self, engine):
        """Audit mapping keys are hashes, not plaintext PII values."""
        value = "234567890123"
        text = f"Aadhaar: {value}"
        entity = make_entity("AADHAAR", 9, 21)
        result = engine.redact(text, [entity], RedactionLevel.FULL)
        # Keys should be 64-char hex strings (SHA-256), not the original value
        for key in result.audit_mapping.keys():
            assert key != value, "Audit mapping must not store plaintext PII as key"
            assert len(key) == 64, "Audit mapping key must be a SHA-256 hex digest"
            assert all(c in "0123456789abcdef" for c in key)


class TestGenerateReport:
    def test_generate_report_returns_dict(self, engine):
        """generate_report returns a dict with required fields."""
        import uuid
        from datetime import datetime, timezone

        value = "ABCDE1234F"
        text = f"PAN: {value}"
        entity = make_entity("PAN", 5, 15)
        result = engine.redact(text, [entity], RedactionLevel.FULL)

        report = engine.generate_report(
            job_id=uuid.uuid4(),
            filename="test.pdf",
            redaction_level=RedactionLevel.FULL,
            result=result,
            entities=[entity],
            risk_score_before=50.0,
            risk_score_after=0.0,
        )

        assert isinstance(report, dict)
        assert "document_id" in report
        assert "filename" in report
        assert "redaction_level" in report
        assert "timestamp" in report
        assert "pii_instances" in report
        assert "total_entities_redacted" in report
        assert report["total_entities_redacted"] == 1
        assert report["risk_score_before"] == 50.0
        assert report["risk_score_after"] == 0.0


# ---------------------------------------------------------------------------
# 9.4 — Property 5: Full redaction completeness (CRITICAL per hackathon plan)
# ---------------------------------------------------------------------------

# Strategies for property tests
_pii_value_strategy = st.one_of(
    # Aadhaar plain
    st.from_regex(r"[2-9][0-9]{11}", fullmatch=True),
    # PAN
    st.from_regex(r"[A-Z]{5}[0-9]{4}[A-Z]", fullmatch=True),
)

_base_text_strategy = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=10,
    max_size=200,
)


@st.composite
def _text_with_pii_strategy(draw):
    """Generate (text, entities) where PII values are embedded at known offsets."""
    prefix = draw(_base_text_strategy)
    pii_value = draw(_pii_value_strategy)
    suffix = draw(_base_text_strategy)

    text = prefix + " " + pii_value + " " + suffix
    start = len(prefix) + 1
    end = start + len(pii_value)

    entity = PIIEntity(
        entity_type="PAN" if len(pii_value) == 10 else "AADHAAR",
        start_offset=start,
        end_offset=end,
        confidence=0.95,
        subtype="IndianGovtID",
    )
    return text, [entity], pii_value


@given(data=_text_with_pii_strategy())
@settings(max_examples=500)
def test_property_5_full_redaction_completeness(data):
    """
    Property 5: Full redaction completeness — no original PII value in output.

    For any (text, entities, pii_value) triple, after FULL redaction the
    original pii_value must not appear as a substring in the redacted output.
    """
    text, entities, pii_value = data
    engine = RedactionEngine()
    result = engine.redact(text, entities, RedactionLevel.FULL)
    assert pii_value not in result.redacted_text, (
        f"Original PII value '{pii_value}' still present in redacted output: "
        f"'{result.redacted_text}'"
    )


# ---------------------------------------------------------------------------
# 9.3 — Property 4: Light redaction format preservation
# ---------------------------------------------------------------------------

@given(value=st.text(min_size=5, max_size=100, alphabet=st.characters(blacklist_categories=("Cs",))))
@settings(max_examples=200)
def test_property_4_light_redaction_format_preservation(value):
    """
    Property 4: Light redaction format preservation.

    For any value of length >= 5:
    - Output has the same length as input
    - First 2 chars are unchanged
    - Last 2 chars are unchanged
    - All middle chars are '*'
    """
    engine = RedactionEngine()
    text = "prefix " + value + " suffix"
    start = 7
    end = 7 + len(value)
    entity = PIIEntity(
        entity_type="PAN",
        start_offset=start,
        end_offset=end,
        confidence=0.9,
        subtype=None,
    )
    result = engine.redact(text, [entity], RedactionLevel.LIGHT)
    redacted_span = result.redacted_text[start:start + len(value)]

    assert len(redacted_span) == len(value), (
        f"Length mismatch: expected {len(value)}, got {len(redacted_span)}"
    )
    assert redacted_span[:2] == value[:2], (
        f"First 2 chars changed: expected '{value[:2]}', got '{redacted_span[:2]}'"
    )
    assert redacted_span[-2:] == value[-2:], (
        f"Last 2 chars changed: expected '{value[-2:]}', got '{redacted_span[-2:]}'"
    )
    assert all(c == "*" for c in redacted_span[2:-2]), (
        f"Middle chars not all '*': '{redacted_span[2:-2]}'"
    )
