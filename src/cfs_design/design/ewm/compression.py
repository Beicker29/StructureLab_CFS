"""S100-24 LRFD EWM axial-compression resistance orchestration."""

from math import isfinite

from cfs_design.core.exceptions import ValidationError
from cfs_design.design.global_compression import (
    GLOBAL_SLENDERNESS_TRANSITION,
    SECTION_SYMMETRY_I_XY_ABSOLUTE_TOLERANCE_MM4,
    SECTION_SYMMETRY_Y0_ABSOLUTE_TOLERANCE_MM,
    calculate_global_column_strength,
    require_singly_symmetric_c,
)
from cfs_design.design.inputs import MemberDesignInput
from cfs_design.domain import DesignFormat, DesignMethod, SectionFamily
from cfs_design.normative import (
    DesignAction,
    PRIMARY_S100_24,
    S100_24_ELASTIC_CONSTANTS,
    S100_24_LRFD_COMPRESSION_RESISTANCE_FACTOR,
    S100_24_STANDARD_EDITION,
    S100_24_STANDARD_ID,
    SoftwareSupportStatus,
)
from cfs_design.results import (
    ApplicabilityStatus,
    CalculationStatus,
    CalculationStep,
    CalculationTrace,
    DiagnosticSeverity,
    EngineeringDiagnostic,
    EngineeringUnit,
    EngineeringValue,
    EquationReference,
    LimitStateId,
    MetadataEntry,
    ReferenceSourceType,
    make_step_id,
    make_trace_id,
)

from ._validation import EWMCalculationError, positive, positive_result
from .e4 import calculate_distortional_buckling, calculate_e4_strength
from .effective_area import calculate_effective_area
from .effective_width import (
    calculate_simple_lip_effective_width,
    calculate_stiffened_effective_width,
    calculate_unstiffened_effective_width,
)
from .global_buckling import calculate_global_buckling
from .interpretations import S10024_A1_1_3A_XREF_001
from .models import (
    EWMCompressionResistance,
    EffectiveWidthResult,
    GlobalColumnStrength,
    NominalLimitState,
    NominalStrengthCandidate,
    PlateElementId,
)


LRFD_COMPRESSION_RESISTANCE_FACTOR = (
    S100_24_LRFD_COMPRESSION_RESISTANCE_FACTOR.value.value
)
_TRACE_LIMIT_STATE = LimitStateId(
    "EWM_AXIAL_COMPRESSION",
    "S100-24 LRFD EWM concentric axial-compression resistance",
)


def _standard_reference(
    *, clause: str, equation_id: str | None, title: str, notes: str | None = None
) -> EquationReference:
    source_note = (
        f"source_id={PRIMARY_S100_24.source_id}; sha256={PRIMARY_S100_24.sha256}"
    )
    return EquationReference(
        source_type=ReferenceSourceType.STANDARD,
        standard_id=S100_24_STANDARD_ID,
        edition=S100_24_STANDARD_EDITION,
        clause=clause,
        equation_id=equation_id,
        title=title,
        notes=source_note if notes is None else f"{source_note}; {notes}",
    )


def _value(
    name: str,
    value: float,
    unit: EngineeringUnit,
    symbol: str | None = None,
) -> EngineeringValue:
    return EngineeringValue(name=name, value=value, unit=unit, symbol=symbol)


def calculate_local_global_strength(
    *, effective_area_mm2: float, fn_mpa: float, p_ne_n: float
) -> float:
    """Apply S100-24 Eq. E3.1-1 and retain its Pne upper limit."""

    area = positive(effective_area_mm2, "Ae")
    stress = positive(fn_mpa, "Fn")
    global_nominal = positive(p_ne_n, "Pne")
    return positive_result(min(area * stress, global_nominal), "Pnl")


def _diagnostic(code: str, message: str) -> EngineeringDiagnostic:
    return EngineeringDiagnostic(
        severity=DiagnosticSeverity.ERROR,
        code=code,
        message=message,
    )


def _empty_result(
    design_input: MemberDesignInput,
    *,
    calculation_status: CalculationStatus,
    diagnostic: EngineeringDiagnostic,
) -> EWMCompressionResistance:
    case_id = design_input.resolved_member.member.case_id
    trace_id = make_trace_id(
        case_id=case_id,
        method=DesignMethod.EWM,
        limit_state=_TRACE_LIMIT_STATE,
    )
    diagnostics = design_input.eligibility.diagnostics + (diagnostic,)
    trace = CalculationTrace(
        trace_id=trace_id,
        status=calculation_status,
        case_id=case_id,
        method=DesignMethod.EWM,
        limit_state=_TRACE_LIMIT_STATE,
        diagnostics=diagnostics,
        metadata=(
            MetadataEntry("standard_id", design_input.design_context.standard_id),
            MetadataEntry(
                "standard_edition", design_input.design_context.standard_edition
            ),
        ),
    )
    return EWMCompressionResistance(
        case_id=case_id,
        calculation_status=calculation_status,
        applicability_status=design_input.eligibility.normative.status,
        global_buckling=None,
        global_column_strength=None,
        effective_width_elements=(),
        effective_area=None,
        e4_result=None,
        candidate_strengths=(),
        governing_limit_state=None,
        nominal_strength_n=None,
        resistance_factor=None,
        design_strength_n=None,
        trace=trace,
        diagnostics=diagnostics,
    )


