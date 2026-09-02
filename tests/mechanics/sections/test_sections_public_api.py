"""Public section-mechanics API and M3A/M3B scope-boundary checks."""

import cfs_design.mechanics as mechanics
import cfs_design.mechanics.sections as sections


def test_useful_section_mechanics_functions_are_public() -> None:
    expected = {
        "CenterlineSection",
        "ComputedSectionProperties",
        "AdvancedSectionProperties",
        "SectorialProperties",
        "VerificationPolicy",
        "build_centerline_section",
        "compute_gross_properties",
        "compute_advanced_properties",
        "verify_catalog_properties",
    }
    assert expected <= set(sections.__all__)
    assert expected <= set(mechanics.__all__)


def test_m3b_does_not_expose_bends_or_design_engines() -> None:
    public_names = set(sections.__all__)
    assert "CircularArc" not in public_names
    assert "Cw" not in public_names
    assert "EWMResult" not in public_names
    assert "DSMResult" not in public_names
