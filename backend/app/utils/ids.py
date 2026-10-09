import uuid

from .errors import ApiError


def parse_uuid(value, field="id") -> str:
    """Return the canonical lowercase UUID string or raise a 422."""
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        raise ApiError(422, "invalid_id", f"'{field}' must be a valid UUID") from None