def _preflight_diagnostic(
    design_input: MemberDesignInput,
) -> EngineeringDiagnostic | None:
    context = design_input.design_context
    if design_input.method is not DesignMethod.EWM:
        return _diagnostic("EWM_METHOD_REQUIRED", "EWM resistance requires method EWM")
    if design_input.action is not DesignAction.AXIAL_COMPRESSION:
        return _diagnostic(
            "EWM_AXIAL_COMPRESSION_REQUIRED",
            "M8B resistance supports axial compression only",
        )
    if (
        context.standard_id != S100_24_STANDARD_ID
        or context.standard_edition != S100_24_STANDARD_EDITION
    ):
        return _diagnostic(
            "EWM_STANDARD_UNSUPPORTED",
            "M8B resistance supports ANSI/SDI AISI S100-2024 only",
        )
    if context.design_format is not DesignFormat.LRFD:
        return _diagnostic(
            "EWM_FORMAT_UNSUPPORTED", "M8B resistance supports LRFD only"
        )
    if design_input.eligibility.normative.status is not ApplicabilityStatus.APPLICABLE:
        return _diagnostic(
            "EWM_NOT_NORMATIVELY_APPLICABLE",
            "normative applicability must be APPLICABLE before resistance execution",
        )
    if design_input.eligibility.software.status is not SoftwareSupportStatus.SUPPORTED:
        return _diagnostic(
            "EWM_SOFTWARE_UNSUPPORTED",
            "software support must be SUPPORTED before resistance execution",
        )
    if not design_input.executable:
        return _diagnostic(
            "EWM_DESIGN_INPUT_NOT_EXECUTABLE", "MemberDesignInput is not executable"
        )
    if design_input.standard_dimensions is None:
        return _diagnostic(
            "EWM_MISSING_DIMENSIONS",
            "explicit S100-24 StandardSectionDimensions are required",
        )
    if design_input.material_qualification is None:
        return _diagnostic(
            "EWM_MISSING_MATERIAL_QUALIFICATION",
            "qualified A3 material evidence is required",
        )
    if not design_input.section_mechanics.design_use_permitted:
        return _diagnostic(
            "EWM_QA_GATE_FAILED",
            "the coherent M3 mechanics set is blocked by project QA",
        )
    return None


def _require_singly_symmetric_c(design_input: MemberDesignInput) -> None:
    require_singly_symmetric_c(
        design_input.resolved_member.section.geometry,
        design_input.section_mechanics,
        error_code="EWM_GLOBAL_NONSYMMETRIC_UNSUPPORTED",
        owner="M8B",
    )


def _calculate_elements(
    design_input: MemberDesignInput, fn_mpa: float
) -> tuple[EffectiveWidthResult, ...]:
    dimensions = design_input.standard_dimensions
    if dimensions is None:
        raise EWMCalculationError(
            "EWM_MISSING_DIMENSIONS", "S100-24 dimensions are required"
        )
    geometry = design_input.resolved_member.section.geometry
    thickness = geometry.t_mm
    web = calculate_stiffened_effective_width(
        element_id=PlateElementId.WEB,
        width_mm=dimensions.web_flat_width_mm,
        thickness_mm=thickness,
        stress_mpa=fn_mpa,
    )
    if geometry.section_type is SectionFamily.C_UNLIPPED:
        return (
            web,
            calculate_unstiffened_effective_width(
                element_id=PlateElementId.FLANGE_1,
                width_mm=dimensions.flange_1_flat_width_mm,
                thickness_mm=thickness,
                stress_mpa=fn_mpa,
            ),
            calculate_unstiffened_effective_width(
                element_id=PlateElementId.FLANGE_2,
                width_mm=dimensions.flange_2_flat_width_mm,
                thickness_mm=thickness,
                stress_mpa=fn_mpa,
            ),
        )
    lipped_values = (
        dimensions.lip_1_flat_width_mm,
        dimensions.lip_2_flat_width_mm,
        dimensions.lip_1_overall_depth_mm,
        dimensions.lip_2_overall_depth_mm,
        geometry.flange_lip_angle_deg,
    )
    if any(value is None for value in lipped_values):
        raise EWMCalculationError(
            "EWM_MISSING_DIMENSIONS",
            "complete simple-lip dimensions and angle are required",
        )
    flange_1, lip_1 = calculate_simple_lip_effective_width(
        flange_element_id=PlateElementId.FLANGE_1,
        lip_element_id=PlateElementId.LIP_1,
        flange_flat_width_mm=dimensions.flange_1_flat_width_mm,
        lip_flat_width_mm=dimensions.lip_1_flat_width_mm,  # type: ignore[arg-type]
        lip_overall_depth_mm=dimensions.lip_1_overall_depth_mm,  # type: ignore[arg-type]
        thickness_mm=thickness,
        stress_mpa=fn_mpa,
        lip_angle_deg=geometry.flange_lip_angle_deg,  # type: ignore[arg-type]
    )
    flange_2, lip_2 = calculate_simple_lip_effective_width(
        flange_element_id=PlateElementId.FLANGE_2,
        lip_element_id=PlateElementId.LIP_2,
        flange_flat_width_mm=dimensions.flange_2_flat_width_mm,
        lip_flat_width_mm=dimensions.lip_2_flat_width_mm,  # type: ignore[arg-type]
        lip_overall_depth_mm=dimensions.lip_2_overall_depth_mm,  # type: ignore[arg-type]
        thickness_mm=thickness,
        stress_mpa=fn_mpa,
        lip_angle_deg=geometry.flange_lip_angle_deg,  # type: ignore[arg-type]
    )
    return web, flange_1, flange_2, lip_1, lip_2


