"""Redaction engine for PII masking with multiple strategies."""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List
from uuid import UUID

from faker import Faker

from backend.core.types import RedactionLevel
from backend.services.pii_detector import PIIEntity

logger = logging.getLogger(__name__)


@dataclass
class RedactionResult:
    """Result of redaction operation."""

    redacted_text: str
    # SHA-256(original_value) -> redacted_value  (for audit trail)
    audit_mapping: Dict[str, str]
    entities_redacted: int
    # FIX: store the per-entity offset→hash mapping so generate_report can
    # look up the redacted value for a given entity without re-hashing "".
    # Key: "{start_offset}:{end_offset}", Value: SHA-256(original_value)
    offset_to_hash: Dict[str, str] = field(default_factory=dict)


class RedactionEngine:
    """Engine for redacting PII from text using various strategies."""

    def __init__(self):
        self.faker = Faker()
        from backend.services.indian_id_provider import IndianIDProvider
        self.faker.add_provider(IndianIDProvider)

    def redact(
        self,
        text: str,
        entities: List[PIIEntity],
        level: RedactionLevel,
    ) -> RedactionResult:
        """Redact PII entities from text.

        Algorithm:
        1. Sort entities by start_offset descending (process end → start
           to avoid offset shifts on earlier spans).
        2. For each entity, extract original value and apply redaction.
        3. Build audit_mapping: SHA-256(original) → redacted_value.
        4. Build offset_to_hash so generate_report can retrieve
           the redacted value per entity without storing originals.
        """
        if not entities:
            return RedactionResult(
                redacted_text=text,
                audit_mapping={},
                entities_redacted=0,
            )

        sorted_entities = sorted(entities, key=lambda e: e.start_offset, reverse=True)

        redacted_text = text
        audit_mapping: Dict[str, str] = {}
        offset_to_hash: Dict[str, str] = {}

        for entity in sorted_entities:
            original_value = text[entity.start_offset : entity.end_offset]

            if level == RedactionLevel.LIGHT:
                redacted_value = self._apply_light_redaction(original_value)
            elif level == RedactionLevel.FULL:
                redacted_value = self._apply_full_redaction(original_value)
            elif level == RedactionLevel.SYNTHETIC:
                redacted_value = self._apply_synthetic_redaction(original_value, entity.entity_type)
            else:
                raise ValueError(f"Unknown redaction level: {level}")

            redacted_text = (
                redacted_text[: entity.start_offset]
                + redacted_value
                + redacted_text[entity.end_offset :]
            )

            original_hash = hashlib.sha256(original_value.encode()).hexdigest()
            audit_mapping[original_hash] = redacted_value

            # FIX: record the hash for this span so generate_report can find it
            span_key = f"{entity.start_offset}:{entity.end_offset}"
            offset_to_hash[span_key] = original_hash

            logger.debug(
                f"Redacted {entity.entity_type} at "
                f"{entity.start_offset}-{entity.end_offset} "
                f"using {level.value} strategy"
            )

        return RedactionResult(
            redacted_text=redacted_text,
            audit_mapping=audit_mapping,
            entities_redacted=len(entities),
            offset_to_hash=offset_to_hash,
        )

    def _apply_light_redaction(self, value: str) -> str:
        """Preserve first 2 + last 2 chars, mask middle with *.

        Falls back to FULL for values shorter than 5 chars.

        Examples:
          "1234567890" → "12******90"
          "ABCDE1234F" → "AB******4F"
          "1234"       → "[REDACTED]"
        """
        if len(value) < 5:
            return "[REDACTED]"
        middle_length = len(value) - 4
        return f"{value[:2]}{'*' * middle_length}{value[-2:]}"

    def _apply_full_redaction(self, value: str) -> str:
        """Replace entire value with [REDACTED]."""
        return "[REDACTED]"

    def _apply_synthetic_redaction(self, value: str, entity_type: str) -> str:
        """Replace with a format-matching synthetic value using Faker + IndianIDProvider."""
        try:
            if entity_type == "AADHAAR":
                if "-" in value:
                    return self.faker.aadhaar(format="hyphen")
                elif " " in value:
                    return self.faker.aadhaar(format="space")
                else:
                    return self.faker.aadhaar(format="plain")
            elif entity_type == "PAN":
                return self.faker.pan()
            elif entity_type == "DRIVING_LICENSE":
                return self.faker.driving_license()
            elif entity_type in ("EMAIL_ADDRESS", "EMAIL"):
                return self.faker.email()
            elif entity_type in ("PHONE_NUMBER", "PHONE"):
                return self.faker.phone_number()
            elif entity_type == "PERSON":
                return self.faker.name()
            else:
                logger.warning(f"Unknown entity type for synthetic redaction: {entity_type}")
                return "[REDACTED]"
        except Exception as e:
            logger.error(f"Synthetic redaction failed for {entity_type}: {e}")
            return "[REDACTED]"

    def generate_report(
        self,
        job_id: UUID,
        filename: str,
        redaction_level: RedactionLevel,
        result: RedactionResult,
        entities: List[PIIEntity],
        risk_score_before: float,
        risk_score_after: float,
    ) -> Dict:
        """Generate redaction report JSON.

        FIX: use offset_to_hash to retrieve the correct redacted_value
        per entity instead of hashing the empty string "".
        """
        pii_instances = []
        for entity in entities:
            span_key = f"{entity.start_offset}:{entity.end_offset}"
            original_hash = result.offset_to_hash.get(span_key)
            redacted_value = (
                result.audit_mapping.get(original_hash, "[REDACTED]")
                if original_hash
                else "[REDACTED]"
            )
            pii_instances.append({
                "entity_type": entity.entity_type,
                "start_offset": entity.start_offset,
                "end_offset": entity.end_offset,
                "confidence": entity.confidence,
                "redacted_value": redacted_value,
            })

        return {
            "document_id": str(job_id),
            "filename": filename,
            "redaction_level": redaction_level.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pii_instances": pii_instances,
            "total_entities_redacted": result.entities_redacted,
            "risk_score_before": risk_score_before,
            "risk_score_after": risk_score_after,
            "audit_mapping_count": len(result.audit_mapping),
        }
