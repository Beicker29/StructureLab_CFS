"""Public M7 normative-applicability and software-support API."""

from .applicability import evaluate_normative_applicability
from .constants import (
    NormativeConstant,
    S100ElasticConstants,
    S100_24_ELASTIC_CONSTANTS,
    S100_24_LRFD_COMPRESSION_RESISTANCE_FACTOR,
)
from .eligibility import evaluate_design_eligibility
from .enums import (
    DesignAction,
    DesignExecutionPurpose,
    SoftwareSupportStatus,
    StandardDocumentRole,
)
from .models import (
    ApplicabilityCheck,
    DesignEligibility,
    NormativeApplicabilityResult,
    SoftwareSupportCheck,
    SoftwareSupportResult,
    aggregate_normative_status,
    aggregate_software_status,
    make_applicability_check_id,
    make_software_check_id,
)
from .source_validation import (
    select_primary_standard_path,
    validate_standard_sources,
)
from .sources import (
    FUTURE_S240_20,
    FUTURE_S400_20,
    PREVIOUS_S100_16_S3_22,
    PRIMARY_S100_24,
    S100_24_STANDARD_EDITION,
    S100_24_STANDARD_ID,
    SOURCE_AUTHORITY_ORDER,
    STANDARD_SOURCE_REGISTRY,
    StandardDocument,
    StandardSourceRegistry,
    s100_24_reference,
)
from .support import (
    SOFTWARE_SCOPE_VERSION,
    SUPPORTED_DESIGN_ACTIONS,
    SUPPORTED_DESIGN_FORMATS,
    SUPPORTED_DESIGN_METHODS,
    SUPPORTED_SECTION_FAMILIES,
    UNSUPPORTED_V01_FEATURES,
    evaluate_software_support,
)

__all__ = [
    "ApplicabilityCheck",
    "DesignAction",
    "DesignExecutionPurpose",
    "DesignEligibility",
    "FUTURE_S240_20",
    "FUTURE_S400_20",
    "NormativeApplicabilityResult",
    "NormativeConstant",
    "PREVIOUS_S100_16_S3_22",
    "PRIMARY_S100_24",
    "S100_24_STANDARD_ID",
    "S100_24_STANDARD_EDITION",
    "S100_24_ELASTIC_CONSTANTS",
    "S100_24_LRFD_COMPRESSION_RESISTANCE_FACTOR",
    "S100ElasticConstants",
    "SOURCE_AUTHORITY_ORDER",
    "SOFTWARE_SCOPE_VERSION",
    "STANDARD_SOURCE_REGISTRY",
    "SUPPORTED_DESIGN_ACTIONS",
    "SUPPORTED_DESIGN_FORMATS",
    "SUPPORTED_DESIGN_METHODS",
    "SUPPORTED_SECTION_FAMILIES",
    "SoftwareSupportCheck",
    "SoftwareSupportResult",
    "SoftwareSupportStatus",
    "StandardDocument",
    "StandardDocumentRole",
    "StandardSourceRegistry",
    "UNSUPPORTED_V01_FEATURES",
    "aggregate_normative_status",
    "aggregate_software_status",
    "evaluate_design_eligibility",
    "evaluate_normative_applicability",
    "evaluate_software_support",
    "make_applicability_check_id",
    "make_software_check_id",
    "s100_24_reference",
    "select_primary_standard_path",
    "validate_standard_sources",
]
