"""Pytest configuration and Hypothesis strategies for property-based testing."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from hypothesis import strategies as st

from backend.api.schemas import PIIInstanceRecord, RedactionMetadata
from backend.core.types import RedactionLevel


# Hypothesis Strategies for Property-Based Testing


@st.composite
def pii_instance_strategy(draw):
    """Generate random PIIInstanceRecord for testing."""
    entity_types = ["AADHAAR", "PAN", "DRIVING_LICENSE", "EMAIL", "PHONE", "PERSON"]
    
    entity_type = draw(st.sampled_from(entity_types))
    start_offset = draw(st.integers(min_value=0, max_value=1000))
    length = draw(st.integers(min_value=5, max_value=50))
    end_offset = start_offset + length
    
    return PIIInstanceRecord(
        entity_type=entity_type,
        original_value=draw(st.text(min_size=5, max_size=50)),
        redacted_value=draw(st.text(min_size=5, max_size=50)),
        start_offset=start_offset,
        end_offset=end_offset,
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
    )


@st.composite
def redaction_metadata_strategy(draw):
    """Generate random RedactionMetadata for testing."""
    num_instances = draw(st.integers(min_value=0, max_value=20))
    pii_instances = [draw(pii_instance_strategy()) for _ in range(num_instances)]
    
    risk_score_before = draw(st.floats(min_value=0.0, max_value=100.0))
    risk_score_after = draw(st.floats(min_value=0.0, max_value=risk_score_before))
    
    return RedactionMetadata(
        document_id=uuid4(),
        filename=draw(st.text(min_size=5, max_size=50, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=".-_"
        ))) + ".pdf",
        redaction_level=draw(st.sampled_from(list(RedactionLevel))),
        timestamp=datetime.now(timezone.utc),
        pii_instances=pii_instances,
        total_entities_redacted=num_instances,
        risk_score_before=risk_score_before,
        risk_score_after=risk_score_after,
    )


@st.composite
def aadhaar_strategy(draw):
    """
    Generate valid Aadhaar numbers in all 3 delimiter formats.
    
    Aadhaar format: 12 digits, first digit 2-9
    Formats:
    - Plain: 123456789012
    - Space: 1234 5678 9012
    - Hyphen: 1234-5678-9012
    """
    first_digit = draw(st.integers(min_value=2, max_value=9))
    remaining_digits = draw(st.integers(min_value=10000000000, max_value=99999999999))
    aadhaar_plain = f"{first_digit}{remaining_digits}"
    
    format_type = draw(st.sampled_from(["plain", "space", "hyphen"]))
    
    if format_type == "plain":
        return aadhaar_plain
    elif format_type == "space":
        return f"{aadhaar_plain[:4]} {aadhaar_plain[4:8]} {aadhaar_plain[8:]}"
    else:  # hyphen
        return f"{aadhaar_plain[:4]}-{aadhaar_plain[4:8]}-{aadhaar_plain[8:]}"


@st.composite
def pan_strategy(draw):
    """
    Generate valid PAN numbers.
    
    PAN format: 5 uppercase letters + 4 digits + 1 uppercase letter
    Example: ABCDE1234F
    """
    letters1 = "".join(draw(st.lists(
        st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        min_size=5,
        max_size=5
    )))
    digits = "".join(draw(st.lists(
        st.sampled_from("0123456789"),
        min_size=4,
        max_size=4
    )))
    letter2 = draw(st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    
    return f"{letters1}{digits}{letter2}"


@st.composite
def driving_license_strategy(draw):
    """
    Generate valid Indian Driving License numbers.
    
    DL format: 2 uppercase letters (state code) + 2 digits (RTO code) + 
               4 digits (year) + 7 digits (sequence)
    Example: MH01 2023 1234567 or MH012023123456
    """
    state_code = "".join(draw(st.lists(
        st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        min_size=2,
        max_size=2
    )))
    rto_code = draw(st.integers(min_value=10, max_value=99))
    year = draw(st.integers(min_value=2000, max_value=2026))
    sequence = draw(st.integers(min_value=1000000, max_value=9999999))
    
    # Randomly add spaces or not
    if draw(st.booleans()):
        return f"{state_code}{rto_code} {year} {sequence}"
    else:
        return f"{state_code}{rto_code}{year}{sequence}"


@st.composite
def document_with_pii_strategy(draw):
    """
    Generate (text, entities) pairs for testing redaction.
    
    Returns:
        tuple: (text: str, entities: list[dict])
    """
    # Generate base text
    base_text = draw(st.text(min_size=100, max_size=500))
    
    # Generate PII values to inject
    num_pii = draw(st.integers(min_value=1, max_value=5))
    entities = []
    
    text_parts = [base_text]
    current_offset = len(base_text)
    
    for _ in range(num_pii):
        pii_type = draw(st.sampled_from(["AADHAAR", "PAN", "DRIVING_LICENSE"]))
        
        if pii_type == "AADHAAR":
            pii_value = draw(aadhaar_strategy())
        elif pii_type == "PAN":
            pii_value = draw(pan_strategy())
        else:
            pii_value = draw(driving_license_strategy())
        
        # Add separator and PII value
        separator = " "
        text_parts.append(separator)
        text_parts.append(pii_value)
        
        start_offset = current_offset + len(separator)
        end_offset = start_offset + len(pii_value)
        
        entities.append({
            "entity_type": pii_type,
            "start_offset": start_offset,
            "end_offset": end_offset,
            "confidence": 0.9,
            "value": pii_value
        })
        
        current_offset = end_offset
    
    final_text = "".join(text_parts)
    
    return final_text, entities


# Pytest Fixtures


@pytest.fixture
def sample_redaction_metadata():
    """Sample RedactionMetadata for unit tests."""
    return RedactionMetadata(
        document_id=uuid4(),
        filename="test_document.pdf",
        redaction_level=RedactionLevel.FULL,
        timestamp=datetime.now(timezone.utc),
        pii_instances=[
            PIIInstanceRecord(
                entity_type="AADHAAR",
                original_value="1234 5678 9012",
                redacted_value="[REDACTED]",
                start_offset=10,
                end_offset=25,
                confidence=0.95,
            )
        ],
        total_entities_redacted=1,
        risk_score_before=85.0,
        risk_score_after=0.0,
    )
