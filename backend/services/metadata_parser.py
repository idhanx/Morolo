"""Redaction metadata parsing and pretty printing services."""

import json
import logging
from typing import Any

from pydantic import ValidationError

from backend.api.schemas import RedactionMetadata

logger = logging.getLogger(__name__)


class RedactionMetadataParser:
    """Parser for redaction metadata JSON."""

    @staticmethod
    def parse(json_str: str) -> RedactionMetadata:
        """Parse a JSON string into a RedactionMetadata object.

        Raises:
            ValueError: if the JSON is malformed or fails schema validation.

        (FIX: was re-raising ValidationError(str) which is invalid in
        Pydantic v2 — ValidationError requires an errors list, not a
        plain string message.)
        """
        try:
            return RedactionMetadata.model_validate_json(json_str)
        except ValidationError as e:
            msg = f"Invalid redaction metadata: {e.error_count()} validation error(s)"
            logger.error(f"{msg}: {e}")
            raise ValueError(msg) from e
        except json.JSONDecodeError as e:
            msg = f"Malformed JSON: {e}"
            logger.error(msg)
            raise ValueError(msg) from e


class RedactionMetadataPrettyPrinter:
    """Pretty printer for redaction metadata."""

    @staticmethod
    def pretty_print(metadata: RedactionMetadata) -> str:
        """Serialise RedactionMetadata to a pretty-printed, sorted JSON string.

        Uses json.dumps(metadata.model_dump(mode="json"), ...) — the correct
        Pydantic v2 approach. model_dump(mode="json") converts UUID/datetime/Enum
        to JSON-native types before json.dumps handles them.
        """
        data_dict = metadata.model_dump(mode="json")
        return json.dumps(data_dict, indent=2, sort_keys=True)
