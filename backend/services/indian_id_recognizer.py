"""Indian Government ID recognizers for Presidio PII detection."""

import logging
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult
from presidio_analyzer.predefined_recognizers import InPanRecognizer

logger = logging.getLogger(__name__)


class AadhaarAliasRecognizer(PatternRecognizer):
    """Aadhaar recognizer supporting all delimiter formats.

    Supports:
      plain:  123456789012
      space:  1234 5678 9012
      hyphen: 1234-5678-9012

    Note: Presidio's built-in InAadhaarRecognizer only matches 12 consecutive
    digits (no spaces/hyphens), so we use our own patterns here.
    """

    PATTERNS = [
        Pattern(
            name="aadhaar_spaced",
            regex=r"\b[2-9][0-9]{3}\s[0-9]{4}\s[0-9]{4}\b",
            score=0.85,
        ),
        Pattern(
            name="aadhaar_hyphen",
            regex=r"\b[2-9][0-9]{3}-[0-9]{4}-[0-9]{4}\b",
            score=0.85,
        ),
        Pattern(
            name="aadhaar_plain",
            regex=r"\b[2-9][0-9]{11}\b",
            score=0.6,
        ),
    ]

    CONTEXT_WORDS = [
        "aadhaar", "aadhar", "uid", "uidai", "unique identification",
        "government of india", "भारत सरकार",
    ]

    def __init__(self):
        super().__init__(
            supported_entity="AADHAAR",
            patterns=self.PATTERNS,
            context=self.CONTEXT_WORDS,
            supported_language="en",
            name="AadhaarAliasRecognizer",
        )

    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        if "AADHAAR" not in entities:
            return []
        try:
            results = super().analyze(text, entities, nlp_artifacts)
        except TypeError:
            results = super().analyze(text, entities)
        for result in results:
            if not hasattr(result, "recognition_metadata") or result.recognition_metadata is None:
                result.recognition_metadata = {}
            result.recognition_metadata["subtype"] = "IndianGovtID"
        logger.debug(f"Detected {len(results)} Aadhaar numbers")
        return results


class PANAliasRecognizer(InPanRecognizer):
    """Renames IN_PAN → PAN and injects IndianGovtID subtype.

    PAN format: [A-Z]{5}[0-9]{4}[A-Z]   e.g. ABCDE1234F
    """

    def __init__(self):
        super().__init__()
        self.supported_entities = ["PAN"]
        self.name = "PANAliasRecognizer"

    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        if "PAN" not in entities:
            return []
        try:
            results = super().analyze(text, ["IN_PAN"], nlp_artifacts)
        except TypeError:
            results = super().analyze(text, ["IN_PAN"])
        for result in results:
            result.entity_type = "PAN"
            if not hasattr(result, "recognition_metadata") or result.recognition_metadata is None:
                result.recognition_metadata = {}
            result.recognition_metadata["subtype"] = "IndianGovtID"
        logger.debug(f"Detected {len(results)} PAN numbers")
        return results


class DrivingLicenseRecognizer(PatternRecognizer):
    """Indian Driving License recognizer.

    Format:  {state_code:2}{rto:2}[optional 1-2 letters]{year:4}{seq:7}
    Examples:
      MH02 2023 1234567
      MH02 AB 2019 1234567 (with initials)
      MH-02-AB-2019-1234567
      DL14 2022 9876543

    Context words boost confidence to reduce false positives from
    alphanumeric product codes.
    """

    PATTERNS = [
        # MH02 AB 2019 1234567 (with optional initials + spaces)
        Pattern(
            name="dl_spaced_with_initials",
            regex=r"\b[A-Z]{2}[0-9]{2}\s[A-Z]{1,2}\s[0-9]{4}\s[0-9]{7}\b",
            score=0.8,
        ),
        # MH02 2019 1234567 (no initials, spaces)
        Pattern(
            name="dl_spaced",
            regex=r"\b[A-Z]{2}[0-9]{2}\s[0-9]{4}\s[0-9]{7}\b",
            score=0.75,
        ),
        # MH-02-AB-2019-1234567 (4 hyphen segments with initials)
        Pattern(
            name="dl_hyphen4_with_initials",
            regex=r"\b[A-Z]{2}-[0-9]{2}-[A-Z]{1,2}-[0-9]{4}-[0-9]{7}\b",
            score=0.8,
        ),
        # MH-02-2019-1234567 (4 hyphen segments no initials)
        Pattern(
            name="dl_hyphen4",
            regex=r"\b[A-Z]{2}-[0-9]{2}-[0-9]{4}-[0-9]{7}\b",
            score=0.75,
        ),
        # MH-02-20191234567 or MH-02AB20191234567 (3 hyphen segments)
        Pattern(
            name="dl_hyphen3",
            regex=r"\b[A-Z]{2}-[0-9]{2}[A-Z]{0,2}-[0-9]{11}\b",
            score=0.7,
        ),
        # MH02AB20191234567 (no separator)
        Pattern(
            name="dl_plain",
            regex=r"\b[A-Z]{2}[0-9]{2}[A-Z]{0,2}[0-9]{4}[0-9]{7}\b",
            score=0.65,
        ),
    ]

    CONTEXT_WORDS = [
        "DL",
        "driving licence",
        "driving license",
        "license no",
        "licence no",
        "dl no",
        "driver",
        "transport",
    ]

    def __init__(self):
        super().__init__(
            supported_entity="DRIVING_LICENSE",
            patterns=self.PATTERNS,
            context=self.CONTEXT_WORDS,
            supported_language="en",
            name="DrivingLicenseRecognizer",
        )

    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        if "DRIVING_LICENSE" not in entities:
            return []
        # FIX: PatternRecognizer.analyze filters by supported_entity internally;
        # pass the full list so the parent's guard doesn't skip us.
        try:
            results = super().analyze(text, entities, nlp_artifacts)
        except TypeError:
            results = super().analyze(text, entities)
        for result in results:
            if not hasattr(result, "recognition_metadata") or result.recognition_metadata is None:
                result.recognition_metadata = {}
            result.recognition_metadata["subtype"] = "IndianGovtID"
        logger.debug(f"Detected {len(results)} Driving License numbers")
        return results


def get_indian_id_recognizers() -> List[PatternRecognizer]:
    """Return all Indian Government ID recognizers."""
    return [
        AadhaarAliasRecognizer(),
        PANAliasRecognizer(),
        DrivingLicenseRecognizer(),
    ]
