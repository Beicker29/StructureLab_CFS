"""Element-by-element S100-24 E3.1 effective-area assembly."""

from math import fsum

from ._validation import EWMCalculationError, positive, positive_result
from .models import (
    EffectiveAreaContribution,
    EffectiveAreaResult,
    EffectiveWidthResult,
)


EFFECTIVE_AREA_ABSOLUTE_TOLERANCE_MM2 = 1.0e-9
EFFECTIVE_AREA_RELATIVE_TOLERANCE = 1.0e-12


def calculate_effective_area(
    *,
    elements: tuple[EffectiveWidthResult, ...],
    thickness_mm: float,
    gross_area_mm2: float,
) -> EffectiveAreaResult:
    """Sum thickness times effective element width as required by E3.1."""

    if not elements:
        raise EWMCalculationError(
            "EWM_EFFECTIVE_AREA_ELEMENTS_REQUIRED",
            "effective area requires at least one plate element",
        )
    identities = tuple(element.element_id for element in elements)
    if len(set(identities)) != len(identities):
        raise EWMCalculationError(
            "EWM_EFFECTIVE_AREA_DUPLICATE_ELEMENT",
            "effective-area element identities must be unique",
        )
    thickness = positive(thickness_mm, "t")
    gross_area = positive(gross_area_mm2, "Ag")
    contributions = tuple(
        EffectiveAreaContribution(
            element_id=element.element_id,
            effective_width_mm=element.effective_width_mm,
            thickness_mm=thickness,
            area_mm2=positive_result(
                element.effective_width_mm * thickness,
                f"{element.element_id.value} effective area",
            ),
        )
        for element in elements
    )
    effective_area = positive_result(
        fsum(item.area_mm2 for item in contributions),
        "Ae",
    )
    tolerance = max(
        EFFECTIVE_AREA_ABSOLUTE_TOLERANCE_MM2,
        EFFECTIVE_AREA_RELATIVE_TOLERANCE * gross_area,
    )
    if effective_area - gross_area > tolerance:
        raise EWMCalculationError(
            "EWM_EFFECTIVE_AREA_EXCEEDS_GROSS",
            "element-by-element effective area exceeds M3 gross area",
        )
    return EffectiveAreaResult(
        contributions=contributions,
        ae_mm2=effective_area,
        ag_mm2=gross_area,
    )


__all__ = [
    "EFFECTIVE_AREA_ABSOLUTE_TOLERANCE_MM2",
    "EFFECTIVE_AREA_RELATIVE_TOLERANCE",
    "calculate_effective_area",
]
