"""PII detection service using Presidio with Indian Government ID support."""

import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry

from backend.core.config import settings
from backend.core.types import RiskBand
from backend.services.indian_id_recognizer import get_indian_id_recognizers

logger = logging.getLogger(__name__)


@dataclass
class PIIEntity:
    """Detected PII entity."""

    entity_type: str
    start_offset: int
    end_offset: int
    confidence: float
    subtype: str | None = None


@dataclass
class PIIDetectionResult:
    """Result of PII detection analysis."""

    entities: List[PIIEntity]
    risk_score: float
    risk_band: RiskBand
    entity_counts: Dict[str, int]
    risk_explanation: Dict = None  # type: ignore

    def __post_init__(self):
        if self.risk_explanation is None:
            self.risk_explanation = {}


class PIIDetector:
    """Service for detecting PII in text using Presidio."""

    # Risk score weights — use NORMALIZED entity type names (after _ENTITY_NORMALISE)
    # Increased weights for Indian Government IDs (Aadhaar, PAN, DL) — highest sensitivity
    ENTITY_WEIGHTS = {
        "AADHAAR":         25.0,  # Biometric national ID — highest risk
        "PAN":             20.0,  # Financial identity — very high risk
        "DRIVING_LICENSE": 20.0,  # Government ID — very high risk
        "EMAIL":            5.0,  # normalized from EMAIL_ADDRESS — lower risk
        "PHONE":            5.0,  # normalized from PHONE_NUMBER — lower risk
        "PERSON":           3.0,  # Name alone — lowest risk
    }

    # FIX: Request Presidio's actual entity names; normalise them after detection.
    _PRESIDIO_ENTITIES = [
        "AADHAAR",
        "PAN",
        "DRIVING_LICENSE",
        "EMAIL_ADDRESS",    # Presidio built-in name
        "PHONE_NUMBER",     # Presidio built-in name
        "PERSON",
    ]

    # Normalise Presidio entity names → our canonical names
    _ENTITY_NORMALISE = {
        "EMAIL_ADDRESS": "EMAIL",
        "PHONE_NUMBER": "PHONE",
    }

    def __init__(self):
        """Initialize PII detector with Presidio analyzer."""
        registry = RecognizerRegistry()
        # Load Presidio's built-in recognizers (Email, Phone, Person, etc.)
        registry.load_predefined_recognizers()
        # Add our custom Indian ID recognizers
        for recognizer in get_indian_id_recognizers():
            registry.add_recognizer(recognizer)
            logger.info(f"Registered recognizer: {recognizer.name}")
        self.analyzer = AnalyzerEngine(registry=registry)
        logger.info("PIIDetector initialized with Indian Government ID support")

    def detect(
        self, text: str, language: str = "en", confidence_threshold: float | None = None
    ) -> PIIDetectionResult:
        """Detect PII entities in text."""
        if confidence_threshold is None:
            confidence_threshold = settings.PII_CONFIDENCE_THRESHOLD

        results = self.analyzer.analyze(
            text=text,
            entities=self._PRESIDIO_ENTITIES,
            language=language,
        )

        filtered = [r for r in results if r.score >= confidence_threshold]

        entities: List[PIIEntity] = []
        for result in filtered:
            subtype = None
            if hasattr(result, "recognition_metadata") and result.recognition_metadata:
                subtype = result.recognition_metadata.get("subtype")

            entity_type = self._ENTITY_NORMALISE.get(result.entity_type, result.entity_type)

            entities.append(
                PIIEntity(
                    entity_type=entity_type,
                    start_offset=result.start,
                    end_offset=result.end,
                    confidence=result.score,
                    subtype=subtype,
                )
            )

        risk_score = self.calculate_risk_score(entities)
        risk_band = self._derive_risk_band(risk_score)
        entity_counts = self._count_entities_by_type(entities)
        risk_explanation = self.explain_risk(entities, risk_score)

        logger.info(
            f"Detected {len(entities)} PII entities "
            f"(risk score: {risk_score:.2f}, band: {risk_band.value})"
        )

        return PIIDetectionResult(
            entities=entities,
            risk_score=risk_score,
            risk_band=risk_band,
            entity_counts=entity_counts,
            risk_explanation=risk_explanation,
        )

    def _aggregate_by_type(self, entities: List[PIIEntity]) -> Dict[str, List[PIIEntity]]:
        aggregated: Dict[str, List[PIIEntity]] = defaultdict(list)
        for entity in entities:
            aggregated[entity.entity_type].append(entity)
        return dict(aggregated)

    # Sensitivity tiers — used for floor enforcement
    _SENSITIVITY = {
        "AADHAAR":         "CRITICAL",
        "PAN":             "HIGH",
        "DRIVING_LICENSE": "HIGH",
        "PHONE":           "MEDIUM",
        "EMAIL":           "LOW",
        "PERSON":          "LOW",
    }

    # Combination boosts — identity bundles that are more dangerous together
    _COMBINATION_BOOSTS = [
        ({"AADHAAR", "PAN"},             12),   # identity theft bundle
        ({"AADHAAR", "PAN", "DRIVING_LICENSE"}, 20),  # full KYC bundle
        ({"AADHAAR", "PHONE"},            5),   # account takeover risk
        ({"PAN", "DRIVING_LICENSE"},      8),   # financial identity bundle
    ]

    def calculate_risk_score(self, entities: List[PIIEntity]) -> float:
        """Calculate risk score with sensitivity boosts and combination awareness.

        Steps:
        1. Base: Σ_per_type(weight × avg_confidence × log2(1 + count))
        2. Diversity multiplier: 1 + 0.3 × (unique_types - 1)
        3. Critical entity boost: ×1.5 if AADHAAR present
        4. Combination boosts: flat additions for dangerous PII bundles
        5. Sensitivity floor: ensure CRITICAL-tier entities never score LOW
        6. Cap at 100
        """
        if not entities:
            return 0.0

        by_type = self._aggregate_by_type(entities)
        detected_types = set(by_type.keys())
        base_score = 0.0

        for entity_type, type_entities in by_type.items():
            weight = self.ENTITY_WEIGHTS.get(entity_type, 1.0)
            avg_confidence = sum(e.confidence for e in type_entities) / len(type_entities)
            count = len(type_entities)
            count_factor = math.log2(1 + count)
            type_score = weight * avg_confidence * count_factor
            base_score += type_score
            logger.debug(f"Risk from {entity_type}: {type_score:.2f}")

        # Diversity multiplier
        unique_types = len(by_type)
        diversity = 1.0 + 0.3 * (unique_types - 1)
        score = base_score * diversity

        # Critical entity boost — Aadhaar alone elevates risk significantly
        if "AADHAAR" in detected_types:
            score *= 1.5

        # Combination boosts — dangerous identity bundles
        for combo, boost in self._COMBINATION_BOOSTS:
            if combo.issubset(detected_types):
                score += boost
                logger.debug(f"Combination boost +{boost} for {combo}")

        # Sensitivity floor — CRITICAL-tier entity should never be LOW
        highest_tier = None
        for t in detected_types:
            tier = self._SENSITIVITY.get(t, "LOW")
            if tier == "CRITICAL":
                highest_tier = "CRITICAL"
                break
            elif tier == "HIGH" and highest_tier != "CRITICAL":
                highest_tier = "HIGH"

        if highest_tier == "CRITICAL":
            score = max(score, 30.0)   # AADHAAR alone → at least CRITICAL (score 30+)
        elif highest_tier == "HIGH":
            score = max(score, 15.0)   # PAN/DL alone → at least HIGH (score 15-30)

        final = min(score, 100.0)

        # Aadhaar alone is always HIGH/CRITICAL risk minimum — it's a biometric national ID
        if "AADHAAR" in detected_types:
            final = max(final, 30.0)  # floor at CRITICAL band minimum (30+)

        logger.debug(f"Risk: base={base_score:.2f} diversity={diversity:.2f} final={final:.2f}")
        return final

    def _derive_risk_band(self, risk_score: float) -> RiskBand:
        """Map score to band with aggressive thresholds for government IDs.

        Thresholds calibrated so:
          1 Aadhaar alone (score ~21)          → HIGH risk
          Aadhaar + PAN (score ~45)            → CRITICAL risk
          Full identity document               → CRITICAL risk
        
        Lower thresholds reflect that government IDs require immediate action.
        """
        if risk_score < 5:
            return RiskBand.LOW
        elif risk_score < 15:
            return RiskBand.MEDIUM
        elif risk_score < 30:
            return RiskBand.HIGH
        else:
            return RiskBand.CRITICAL

    def _count_entities_by_type(self, entities: List[PIIEntity]) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for entity in entities:
            counts[entity.entity_type] += 1
        return dict(counts)

    def explain_risk(self, entities: List[PIIEntity], final_score: float) -> Dict:
        """Generate human-readable risk explanation.

        Returns a dict with:
        - top_contributors: which PII types drove the score highest
        - diversity_note: whether multiple types amplified the score
        - summary: one-line explanation
        """
        if not entities:
            return {"summary": "No PII detected.", "top_contributors": [], "diversity_note": None}

        by_type = self._aggregate_by_type(entities)
        unique_types = len(by_type)

        contributors = []
        for entity_type, type_entities in sorted(
            by_type.items(),
            key=lambda x: self.ENTITY_WEIGHTS.get(x[0], 1.0),
            reverse=True,
        ):
            weight = self.ENTITY_WEIGHTS.get(entity_type, 1.0)
            contributors.append({
                "type": entity_type,
                "count": len(type_entities),
                "weight": weight,
                "sensitivity": "Very High" if weight >= 9 else "High" if weight >= 6 else "Medium" if weight >= 4 else "Low",
            })

        diversity_note = None
        if unique_types > 1:
            diversity_note = (
                f"{unique_types} different PII types detected — "
                f"diversity multiplier ×{1 + 0.3 * (unique_types - 1):.1f} applied"
            )

        top = contributors[0]
        summary = (
            f"Score driven primarily by {top['type']} ({top['sensitivity']} sensitivity)"
        )
        if unique_types > 1:
            summary += f" combined with {unique_types - 1} other type(s)"

        return {
            "summary": summary,
            "top_contributors": contributors,
            "diversity_note": diversity_note,
            "unique_types": unique_types,
        }
