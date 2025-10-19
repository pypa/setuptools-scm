from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeAlias, TypedDict, TypeVar, cast, get_type_hints

if sys.version_info >= (3, 11):
    from tomllib import loads as load_toml
else:
    from tomli import loads as load_toml


log = logging.getLogger(__name__)

TOML_RESULT: TypeAlias = dict[str, Any]
TOML_LOADER: TypeAlias = Callable[[str], TOML_RESULT]

# TypeVar for generic TypedDict support - the schema defines the return type
TSchema = TypeVar("TSchema", bound=TypedDict)  # type: ignore[valid-type]


class InvalidTomlError(ValueError):
    """Raised when TOML data cannot be parsed."""


class InvalidTomlSchemaError(ValueError):
    """Raised when TOML data does not conform to the expected schema."""


def read_toml_content(path: Path, default: TOML_RESULT | None = None) -> TOML_RESULT:
    try:
        data = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        if default is None:
            raise
        else:
            log.debug("%s missing, presuming default %r", path, default)
            return default
    else:
        try:
            return load_toml(data)
        except Exception as e:  # tomllib/tomli raise different decode errors
            raise InvalidTomlError(f"Invalid TOML in {path}") from e


class _CheatTomlData(TypedDict):
    cheat: dict[str, Any]


def _validate_against_schema(
    data: dict[str, Any],
    schema: type[TypedDict] | None,  # type: ignore[valid-type]
) -> dict[str, Any]:
    """Validate parsed TOML data against a TypedDict schema.

    Args:
        data: Parsed TOML data to validate
        schema: TypedDict class defining valid fields, or None to skip validation

    Returns:
        The validated data with invalid fields removed

    Raises:
        InvalidTomlSchemaError: If there are invalid fields (after logging warnings)
    """
    if schema is None:
        return data

    # Extract valid field names from the TypedDict
    try:
        valid_fields = frozenset(get_type_hints(schema).keys())
    except NameError as e:
        # If type hints can't be resolved, log warning and skip validation
        log.warning("Could not resolve type hints for schema validation: %s", e)
        return data

    # If the schema has no fields (empty TypedDict), skip validation
    if not valid_fields:
        return data

    invalid_fields = set(data.keys()) - valid_fields
    if invalid_fields:
        log.warning(
            "Invalid fields in TOML data: %s. Valid fields are: %s",
            sorted(invalid_fields),
            sorted(valid_fields),
        )
        # Remove invalid fields
        validated_data = {k: v for k, v in data.items() if k not in invalid_fields}
        return validated_data

    return data


def load_toml_or_inline_map(data: str | None, *, schema: type[TSchema]) -> TSchema:
    """Load toml data - with a special hack if only a inline map is given.

    Args:
        data: TOML string to parse, or None for empty dict
        schema: TypedDict class for schema validation.
               Invalid fields will be logged as warnings and removed.

    Returns:
        Parsed TOML data as a dictionary conforming to the schema type

    Raises:
        InvalidTomlError: If the TOML content is malformed
    """
    if not data:
        return {}  # type: ignore[return-value]
    try:
        if data[0] == "{":
            data = "cheat=" + data
            loaded: _CheatTomlData = cast(_CheatTomlData, load_toml(data))
            result = loaded["cheat"]
        else:
            result = load_toml(data)

        return _validate_against_schema(result, schema)  # type: ignore[return-value]
    except Exception as e:  # tomllib/tomli raise different decode errors
        # Don't re-wrap our own validation errors
        if isinstance(e, InvalidTomlSchemaError):
            raise
        raise InvalidTomlError("Invalid TOML content") from e
