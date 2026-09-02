"""Public M3A/M3B section-mechanics API."""

from .advanced_properties import compute_advanced_properties
from .design_properties import ResolvedSectionMechanics
from .builder import build_centerline_section
from .centerline import CenterlineSection
from .gross_properties import compute_gross_properties
from .models import (
    AdvancedPropertyMethod,
    AdvancedSectionProperties,
    CatalogVerificationResult,
    ComputedSectionProperties,
    ExtremeFiberMethod,
    GeometryMethod,
    GrossPropertyMethod,
    PropertyVerification,
    SectorialNode,
    SectorialProperties,
    VerificationPolicy,
    VerificationProperty,
    VerificationStatus,
)
from .primitives import Point2D, StraightSegment
from .verification import verify_catalog_properties

__all__ = [
    "AdvancedPropertyMethod",
    "AdvancedSectionProperties",
    "ResolvedSectionMechanics",
    "CatalogVerificationResult",
    "CenterlineSection",
    "ComputedSectionProperties",
    "ExtremeFiberMethod",
    "GeometryMethod",
    "GrossPropertyMethod",
    "Point2D",
    "PropertyVerification",
    "SectorialNode",
    "SectorialProperties",
    "StraightSegment",
    "VerificationPolicy",
    "VerificationProperty",
    "VerificationStatus",
    "build_centerline_section",
    "compute_gross_properties",
    "compute_advanced_properties",
    "verify_catalog_properties",
]