def _build_trace(
    design_input: MemberDesignInput,
    *,
    global_buckling,
    global_strength,
    elements,
    effective_area,
    p_nl_n: float,
    e4_result,
    candidates,
    governing,
    nominal_strength_n: float,
    design_strength_n: float,
) -> CalculationTrace:
    case_id = design_input.resolved_member.member.case_id
    trace_id = make_trace_id(
        case_id=case_id, method=DesignMethod.EWM, limit_state=_TRACE_LIMIT_STATE
    )
    steps: list[CalculationStep] = []

    def add(
        name: str,
        results: tuple[EngineeringValue, ...],
        *,
        inputs: tuple[EngineeringValue, ...] = (),
        reference: EquationReference | None = None,
        description: str | None = None,
        expression: str | None = None,
    ) -> None:
        steps.append(
            CalculationStep(
                step_id=make_step_id(trace_id, len(steps) + 1),
                name=name,
                inputs=inputs,
                results=results,
                reference=reference,
                description=description,
                expression=expression,
            )
        )

    member = design_input.resolved_member
    geometry = member.section.geometry
    gross = design_input.section_mechanics.gross
    advanced = design_input.section_mechanics.advanced
    material = member.material
    dimensions = design_input.standard_dimensions
    assert dimensions is not None
    add(
        "Resolved eligibility",
        (_value("eligible", 1.0, EngineeringUnit.DIMENSIONLESS),),
        reference=_standard_reference(
            clause="A1.1; A1.2.3; A3; B4.1",
            equation_id="Table B4.1-1",
            title="M8B eligibility boundary",
        ),
    )
    member_restraint_values = [
        _value(
            "member_length",
            member.member.geometry.l_mm,
            EngineeringUnit.MILLIMETRE,
            "L",
        )
    ]
    distortional_length = (
        member.member.restraints.distortional_unbraced_length_mm
    )
    if distortional_length is not None:
        member_restraint_values.append(
            _value(
                "distortional_length",
                distortional_length,
                EngineeringUnit.MILLIMETRE,
                "Lm",
            )
        )
    add(
        "Member geometry and restraints",
        tuple(member_restraint_values),
        description=(
            "Lm is recorded independently and is never substituted for a global length."
        ),
    )
    add(
        "Coherent M3 design mechanics",
        (
            _value("gross_area", gross.a_mm2, EngineeringUnit.SQUARE_MILLIMETRE, "Ag"),
            _value("ix", gross.ix_mm4, EngineeringUnit.FOURTH_POWER_MILLIMETRE, "Ix"),
            _value("iy", gross.iy_mm4, EngineeringUnit.FOURTH_POWER_MILLIMETRE, "Iy"),
            _value("ixy", gross.ixy_mm4, EngineeringUnit.FOURTH_POWER_MILLIMETRE, "Ixy"),
            _value("j", gross.j_mm4, EngineeringUnit.FOURTH_POWER_MILLIMETRE, "J"),
            _value("cw", advanced.cw_mm6, EngineeringUnit.SIXTH_POWER_MILLIMETRE, "Cw"),
            _value("x0", advanced.x0_mm, EngineeringUnit.MILLIMETRE, "x0"),
            _value("y0", advanced.y0_mm, EngineeringUnit.MILLIMETRE, "y0"),
        ),
        reference=EquationReference(
            source_type=ReferenceSourceType.MECHANICS,
            title="M3A/M3B coherent computed-property set",
        ),
    )
    add(
        "S100-24 elastic constants",
        (
            _value(
                "elastic_modulus",
                S100_24_ELASTIC_CONSTANTS.elastic_modulus.value.value,
                EngineeringUnit.MEGAPASCAL,
                "E",
            ),
            _value(
                "shear_modulus",
                S100_24_ELASTIC_CONSTANTS.shear_modulus.value.value,
                EngineeringUnit.MEGAPASCAL,
                "G",
            ),
            _value(
                "poisson_ratio",
                S100_24_ELASTIC_CONSTANTS.poisson_ratio.value.value,
                EngineeringUnit.DIMENSIONLESS,
                "mu",
            ),
        ),
        reference=_standard_reference(
            clause="Symbols; Appendix 2 Section 2.3.1",
            equation_id=None,
            title="Prescribed elastic constants",
        ),
    )
    add(
        "Resolved material strengths",
        (
            _value("yield_stress", material.fy_mpa, EngineeringUnit.MEGAPASCAL, "Fy"),
            _value("tensile_strength", material.fu_mpa, EngineeringUnit.MEGAPASCAL, "Fu"),
        ),
        reference=_standard_reference(
            clause="E2", equation_id="E2-4", title="Yield stress input"
        ),
    )
    lengths = global_buckling.effective_lengths
    add(
        "Global effective lengths",
        (
            _value("effective_length_x", lengths.lx_mm, EngineeringUnit.MILLIMETRE, "KxLx"),
            _value("effective_length_y", lengths.ly_mm, EngineeringUnit.MILLIMETRE, "KyLy"),
            _value("effective_length_t", lengths.lt_mm, EngineeringUnit.MILLIMETRE, "KtLt"),
        ),
        reference=_standard_reference(
            clause="Appendix 2 Section 2.3.1",
            equation_id=None,
            title="Global effective-length definitions",
        ),
        description=f"Length source: {lengths.source}",
    )
    add(
        "Global elastic buckling loads",
        (
            _value("polar_radius", global_buckling.ro_mm, EngineeringUnit.MILLIMETRE, "ro"),
            _value("p_ex", global_buckling.p_ex_n, EngineeringUnit.NEWTON, "Pex"),
            _value("p_ey", global_buckling.p_ey_n, EngineeringUnit.NEWTON, "Pey"),
            _value("p_t", global_buckling.p_t_n, EngineeringUnit.NEWTON, "Pt"),
            _value("beta", global_buckling.beta, EngineeringUnit.DIMENSIONLESS, "beta"),
            _value("p_flexural", global_buckling.p_flexural_n, EngineeringUnit.NEWTON),
            _value("p_flexural_torsional", global_buckling.p_flexural_torsional_n, EngineeringUnit.NEWTON),
            _value("p_cre", global_buckling.p_cre_n, EngineeringUnit.NEWTON, "Pcre"),
            _value("f_cre", global_buckling.f_cre_mpa, EngineeringUnit.MEGAPASCAL, "Fcre"),
        ),
        reference=_standard_reference(
            clause=(
                "Appendix 2 Sections 2.3.1, 2.3.1.1, 2.3.1.1.1, 2.3.1.1.2"
            ),
            equation_id=(
                "2.3.1-1 to 2.3.1-4; 2.3.1-7; 2.3.1.1-1; "
                "2.3.1.1.1-1; 2.3.1.1.2-1"
            ),
            title="Singly symmetric C global buckling",
        ),
        description=f"Governing elastic mode: {global_buckling.governing_mode.value}",
    )
    add(
        "E2 global column strength",
        (
            _value("lambda_c", global_strength.lambda_c, EngineeringUnit.DIMENSIONLESS, "lambda_c"),
            _value("fn", global_strength.fn_mpa, EngineeringUnit.MEGAPASCAL, "Fn"),
            _value("p_ne", global_strength.p_ne_n, EngineeringUnit.NEWTON, "Pne"),
        ),
        reference=_standard_reference(
            clause="E2",
            equation_id="E2-1 through E2-4",
            title="Yielding and global compression strength",
        ),
        description=f"Column-curve branch: {global_strength.branch.value}",
    )
    dimension_values = [
        _value("web_flat_width", dimensions.web_flat_width_mm, EngineeringUnit.MILLIMETRE),
        _value("flange_1_flat_width", dimensions.flange_1_flat_width_mm, EngineeringUnit.MILLIMETRE),
        _value("flange_2_flat_width", dimensions.flange_2_flat_width_mm, EngineeringUnit.MILLIMETRE),
        _value("thickness", geometry.t_mm, EngineeringUnit.MILLIMETRE, "t"),
    ]
    if dimensions.has_lipped_dimensions:
        dimension_values.extend(
            (
                _value("web_out_to_out_depth", dimensions.web_out_to_out_depth_mm, EngineeringUnit.MILLIMETRE, "ho"),  # type: ignore[arg-type]
                _value("lip_1_flat_width", dimensions.lip_1_flat_width_mm, EngineeringUnit.MILLIMETRE),  # type: ignore[arg-type]
                _value("lip_2_flat_width", dimensions.lip_2_flat_width_mm, EngineeringUnit.MILLIMETRE),  # type: ignore[arg-type]
                _value("lip_1_overall_depth", dimensions.lip_1_overall_depth_mm, EngineeringUnit.MILLIMETRE, "D1"),  # type: ignore[arg-type]
                _value("lip_2_overall_depth", dimensions.lip_2_overall_depth_mm, EngineeringUnit.MILLIMETRE, "D2"),  # type: ignore[arg-type]
            )
        )
    add(
        "Explicit AISI dimensions",
        tuple(dimension_values),
        reference=_standard_reference(
            clause="B4.1; Appendix 1",
            equation_id="Table B4.1-1",
            title="Standard-specific dimensions",
        ),
        description="No dimensional value in this step is inferred from MIDLINE geometry.",
    )
    interpretation_applied = any(
        element.interpretation_id == S10024_A1_1_3A_XREF_001.interpretation_id
        for element in elements
    )
    if interpretation_applied:
        interpretation = S10024_A1_1_3A_XREF_001
        add(
            "Controlled no-hole cross-reference interpretation",
            (_value("interpretation_applied", 1.0, EngineeringUnit.DIMENSIONLESS),),
            reference=EquationReference(
                source_type=ReferenceSourceType.OTHER,
                title=interpretation.interpretation_id,
                notes=(
                    f"status={interpretation.status.value}; "
                    f"published={interpretation.published_reference}; "
                    f"interpreted={interpretation.interpreted_reference}; "
                    f"rationale={interpretation.technical_rationale}; "
                    f"corroboration={interpretation.corroborating_reference}; "
                    f"section_type={interpretation.applicable_section_type}; "
                    f"restriction={interpretation.restriction}; "
                    f"project={interpretation.project}; "
                    f"decision_date={interpretation.decision_date}; "
                    f"supersession={interpretation.supersession_rule}"
                ),
            ),
            description="Project-controlled interpretation; not an official AISI erratum.",
        )
    for element in elements:
        results = [
            _value("full_width", element.full_width_mm, EngineeringUnit.MILLIMETRE, "w"),
            _value("effective_width", element.effective_width_mm, EngineeringUnit.MILLIMETRE, "b"),
        ]
        optional_values = (
            ("plate_coefficient", element.plate_coefficient, EngineeringUnit.DIMENSIONLESS, "k"),
            ("f_crl", element.f_crl_mpa, EngineeringUnit.MEGAPASCAL, "Fcrl"),
            ("plate_slenderness", element.slenderness, EngineeringUnit.DIMENSIONLESS, "lambda"),
            ("reduction_factor", element.reduction_factor, EngineeringUnit.DIMENSIONLESS, "rho"),
            ("flange_b1", element.flange_b1_mm, EngineeringUnit.MILLIMETRE, "b1"),
            ("flange_b2", element.flange_b2_mm, EngineeringUnit.MILLIMETRE, "b2"),
            ("s_parameter", element.s_parameter, EngineeringUnit.DIMENSIONLESS, "S"),
            ("ia", element.ia_mm4, EngineeringUnit.FOURTH_POWER_MILLIMETRE, "Ia"),
            ("is", element.is_mm4, EngineeringUnit.FOURTH_POWER_MILLIMETRE, "Is"),
            ("stiffener_ratio", element.stiffener_ratio, EngineeringUnit.DIMENSIONLESS, "RI"),
            ("exponent_n", element.exponent_n, EngineeringUnit.DIMENSIONLESS, "n"),
            ("d_over_w", element.d_over_w, EngineeringUnit.DIMENSIONLESS, "D/w"),
        )
        for name, optional_value, unit, symbol in optional_values:
            if optional_value is not None:
                results.append(_value(name, optional_value, unit, symbol))
        if element.element_id is PlateElementId.WEB:
            clause = "Appendix 1 Section 1.1(a)"
            equation = "1.1-1 through 1.1-4"
        elif geometry.section_type is SectionFamily.C_UNLIPPED:
            clause = "Appendix 1 Sections 1.1(a), 1.2.1(a)"
            equation = "1.1-1 through 1.1-4; k=0.43"
        elif element.element_id in {PlateElementId.LIP_1, PlateElementId.LIP_2}:
            clause = "Appendix 1 Sections 1.2.1(a), 1.3(a)"
            equation = (
                "1.3-3; 1.2.1(a); 1.1-1 through 1.1-4"
                if element.ia_mm4 == 0.0
                else "1.3-6; 1.3-9; 1.2.1(a); 1.1-1 through 1.1-4"
            )
        elif element.interpretation_id is None:
            clause = "Appendix 1 Section 1.3(a)"
            equation = "1.3-1 through 1.3-3; 1.3-7"
        else:
            clause = (
                "Appendix 1 Section 1.3(a); controlled interpretation "
                "S10024-A1-1_3A-XREF-001"
            )
            equation = (
                "1.3-1 through 1.3-11; Table 1.3-1; "
                "1.1-1 through 1.1-4"
            )
        add(
            f"Effective width {element.element_id.value}",
            tuple(results),
            reference=_standard_reference(
                clause=clause,
                equation_id=equation,
                title=element.classification.value,
            ),
            description=(
                f"Element identity and classification: {element.element_id.value}; "
                f"{element.classification.value}"
            ),
        )
    add(
        "E3.1 effective area",
        tuple(
            [
                _value(
                    "effective_area",
                    effective_area.ae_mm2,
                    EngineeringUnit.SQUARE_MILLIMETRE,
                    "Ae",
                )
            ]
            + [
                _value(
                    f"area_{item.element_id.value.lower()}",
                    item.area_mm2,
                    EngineeringUnit.SQUARE_MILLIMETRE,
                )
                for item in effective_area.contributions
            ]
        ),
        reference=_standard_reference(
            clause="E3.1",
            equation_id="text following E3.1-1",
            title="Element-by-element effective area",
        ),
    )
    add(
        "E3.1 local-global nominal strength",
        (_value("p_nl", p_nl_n, EngineeringUnit.NEWTON, "Pnl"),),
        inputs=(
            _value("effective_area_input", effective_area.ae_mm2, EngineeringUnit.SQUARE_MILLIMETRE, "Ae"),
            _value("fn_input", global_strength.fn_mpa, EngineeringUnit.MEGAPASCAL, "Fn"),
            _value("p_ne_limit", global_strength.p_ne_n, EngineeringUnit.NEWTON, "Pne"),
        ),
        reference=_standard_reference(
            clause="E3.1",
            equation_id="E3.1-1",
            title="Local buckling interacting with global buckling",
        ),
    )
    if e4_result is not None:
        flange = e4_result.buckling.flange
        add(
            "Appendix 2 distortional flange properties",
            (
                _value("af", flange.af_mm2, EngineeringUnit.SQUARE_MILLIMETRE, "Af"),
                _value("jf", flange.jf_mm4, EngineeringUnit.FOURTH_POWER_MILLIMETRE, "Jf"),
                _value("ixf", flange.ixf_mm4, EngineeringUnit.FOURTH_POWER_MILLIMETRE, "Ixf"),
                _value("iyf", flange.iyf_mm4, EngineeringUnit.FOURTH_POWER_MILLIMETRE, "Iyf"),
                _value("ixyf", flange.ixyf_mm4, EngineeringUnit.FOURTH_POWER_MILLIMETRE, "Ixyf"),
                _value("cwf", flange.cwf_mm6, EngineeringUnit.SIXTH_POWER_MILLIMETRE, "Cwf"),
                _value("xof", flange.xof_mm, EngineeringUnit.MILLIMETRE, "xof"),
                _value("xhf", flange.xhf_mm, EngineeringUnit.MILLIMETRE, "xhf"),
                _value("yof", flange.yof_mm, EngineeringUnit.MILLIMETRE, "yof"),
                _value("yhf", flange.yhf_mm, EngineeringUnit.MILLIMETRE, "yhf"),
            ),
            reference=_standard_reference(
                clause="Appendix 2 Section 2.3.3.1",
                equation_id="Table 2.3.3-1",
                title="Orthogonal flange-plus-lip properties",
            ),
        )
        buckling = e4_result.buckling
        add(
            "Appendix 2 analytical distortional buckling",
            (
                _value("l_crd", buckling.l_crd_mm, EngineeringUnit.MILLIMETRE, "Lcrd"),
                _value("l_m", buckling.l_m_mm, EngineeringUnit.MILLIMETRE, "Lm"),
                _value("l_d", buckling.l_d_mm, EngineeringUnit.MILLIMETRE, "Ld"),
                _value("k_phi_fe", buckling.k_phi_fe_n, EngineeringUnit.NEWTON),
                _value("k_phi_we", buckling.k_phi_we_n, EngineeringUnit.NEWTON),
                _value("k_phi", buckling.k_phi_n, EngineeringUnit.NEWTON),
                _value("k_phi_fg", buckling.k_phi_fg_mm2, EngineeringUnit.SQUARE_MILLIMETRE),
                _value("k_phi_wg", buckling.k_phi_wg_mm2, EngineeringUnit.SQUARE_MILLIMETRE),
                _value("f_crd", buckling.f_crd_mpa, EngineeringUnit.MEGAPASCAL, "Fcrd"),
                _value("p_crd", buckling.p_crd_n, EngineeringUnit.NEWTON, "Pcrd"),
            ),
            reference=_standard_reference(
                clause="Appendix 2 Section 2.3.3.1",
                equation_id="2.3.3.1-1 through 2.3.3.1-7",
                title="Analytical compression distortional buckling",
            ),
            description=(
                "Continuous rotational stiffness k_phi is conservatively taken "
                "as zero under Section 2.3.3.1."
            ),
        )
        add(
            "E4 distortional nominal strength",
            (
                _value("p_y", e4_result.p_y_n, EngineeringUnit.NEWTON, "Py"),
                _value("lambda_d", e4_result.lambda_d, EngineeringUnit.DIMENSIONLESS, "lambda_d"),
                _value("p_nd", e4_result.p_nd_n, EngineeringUnit.NEWTON, "Pnd"),
            ),
            reference=_standard_reference(
                clause="E4",
                equation_id="E4-1 through E4-3",
                title="Distortional compression strength",
            ),
        )
    add(
        "Nominal strength candidates",
        tuple(
            _value(
                f"candidate_{item.limit_state.value.lower()}",
                item.nominal_strength_n,
                EngineeringUnit.NEWTON,
            )
            for item in candidates
        ),
        reference=_standard_reference(
            clause="E1; E2; E3.1; E4 where applicable",
            equation_id=None,
            title="Applicable nominal candidates",
        ),
    )
    add(
        "Governing nominal strength",
        (_value("nominal_strength", nominal_strength_n, EngineeringUnit.NEWTON, "Pn"),),
        reference=_standard_reference(
            clause="E1", equation_id=None, title="Smallest applicable axial strength"
        ),
        description=f"Governing limit state: {governing.value}",
    )
    add(
        "LRFD design strength",
        (
            _value("resistance_factor", LRFD_COMPRESSION_RESISTANCE_FACTOR, EngineeringUnit.DIMENSIONLESS, "phi_c"),
            _value("design_strength", design_strength_n, EngineeringUnit.NEWTON, "phi_c Pn"),
        ),
        reference=_standard_reference(
            clause="E2; E3; E4",
            equation_id="stated LRFD factor",
            title="Compression resistance factor",
        ),
        expression="design_strength = resistance_factor * nominal_strength",
    )
    return CalculationTrace(
        trace_id=trace_id,
        status=CalculationStatus.COMPLETED,
        steps=tuple(steps),
        final_values=(
            _value("nominal_strength", nominal_strength_n, EngineeringUnit.NEWTON, "Pn"),
            _value("resistance_factor", LRFD_COMPRESSION_RESISTANCE_FACTOR, EngineeringUnit.DIMENSIONLESS, "phi_c"),
            _value("design_strength", design_strength_n, EngineeringUnit.NEWTON, "phi_c Pn"),
        ),
        case_id=case_id,
        method=DesignMethod.EWM,
        limit_state=_TRACE_LIMIT_STATE,
        metadata=(
            MetadataEntry("standard_id", S100_24_STANDARD_ID),
            MetadataEntry("standard_edition", S100_24_STANDARD_EDITION),
            MetadataEntry("standard_sha256", PRIMARY_S100_24.sha256),
            MetadataEntry("section_id", design_input.section_mechanics.section_id),
            MetadataEntry("dimension_source", dimensions.source_id),
            MetadataEntry("material_id", material.material_id),
            MetadataEntry("method", DesignMethod.EWM.value),
            MetadataEntry("action", DesignAction.AXIAL_COMPRESSION.value),
            MetadataEntry("governing_limit_state", governing.value),
            MetadataEntry(
                "controlled_interpretation_id",
                S10024_A1_1_3A_XREF_001.interpretation_id
                if interpretation_applied
                else None,
            ),
            MetadataEntry(
                "controlled_interpretation_status",
                S10024_A1_1_3A_XREF_001.status.value
                if interpretation_applied
                else None,
            ),
            MetadataEntry("holes_supported", False),
        ),
    )


