"""Structured errors. The engine turns blocking errors into INCOMPLETE checks with their reason."""
from typing import Any


class CfsDesignError(Exception):
    """Base error with a stable code and structured details."""

    default_code = "CFS_DESIGN_ERROR"

    def __init__(self, message: str, *, code: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code or self.default_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.__class__.__name__, "code": self.code, "message": str(self), "details": self.details}


class ValidationError(CfsDesignError):
    """Invalid or inconsistent input."""

    default_code = "VALIDATION_ERROR"


class MaterialNotFoundError(CfsDesignError):
    """The material name is not in data/Materiales.xlsx."""

    default_code = "MATERIAL_NOT_FOUND"


class SectionNotFoundError(CfsDesignError):
    """The section name is not in data/Sections.xlsx."""

    default_code = "SECTION_NOT_FOUND"


class CatalogSchemaError(CfsDesignError):
    """A catalog sheet or header does not match the expected schema."""

    default_code = "CATALOG_SCHEMA_ERROR"


class RuleNotImplementedError(CfsDesignError):
    """A provision required for the demand is not implemented yet."""

    default_code = "RULE_NOT_IMPLEMENTED"


class IncompleteDataError(CfsDesignError):
    """A provision applies but a required datum (Fu, Lm, Cb, ...) is missing."""

    default_code = "INCOMPLETE_DATA"


class OutOfMethodScopeError(CfsDesignError):
    """The member is outside the scope of the requested method: Table B4.1-1 limits (B4.2 is not automated)
    or a DSM slenderness above its limit (no extrapolation). The check status is OUT_OF_METHOD_SCOPE."""

    default_code = "OUT_OF_METHOD_SCOPE"


BLOCKING_ERRORS: tuple[type[CfsDesignError], ...] = (RuleNotImplementedError, IncompleteDataError, OutOfMethodScopeError)
