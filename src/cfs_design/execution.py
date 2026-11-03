"""In-memory execution for the CLI and a future web app. Nothing is written to disk here."""
from typing import Any

import pydantic

from .engine import run_member
from .errors import ValidationError
from .models import MemberInput


def parse_member(payload: dict[str, Any]) -> MemberInput:
    try:
        return MemberInput.model_validate(payload)
    except pydantic.ValidationError as error:
        issues = [{"loc": ".".join(str(p) for p in e["loc"]), "msg": e["msg"]} for e in error.errors()]
        raise ValidationError("invalid member input", details={"issues": issues}) from None


def execute_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate one member payload and return its JSON-ready result. Raises CfsDesignError on invalid input."""
    return run_member(parse_member(payload)).model_dump(mode="json")