def calculate_ewm_compression_resistance(
    design_input: MemberDesignInput,
) -> EWMCompressionResistance:
    """Calculate S100-24 LRFD EWM concentric compression resistance."""

    if not isinstance(design_input, MemberDesignInput):
        raise ValidationError("design_input must be MemberDesignInput")
    preflight = _preflight_diagnostic(design_input)
    if preflight is not None:
        return _empty_result(
            design_input,
            calculation_status=CalculationStatus.NOT_RUN,
            diagnostic=preflight,
        )
    try:
        _require_singly_symmetric_c(design_input)
        member = design_input.resolved_member
        mechanics = design_input.section_mechanics
        gross = mechanics.gross
        material = member.material
        global_buckling = calculate_global_buckling(
            member.member.geometry, mechanics
        )
        global_strength = calculate_global_column_strength(
            gross_area_mm2=gross.a_mm2,
            yield_stress_mpa=material.fy_mpa,
            f_cre_mpa=global_buckling.f_cre_mpa,
        )
        elements = _calculate_elements(design_input, global_strength.fn_mpa)
        effective_area = calculate_effective_area(
            elements=elements,
            thickness_mm=member.section.geometry.t_mm,
            gross_area_mm2=gross.a_mm2,
        )
        p_nl = calculate_local_global_strength(
            effective_area_mm2=effective_area.ae_mm2,
            fn_mpa=global_strength.fn_mpa,
            p_ne_n=global_strength.p_ne_n,
        )
        e4_result = None
        nominal_values = [
            (NominalLimitState.E2_YIELDING_GLOBAL, global_strength.p_ne_n),
            (NominalLimitState.E3_1_LOCAL_GLOBAL, p_nl),
        ]
        if member.section.geometry.section_type is SectionFamily.C_LIPPED:
            dimensions = design_input.standard_dimensions
            restraints = member.member.restraints
            geometry = member.section.geometry
            if (
                dimensions is None
                or dimensions.web_out_to_out_depth_mm is None
                or geometry.d1_mm is None
                or restraints.distortional_unbraced_length_mm is None
                or restraints.distortional_restraint_source is None
            ):
                raise EWMCalculationError(
                    "EWM_E4_LM_REQUIRED",
                    "analytical E4 requires explicit dimensions, Lm, and Lm provenance",
                )
            distortional = calculate_distortional_buckling(
                flange_midline_width_mm=geometry.b1_mm,
                lip_midline_width_mm=geometry.d1_mm,
                web_out_to_out_depth_mm=dimensions.web_out_to_out_depth_mm,
                thickness_mm=geometry.t_mm,
                gross_area_mm2=gross.a_mm2,
                distortional_unbraced_length_mm=(
                    restraints.distortional_unbraced_length_mm
                ),
            )
            e4_result = calculate_e4_strength(
                buckling=distortional,
                gross_area_mm2=gross.a_mm2,
                yield_stress_mpa=material.fy_mpa,
            )
            nominal_values.append(
                (NominalLimitState.E4_DISTORTIONAL, e4_result.p_nd_n)
            )
        candidates = tuple(
            NominalStrengthCandidate(
                limit_state=limit_state,
                nominal_strength_n=value,
                resistance_factor=LRFD_COMPRESSION_RESISTANCE_FACTOR,
                design_strength_n=value * LRFD_COMPRESSION_RESISTANCE_FACTOR,
            )
            for limit_state, value in nominal_values
        )
        governing_candidate = min(
            candidates, key=lambda item: item.nominal_strength_n
        )
        nominal_strength = positive_result(
            governing_candidate.nominal_strength_n, "Pn"
        )
        design_strength = positive_result(
            LRFD_COMPRESSION_RESISTANCE_FACTOR * nominal_strength,
            "phi_c Pn",
        )
        if not all(isfinite(value) for value in (nominal_strength, design_strength)):
            raise EWMCalculationError(
                "EWM_NONFINITE_VALUE", "final resistance is nonfinite"
            )
        trace = _build_trace(
            design_input,
            global_buckling=global_buckling,
            global_strength=global_strength,
            elements=elements,
            effective_area=effective_area,
            p_nl_n=p_nl,
            e4_result=e4_result,
            candidates=candidates,
            governing=governing_candidate.limit_state,
            nominal_strength_n=nominal_strength,
            design_strength_n=design_strength,
        )
        return EWMCompressionResistance(
            case_id=member.member.case_id,
            calculation_status=CalculationStatus.COMPLETED,
            applicability_status=ApplicabilityStatus.APPLICABLE,
            global_buckling=global_buckling,
            global_column_strength=global_strength,
            effective_width_elements=elements,
            effective_area=effective_area,
            e4_result=e4_result,
            candidate_strengths=candidates,
            governing_limit_state=governing_candidate.limit_state,
            nominal_strength_n=nominal_strength,
            resistance_factor=LRFD_COMPRESSION_RESISTANCE_FACTOR,
            design_strength_n=design_strength,
            trace=trace,
        )
    except EWMCalculationError as error:
        return _empty_result(
            design_input,
            calculation_status=CalculationStatus.FAILED,
            diagnostic=_diagnostic(error.code, str(error)),
        )
    except ArithmeticError as error:
        return _empty_result(
            design_input,
            calculation_status=CalculationStatus.FAILED,
            diagnostic=_diagnostic("EWM_NUMERICAL_FAILURE", str(error)),
        )


__all__ = [
    "GLOBAL_SLENDERNESS_TRANSITION",
    "LRFD_COMPRESSION_RESISTANCE_FACTOR",
    "SECTION_SYMMETRY_I_XY_ABSOLUTE_TOLERANCE_MM4",
    "SECTION_SYMMETRY_Y0_ABSOLUTE_TOLERANCE_MM",
    "calculate_ewm_compression_resistance",
    "calculate_global_column_strength",
    "calculate_local_global_strength",
]
