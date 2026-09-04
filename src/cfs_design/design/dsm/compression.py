"""S100-24 LRFD DSM axial-compression resistance orchestration."""

from math import isfinite

from cfs_design.core.exceptions import ValidationError
from cfs_design.design._validation import EngineeringCalculationError
from cfs_design.design.global_compression import (
    calculate_global_buckling,
    calculate_global_column_strength,
    require_singly_symmetric_c,
)
from cfs_design.design.inputs import MemberDesignInput
from cfs_design.domain import DesignFormat, DesignMethod, SectionFamily
from cfs_design.normative import (
    DesignAction,
    PRIMARY_S100_24,
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
from cfs_design.stability import (
    BucklingModeFamily,
    ClassificationStatus,
    ElasticBucklingModeResult,
    ElasticBucklingResult,
)

from .equations import (
    DSMCalculationError,
    calculate_dsm_distortional_strength,
    calculate_dsm_local_strength,
    select_dsm_nominal_strength,
)
from .models import (
    DSMCompressionResistance,
    DSMDesignReadiness,
    DSMDistortionalBranch,
    DSMElasticBucklingProvenance,
    DSMElasticInputBasis,
    DSMGoverningLimitState,
    M9AUnavailable,
)


LRFD_COMPRESSION_RESISTANCE_FACTOR = (
    S100_24_LRFD_COMPRESSION_RESISTANCE_FACTOR.value.value
)
_TRACE_LIMIT_STATE = LimitStateId(
    "DSM_AXIAL_COMPRESSION",
    "S100-24 LRFD DSM concentric axial-compression resistance",
)


class _M9AReviewRequired(Exception):
    pass


class _M9AUnsupported(Exception):
    pass


def _reference(
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


_REF_E1 = _reference(
    clause="E1",
    equation_id=None,
    title="Smallest applicable axial-compression strength",
)
_REF_E2 = _reference(
    clause="E2",
    equation_id="E2-1 through E2-4",
    title="Yielding and global column strength",
)
_REF_APP2_GLOBAL = _reference(
    clause="Appendix 2 Sections 2.3.1 and 2.3.1.1",
    equation_id="2.3.1-1 through 2.3.1-7; 2.3.1.1.2-1",
    title="Elastic global compression buckling",
)
_REF_APP2_NUMERICAL = _reference(
    clause="Appendix 2 Sections 2.1 and 2.2",
    equation_id="2.1-1",
    title="Numerical local and distortional elastic buckling forces",
)
_REF_E3_2 = _reference(
    clause="E3.2",
    equation_id="E3.2-1 and E3.2-2",
    title="DSM local buckling interacting with yielding and global buckling",
    notes="Implemented no-hole branch; specified range lambda_l <= 5.",
)
_REF_E4 = _reference(
    clause="E4",
    equation_id="E4-1 through E4-3",
    title="DSM distortional buckling",
    notes="Implemented no-hole branch; specified range lambda_d <= 5.",
)
_REF_PHI = S100_24_LRFD_COMPRESSION_RESISTANCE_FACTOR.reference


def _value(
    name: str,
    value: float,
    unit: EngineeringUnit,
    symbol: str | None = None,
) -> EngineeringValue:
    return EngineeringValue(name=name, value=value, unit=unit, symbol=symbol)


def _diagnostic(
    code: str,
    message: str,
    *,
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
    context: tuple[MetadataEntry, ...] = (),
) -> EngineeringDiagnostic:
    return EngineeringDiagnostic(
        severity=severity,
        code=code,
        message=message,
        context=context,
    )


def _equation_references(*, distortional_applicable: bool) -> tuple[EquationReference, ...]:
    references = (
        _REF_E1,
        _REF_E2,
        _REF_APP2_GLOBAL,
        _REF_APP2_NUMERICAL,
        _REF_E3_2,
    )
    if distortional_applicable:
        references += (_REF_E4,)
    return references + (_REF_PHI,)


def _empty_result(
    design_input: MemberDesignInput,
    *,
    readiness: DSMDesignReadiness,
    calculation_status: CalculationStatus,
    diagnostic: EngineeringDiagnostic,
) -> DSMCompressionResistance:
    case_id = design_input.resolved_member.member.case_id
    diagnostics = design_input.eligibility.diagnostics + (diagnostic,)
    trace_id = make_trace_id(
        case_id=case_id,
        method=DesignMethod.DSM,
        limit_state=_TRACE_LIMIT_STATE,
    )
    trace = CalculationTrace(
        trace_id=trace_id,
        status=calculation_status,
        case_id=case_id,
        method=DesignMethod.DSM,
        limit_state=_TRACE_LIMIT_STATE,
        diagnostics=diagnostics,
        metadata=(
            MetadataEntry("standard_id", design_input.design_context.standard_id),
            MetadataEntry(
                "standard_edition", design_input.design_context.standard_edition
            ),
            MetadataEntry("design_readiness", readiness.value),
        ),
    )
    return DSMCompressionResistance(
        case_id=case_id,
        standard_id=design_input.design_context.standard_id,
        standard_edition=design_input.design_context.standard_edition,
        design_method=DesignMethod.DSM,
        design_format=design_input.design_context.design_format,
        calculation_status=calculation_status,
        design_readiness=readiness,
        applicability_status=design_input.eligibility.normative.status,
        software_support_status=design_input.eligibility.software.status,
        global_buckling=None,
        global_column_strength=None,
        p_y_n=None,
        p_crl_n=None,
        lambda_l=None,
        p_nl_n=None,
        local_branch=None,
        p_crd_n=None,
        lambda_d=None,
        p_nd_n=None,
        distortional_branch=None,
        nominal_strength_n=None,
        resistance_factor=None,
        design_strength_n=None,
        governing_limit_state=None,
        local_buckling_provenance=None,
        distortional_buckling_provenance=None,
        elastic_input_basis=None,
        equation_references=_equation_references(
            distortional_applicable=(
                design_input.resolved_member.section.catalog_section.family
                is SectionFamily.C_LIPPED
            )
        ),
        trace=trace,
        diagnostics=diagnostics,
    )


def _preflight(
    design_input: MemberDesignInput,
) -> tuple[DSMDesignReadiness, EngineeringDiagnostic] | None:
    context = design_input.design_context
    if design_input.method is not DesignMethod.DSM:
        return DSMDesignReadiness.INVALID_INPUT, _diagnostic(
            "DSM_METHOD_REQUIRED", "M9B resistance requires method DSM"
        )
    if design_input.action is not DesignAction.AXIAL_COMPRESSION:
        return DSMDesignReadiness.UNSUPPORTED, _diagnostic(
            "DSM_AXIAL_COMPRESSION_REQUIRED",
            "M9B supports axial compression only",
        )
    if (
        context.standard_id != S100_24_STANDARD_ID
        or context.standard_edition != S100_24_STANDARD_EDITION
    ):
        return DSMDesignReadiness.UNSUPPORTED, _diagnostic(
            "DSM_STANDARD_UNSUPPORTED",
            "M9B supports ANSI/SDI AISI S100-2024 only",
        )
    if context.design_format is not DesignFormat.LRFD:
        return DSMDesignReadiness.UNSUPPORTED, _diagnostic(
            "DSM_FORMAT_UNSUPPORTED", "M9B supports LRFD only"
        )
    if design_input.eligibility.normative.status is not ApplicabilityStatus.APPLICABLE:
        readiness = (
            DSMDesignReadiness.INVALID_INPUT
            if design_input.eligibility.normative.status
            is ApplicabilityStatus.INVALID_INPUT
            else DSMDesignReadiness.UNSUPPORTED
        )
        return readiness, _diagnostic(
            "DSM_NOT_NORMATIVELY_APPLICABLE",
            "normative applicability must be APPLICABLE before DSM execution",
        )
    if design_input.eligibility.software.status is not SoftwareSupportStatus.SUPPORTED:
        readiness = (
            DSMDesignReadiness.INVALID_INPUT
            if design_input.eligibility.software.status
            is SoftwareSupportStatus.INVALID_INPUT
            else DSMDesignReadiness.UNSUPPORTED
        )
        return readiness, _diagnostic(
            "DSM_SOFTWARE_UNSUPPORTED",
            "software support must be SUPPORTED before DSM execution",
        )
    if not design_input.executable:
        return DSMDesignReadiness.INVALID_INPUT, _diagnostic(
            "DSM_DESIGN_INPUT_NOT_EXECUTABLE",
            "MemberDesignInput is not executable",
        )
    if design_input.resolved_member.section.catalog_section.family not in (
        SectionFamily.C_LIPPED,
        SectionFamily.C_UNLIPPED,
    ):
        return DSMDesignReadiness.UNSUPPORTED, _diagnostic(
            "DSM_SECTION_FAMILY_UNSUPPORTED",
            "M9B supports catalog lipped and unlipped C sections only",
        )
    return None


def _automatic_provenance(
    source: ElasticBucklingResult,
    candidate: ElasticBucklingModeResult,
) -> DSMElasticBucklingProvenance:
    if (
        candidate.classification.status is not ClassificationStatus.AUTOMATIC_ACCEPTED
        or not candidate.dsm_input_eligible
    ):
        raise _M9AUnsupported(
            f"{candidate.family.value} candidate is not M9A DSM-input eligible"
        )
    return DSMElasticBucklingProvenance(
        family=candidate.family,
        input_basis=DSMElasticInputBasis.AUTOMATIC,
        critical_stress_mpa=candidate.critical_stress_mpa,
        critical_load_n=candidate.critical_load_n,
        half_wavelength_mm=candidate.half_wavelength_mm,
        source_candidate_ids=(candidate.tracked_mode.eigenvector_id,),
        m9a_trace_id=source.trace.trace_id,
        solver_package=source.solver_provenance.package,
        solver_version=source.solver_provenance.version,
        adapter_version=source.solver_provenance.adapter_version,
        engineer_confirmed=False,
    )


def _resolve_elastic_input(
    source: ElasticBucklingResult,
    family: BucklingModeFamily,
) -> DSMElasticBucklingProvenance:
    accepted = tuple(
        candidate for candidate in source.accepted_results if candidate.family is family
    )
    if len(accepted) > 1:
        raise _M9AUnsupported(
            f"M9A has multiple automatically accepted {family.value} candidates"
        )
    if accepted:
        return _automatic_provenance(source, accepted[0])

    selection = source.engineering_selection
    if selection is not None and selection.family is family:
        reviewed_ids = {
            candidate.tracked_mode.eigenvector_id
            for candidate in source.engineering_review_required_candidates
            if candidate.family is family
        }
        if not set(selection.candidate_eigenvector_ids).issubset(reviewed_ids):
            raise _M9AUnsupported(
                "EngineeringSelection does not reference review-required candidates "
                f"for {family.value}"
            )
        return DSMElasticBucklingProvenance(
            family=family,
            input_basis=DSMElasticInputBasis.ENGINEERING_SELECTED,
            critical_stress_mpa=selection.critical_stress_mpa,
            critical_load_n=selection.critical_load_n,
            half_wavelength_mm=selection.half_wavelength_mm,
            source_candidate_ids=selection.candidate_eigenvector_ids,
            m9a_trace_id=source.trace.trace_id,
            solver_package=source.solver_provenance.package,
            solver_version=source.solver_provenance.version,
            adapter_version=source.solver_provenance.adapter_version,
            engineer_confirmed=selection.engineer_confirmed,
            selection_reason=selection.reason,
            confirmed_by=selection.confirmed_by,
            selection_provenance=selection.provenance,
        )

    if any(
        candidate.family is family
        for candidate in source.engineering_review_required_candidates
    ):
        raise _M9AReviewRequired(
            f"M9A {family.value} candidate requires an explicit EngineeringSelection"
        )
    raise _M9AUnsupported(f"M9A has no usable {family.value} result")


def _overall_basis(
    local: DSMElasticBucklingProvenance,
    distortional: DSMElasticBucklingProvenance | None,
) -> DSMElasticInputBasis:
    bases = {local.input_basis}
    if distortional is not None:
        bases.add(distortional.input_basis)
    if len(bases) == 2:
        return DSMElasticInputBasis.MIXED
    return next(iter(bases))


def _build_trace(
    design_input: MemberDesignInput,
    *,
    global_buckling,
    global_strength,
    p_y_n: float,
    local: DSMElasticBucklingProvenance,
    local_strength,
    distortional: DSMElasticBucklingProvenance | None,
    distortional_strength,
    governing: DSMGoverningLimitState,
    nominal_strength_n: float,
    design_strength_n: float,
    basis: DSMElasticInputBasis,
    diagnostics: tuple[EngineeringDiagnostic, ...],
) -> CalculationTrace:
    case_id = design_input.resolved_member.member.case_id
    trace_id = make_trace_id(
        case_id=case_id,
        method=DesignMethod.DSM,
        limit_state=_TRACE_LIMIT_STATE,
    )
    steps: list[CalculationStep] = []

    def add(
        name: str,
        results: tuple[EngineeringValue, ...],
        *,
        inputs: tuple[EngineeringValue, ...] = (),
        reference: EquationReference,
        description: str,
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

    gross = design_input.section_mechanics.gross
    fy = design_input.resolved_member.material.fy_mpa
    add(
        "Authoritative gross yield load",
        (_value("p_y", p_y_n, EngineeringUnit.NEWTON, "Py"),),
        inputs=(
            _value("gross_area", gross.a_mm2, EngineeringUnit.SQUARE_MILLIMETRE, "Ag"),
            _value("yield_stress", fy, EngineeringUnit.MEGAPASCAL, "Fy"),
        ),
        reference=_REF_E4,
        description="Ag is the M3 gross area and Fy is the resolved material value.",
        expression="Py = Ag * Fy",
    )
    add(
        "M8B global elastic buckling",
        (
            _value("p_cre", global_buckling.p_cre_n, EngineeringUnit.NEWTON, "Pcre"),
            _value("f_cre", global_buckling.f_cre_mpa, EngineeringUnit.MEGAPASCAL, "Fcre"),
        ),
        reference=_REF_APP2_GLOBAL,
        description="Shared M8B analytical global-buckling mechanics; no pyCUFSM GLOBAL value.",
    )
    add(
        "M8B E2 global column strength",
        (
            _value("lambda_c", global_strength.lambda_c, EngineeringUnit.DIMENSIONLESS, "lambda_c"),
            _value("p_ne", global_strength.p_ne_n, EngineeringUnit.NEWTON, "Pne"),
        ),
        inputs=(
            _value("f_cre", global_buckling.f_cre_mpa, EngineeringUnit.MEGAPASCAL, "Fcre"),
            _value("yield_stress", fy, EngineeringUnit.MEGAPASCAL, "Fy"),
        ),
        reference=_REF_E2,
        description="Authoritative shared E2 result reused without an EWM calculation.",
    )
    add(
        "M9A local elastic buckling input",
        (
            _value("p_crl", local.critical_load_n, EngineeringUnit.NEWTON, "Pcrl"),
            _value("f_crl", local.critical_stress_mpa, EngineeringUnit.MEGAPASCAL, "Fcrl"),
            _value("local_half_wavelength", local.half_wavelength_mm, EngineeringUnit.MILLIMETRE),
        ),
        reference=_REF_APP2_NUMERICAL,
        description=f"Input basis: {local.input_basis.value}; M9A trace: {local.m9a_trace_id}.",
    )
    add(
        "E3.2 DSM local nominal strength",
        (
            _value("lambda_l", local_strength.lambda_l, EngineeringUnit.DIMENSIONLESS, "lambda_l"),
            _value("p_nl", local_strength.p_nl_n, EngineeringUnit.NEWTON, "Pnl"),
        ),
        inputs=(
            _value("p_ne", global_strength.p_ne_n, EngineeringUnit.NEWTON, "Pne"),
            _value("p_crl", local.critical_load_n, EngineeringUnit.NEWTON, "Pcrl"),
        ),
        reference=_REF_E3_2,
        description=f"Deterministic branch: {local_strength.branch.value}.",
        expression="lambda_l=sqrt(Pne/Pcrl); Pnl per E3.2-1, limited to Pne",
    )
    if distortional is not None and distortional_strength is not None:
        add(
            "M9A distortional elastic buckling input",
            (
                _value("p_crd", distortional.critical_load_n, EngineeringUnit.NEWTON, "Pcrd"),
                _value("f_crd", distortional.critical_stress_mpa, EngineeringUnit.MEGAPASCAL, "Fcrd"),
                _value("distortional_half_wavelength", distortional.half_wavelength_mm, EngineeringUnit.MILLIMETRE),
            ),
            reference=_REF_APP2_NUMERICAL,
            description=(
                f"Input basis: {distortional.input_basis.value}; "
                f"M9A trace: {distortional.m9a_trace_id}."
            ),
        )
        add(
            "E4 DSM distortional nominal strength",
            (
                _value("lambda_d", distortional_strength.lambda_d, EngineeringUnit.DIMENSIONLESS, "lambda_d"),
                _value("p_nd", distortional_strength.p_nd_n, EngineeringUnit.NEWTON, "Pnd"),
            ),
            inputs=(
                _value("p_y", p_y_n, EngineeringUnit.NEWTON, "Py"),
                _value("p_crd", distortional.critical_load_n, EngineeringUnit.NEWTON, "Pcrd"),
            ),
            reference=_REF_E4,
            description=f"Deterministic branch: {distortional_strength.branch.value}.",
            expression="lambda_d=sqrt(Py/Pcrd); Pnd per E4-1, limited to Py",
        )
    add(
        "E1 governing nominal strength",
        (_value("nominal_strength", nominal_strength_n, EngineeringUnit.NEWTON, "Pn"),),
        inputs=(
            _value("p_nl", local_strength.p_nl_n, EngineeringUnit.NEWTON, "Pnl"),
        )
        + (
            (_value("p_nd", distortional_strength.p_nd_n, EngineeringUnit.NEWTON, "Pnd"),)
            if distortional_strength is not None
            else ()
        ),
        reference=_REF_E1,
        description=f"Governing limit state: {governing.value}.",
        expression="Pn = smallest applicable nominal axial strength",
    )
    add(
        "LRFD design resistance",
        (
            _value("resistance_factor", LRFD_COMPRESSION_RESISTANCE_FACTOR, EngineeringUnit.DIMENSIONLESS, "phi_c"),
            _value("design_strength", design_strength_n, EngineeringUnit.NEWTON, "phi_c Pn"),
        ),
        inputs=(_value("nominal_strength", nominal_strength_n, EngineeringUnit.NEWTON, "Pn"),),
        reference=_REF_PHI,
        description="The centralized S100-24 LRFD compression factor is applied once.",
        expression="phi_c Pn = phi_c * Pn",
    )
    return CalculationTrace(
        trace_id=trace_id,
        status=(
            CalculationStatus.COMPLETED_WITH_WARNINGS
            if basis is not DSMElasticInputBasis.AUTOMATIC
            else CalculationStatus.COMPLETED
        ),
        steps=tuple(steps),
        final_values=(
            _value("p_y", p_y_n, EngineeringUnit.NEWTON, "Py"),
            _value("p_ne", global_strength.p_ne_n, EngineeringUnit.NEWTON, "Pne"),
            _value("p_crl", local.critical_load_n, EngineeringUnit.NEWTON, "Pcrl"),
            _value("p_nl", local_strength.p_nl_n, EngineeringUnit.NEWTON, "Pnl"),
        )
        + (
            (
                _value("p_crd", distortional.critical_load_n, EngineeringUnit.NEWTON, "Pcrd"),
                _value("p_nd", distortional_strength.p_nd_n, EngineeringUnit.NEWTON, "Pnd"),
            )
            if distortional is not None and distortional_strength is not None
            else ()
        )
        + (
            _value("nominal_strength", nominal_strength_n, EngineeringUnit.NEWTON, "Pn"),
            _value("resistance_factor", LRFD_COMPRESSION_RESISTANCE_FACTOR, EngineeringUnit.DIMENSIONLESS, "phi_c"),
            _value("design_strength", design_strength_n, EngineeringUnit.NEWTON, "phi_c Pn"),
        ),
        case_id=case_id,
        method=DesignMethod.DSM,
        limit_state=_TRACE_LIMIT_STATE,
        diagnostics=diagnostics,
        metadata=(
            MetadataEntry("standard_id", S100_24_STANDARD_ID),
            MetadataEntry("standard_edition", S100_24_STANDARD_EDITION),
            MetadataEntry("elastic_input_basis", basis.value),
            MetadataEntry("normative_applicability", ApplicabilityStatus.APPLICABLE.value),
            MetadataEntry("software_support", SoftwareSupportStatus.SUPPORTED.value),
            MetadataEntry("holes_supported", False),
            MetadataEntry("global_buckling_owner", "STRUCTURELAB_M8B_AISI_E2"),
        ),
    )


def calculate_dsm_compression_resistance(
    design_input: MemberDesignInput,
    elastic_buckling: ElasticBucklingResult | M9AUnavailable,
) -> DSMCompressionResistance:
    """Calculate S100-24 LRFD DSM concentric axial-compression resistance."""

    if not isinstance(design_input, MemberDesignInput):
        raise ValidationError("design_input must be MemberDesignInput")
    preflight = _preflight(design_input)
    if preflight is not None:
        readiness, diagnostic = preflight
        return _empty_result(
            design_input,
            readiness=readiness,
            calculation_status=CalculationStatus.NOT_RUN,
            diagnostic=diagnostic,
        )
    case_id = design_input.resolved_member.member.case_id
    if isinstance(elastic_buckling, M9AUnavailable):
        if elastic_buckling.case_id != case_id:
            return _empty_result(
                design_input,
                readiness=DSMDesignReadiness.INVALID_INPUT,
                calculation_status=CalculationStatus.NOT_RUN,
                diagnostic=_diagnostic(
                    "DSM_M9A_CASE_MISMATCH",
                    "M9A unavailable state does not match the design member",
                ),
            )
        return _empty_result(
            design_input,
            readiness=DSMDesignReadiness.UNSUPPORTED,
            calculation_status=CalculationStatus.NOT_RUN,
            diagnostic=_diagnostic(
                "DSM_M9A_UNSUPPORTED",
                elastic_buckling.reason,
                context=tuple(
                    MetadataEntry(f"m9a_provenance_{index}", value)
                    for index, value in enumerate(elastic_buckling.provenance, 1)
                ),
            ),
        )
    if not isinstance(elastic_buckling, ElasticBucklingResult):
        raise ValidationError(
            "elastic_buckling must be ElasticBucklingResult or M9AUnavailable"
        )
    if elastic_buckling.case_id != case_id:
        return _empty_result(
            design_input,
            readiness=DSMDesignReadiness.INVALID_INPUT,
            calculation_status=CalculationStatus.NOT_RUN,
            diagnostic=_diagnostic(
                "DSM_M9A_CASE_MISMATCH",
                "M9A elastic buckling result does not match the design member",
            ),
        )

    family = design_input.resolved_member.section.catalog_section.family
    distortional_applicable = family is SectionFamily.C_LIPPED
    try:
        local = _resolve_elastic_input(elastic_buckling, BucklingModeFamily.LOCAL)
        distortional = (
            _resolve_elastic_input(
                elastic_buckling, BucklingModeFamily.DISTORTIONAL
            )
            if distortional_applicable
            else None
        )
    except _M9AReviewRequired as error:
        return _empty_result(
            design_input,
            readiness=DSMDesignReadiness.ENGINEERING_REVIEW_REQUIRED,
            calculation_status=CalculationStatus.NOT_RUN,
            diagnostic=_diagnostic(
                "DSM_ENGINEERING_REVIEW_REQUIRED",
                str(error),
                severity=DiagnosticSeverity.WARNING,
            ),
        )
    except _M9AUnsupported as error:
        return _empty_result(
            design_input,
            readiness=DSMDesignReadiness.UNSUPPORTED,
            calculation_status=CalculationStatus.NOT_RUN,
            diagnostic=_diagnostic("DSM_M9A_INPUT_UNSUPPORTED", str(error)),
        )

    try:
        require_singly_symmetric_c(
            design_input.resolved_member.section.geometry,
            design_input.section_mechanics,
            error_code="DSM_GLOBAL_NONSYMMETRIC_UNSUPPORTED",
            owner="M8B/M9B",
        )
        gross = design_input.section_mechanics.gross
        fy = design_input.resolved_member.material.fy_mpa
        if not isfinite(gross.a_mm2) or gross.a_mm2 <= 0.0:
            raise DSMCalculationError(
                "DSM_INVALID_POSITIVE_INPUT", "Ag must be finite and greater than zero"
            )
        if not isfinite(fy) or fy <= 0.0:
            raise DSMCalculationError(
                "DSM_INVALID_POSITIVE_INPUT", "Fy must be finite and greater than zero"
            )
        p_y = gross.a_mm2 * fy
        if not isfinite(p_y) or p_y <= 0.0:
            raise DSMCalculationError(
                "DSM_INVALID_POSITIVE_INPUT", "Py must be finite and greater than zero"
            )
        global_buckling = calculate_global_buckling(
            design_input.resolved_member.member.geometry,
            design_input.section_mechanics,
        )
        global_strength = calculate_global_column_strength(
            gross_area_mm2=gross.a_mm2,
            yield_stress_mpa=fy,
            f_cre_mpa=global_buckling.f_cre_mpa,
        )
        local_strength = calculate_dsm_local_strength(
            p_ne_n=global_strength.p_ne_n,
            p_crl_n=local.critical_load_n,
        )
        distortional_strength = (
            calculate_dsm_distortional_strength(
                p_y_n=p_y,
                p_crd_n=distortional.critical_load_n,
            )
            if distortional is not None
            else None
        )
        nominal_strength, governing = select_dsm_nominal_strength(
            p_nl_n=local_strength.p_nl_n,
            p_nd_n=(
                distortional_strength.p_nd_n
                if distortional_strength is not None
                else None
            ),
        )
        design_strength = LRFD_COMPRESSION_RESISTANCE_FACTOR * nominal_strength
        if not all(
            isfinite(value) and value > 0.0
            for value in (global_strength.p_ne_n, nominal_strength, design_strength)
        ):
            raise DSMCalculationError(
                "DSM_NONFINITE_RESULT", "DSM resistance values must be positive and finite"
            )
        basis = _overall_basis(local, distortional)
        warnings = (
            (
                "At least one elastic buckling input is an explicit "
                "engineer-confirmed selection; it is not an automatic M9A result."
            ),
        ) if basis is not DSMElasticInputBasis.AUTOMATIC else ()
        diagnostics = tuple(
            _diagnostic(
                "DSM_ENGINEERING_SELECTION_CONSUMED",
                warning,
                severity=DiagnosticSeverity.WARNING,
            )
            for warning in warnings
        )
        trace = _build_trace(
            design_input,
            global_buckling=global_buckling,
            global_strength=global_strength,
            p_y_n=p_y,
            local=local,
            local_strength=local_strength,
            distortional=distortional,
            distortional_strength=distortional_strength,
            governing=governing,
            nominal_strength_n=nominal_strength,
            design_strength_n=design_strength,
            basis=basis,
            diagnostics=diagnostics,
        )
        return DSMCompressionResistance(
            case_id=case_id,
            standard_id=S100_24_STANDARD_ID,
            standard_edition=S100_24_STANDARD_EDITION,
            design_method=DesignMethod.DSM,
            design_format=DesignFormat.LRFD,
            calculation_status=trace.status,
            design_readiness=DSMDesignReadiness.DESIGN_READY,
            applicability_status=ApplicabilityStatus.APPLICABLE,
            software_support_status=SoftwareSupportStatus.SUPPORTED,
            global_buckling=global_buckling,
            global_column_strength=global_strength,
            p_y_n=p_y,
            p_crl_n=local.critical_load_n,
            lambda_l=local_strength.lambda_l,
            p_nl_n=local_strength.p_nl_n,
            local_branch=local_strength.branch,
            p_crd_n=(
                distortional.critical_load_n if distortional is not None else None
            ),
            lambda_d=(
                distortional_strength.lambda_d
                if distortional_strength is not None
                else None
            ),
            p_nd_n=(
                distortional_strength.p_nd_n
                if distortional_strength is not None
                else None
            ),
            distortional_branch=(
                distortional_strength.branch
                if distortional_strength is not None
                else DSMDistortionalBranch.NOT_APPLICABLE
            ),
            nominal_strength_n=nominal_strength,
            resistance_factor=LRFD_COMPRESSION_RESISTANCE_FACTOR,
            design_strength_n=design_strength,
            governing_limit_state=governing,
            local_buckling_provenance=local,
            distortional_buckling_provenance=distortional,
            elastic_input_basis=basis,
            equation_references=_equation_references(
                distortional_applicable=distortional_applicable
            ),
            trace=trace,
            diagnostics=diagnostics,
            warnings=warnings,
        )
    except DSMCalculationError as error:
        unsupported = error.code in {
            "DSM_E3_2_SLENDERNESS_UNSUPPORTED",
            "DSM_E4_SLENDERNESS_UNSUPPORTED",
        }
        return _empty_result(
            design_input,
            readiness=(
                DSMDesignReadiness.UNSUPPORTED
                if unsupported
                else DSMDesignReadiness.INVALID_INPUT
            ),
            calculation_status=(
                CalculationStatus.NOT_RUN if unsupported else CalculationStatus.FAILED
            ),
            diagnostic=_diagnostic(error.code, str(error)),
        )
    except EngineeringCalculationError as error:
        return _empty_result(
            design_input,
            readiness=DSMDesignReadiness.UNSUPPORTED,
            calculation_status=CalculationStatus.NOT_RUN,
            diagnostic=_diagnostic(
                "DSM_GLOBAL_CALCULATION_UNSUPPORTED",
                str(error),
                context=(MetadataEntry("source_error_code", error.code),),
            ),
        )


__all__ = [
    "LRFD_COMPRESSION_RESISTANCE_FACTOR",
    "calculate_dsm_compression_resistance",
]
