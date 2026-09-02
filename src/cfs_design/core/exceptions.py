"""Base exceptions shared by future StructureLab_CFS layers."""


class CFSDesignError(Exception):
    """Base class for all expected package errors."""


class ConfigurationError(CFSDesignError):
    """Raised when project configuration is missing, invalid, or inconsistent."""


class ValidationError(CFSDesignError):
    """Raised when supplied data fails an explicit validation rule."""


class CatalogError(CFSDesignError):
    """Raised for catalog access or catalog-content errors."""


class SchemaError(CFSDesignError):
    """Raised when an input does not conform to its declared schema."""


class ETABSImportError(CFSDesignError):
    """Raised when native ETABS data cannot be read or normalized safely."""


class UnsupportedFeatureError(CFSDesignError):
    """Raised when a requested feature is outside implemented software support."""


class StandardSourceError(ConfigurationError):
    """Raised when registered engineering-standard sources fail validation."""


__all__ = [
    "CFSDesignError",
    "CatalogError",
    "ConfigurationError",
    "ETABSImportError",
    "SchemaError",
    "StandardSourceError",
    "UnsupportedFeatureError",
    "ValidationError",
]
