"""UTC timestamp normalization shared by importers and metrics."""

import math
from datetime import UTC, datetime


def timestamp(value) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("Timestamps must include a timezone")
        return value.timestamp()
    if isinstance(value, str):
        try:
            return timestamp(float(value))
        except ValueError:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return timestamp(parsed)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Timestamp must be finite")
    return number


def iso_utc(value: float) -> str:
    return datetime.fromtimestamp(value, UTC).isoformat().replace("+00:00", "Z")
