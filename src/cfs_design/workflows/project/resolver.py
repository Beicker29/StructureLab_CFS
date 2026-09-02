"""M5 orchestration from approved project files to resolved executable inputs."""

from pathlib import Path

from cfs_design.catalogs import (
    CatalogRegistry,
    load_material_catalog,
    load_section_catalog,
)
from cfs_design.core.exceptions import (
    CatalogError,
    ConfigurationError,
    SchemaError,
    UnsupportedFeatureError,
    ValidationError,
)
from cfs_design.domain import Material, MemberCase, Project, ResolvedMember, ResolvedSection
from cfs_design.io.etabs import ETABSImportResult, import_etabs_results, load_etabs_mapping
from cfs_design.io.project import (
    CatalogVerificationAction,
    ProjectConfig,
    load_members,
    load_project_config,
)
from cfs_design.mechanics.sections import (
    CatalogVerificationResult,
    VerificationPolicy,
    VerificationProperty,
    VerificationStatus,
    build_centerline_section,
    compute_advanced_properties,
    compute_gross_properties,
    verify_catalog_properties,
)

from .demand_transform import transform_demand_set
from .models import (
    DiagnosticSeverity,
    ProjectDiagnostic,
    ProjectProvenance,
    ResolvedProject,
    ResolvedSectionMechanics,
)


def _verification_properties(
    config: ProjectConfig,
) -> tuple[tuple[VerificationProperty, ...], set[VerificationProperty]]:
    required: list[VerificationProperty] = []
    extended: list[VerificationProperty] = []
    for values, destination, label in (
        (
            config.catalog_verification.required_properties,
            required,
            "required_properties",
        ),
        (
            config.catalog_verification.extended_properties,
            extended,
            "extended_properties",
        ),
    ):
        for value in values:
            try:
                destination.append(VerificationProperty(value))
            except ValueError as error:
                allowed = ", ".join(item.value for item in VerificationProperty)
                raise SchemaError(
                    f"project.yaml catalog_verification.{label} contains unknown "
                    f"property {value!r}; expected one of: {allowed}"
                ) from error
    return tuple(required + extended), set(required)


def _catalog_inputs(
    member: MemberCase,
    registry: CatalogRegistry,
    config: ProjectConfig,
    diagnostics: list[ProjectDiagnostic],
) -> tuple[ResolvedSection, Material] | None:
    section: ResolvedSection | None = None
    material: Material | None = None
    try:
        section = registry.get_section(member.section_id)
    except CatalogError as error:
        if config.quality_assurance.fail_on_missing_catalog_reference:
            raise ConfigurationError(
                f"Active member {member.case_id!r} references unknown section_id "
                f"{member.section_id!r}"
            ) from error
        diagnostics.append(
            ProjectDiagnostic(
                severity=DiagnosticSeverity.WARNING,
                code="MISSING_SECTION_REFERENCE",
                message="Active member could not be resolved to a section",
                case_id=member.case_id,
                section_id=member.section_id,
            )
        )
    try:
        material = registry.get_material(member.material_id)
    except CatalogError as error:
        if config.quality_assurance.fail_on_missing_catalog_reference:
            raise ConfigurationError(
                f"Active member {member.case_id!r} references unknown material_id "
                f"{member.material_id!r}"
            ) from error
        diagnostics.append(
            ProjectDiagnostic(
                severity=DiagnosticSeverity.WARNING,
                code="MISSING_MATERIAL_REFERENCE",
                message="Active member could not be resolved to a material",
                case_id=member.case_id,
                context=(("material_id", member.material_id),),
            )
        )
    if section is None or material is None:
        return None
    if not section.catalog_section.active:
        raise ConfigurationError(
            f"Active member {member.case_id!r} uses inactive section "
            f"{member.section_id!r}"
        )
    if not material.active:
        raise ConfigurationError(
            f"Active member {member.case_id!r} uses inactive material "
            f"{member.material_id!r}"
        )
    return section, material


def _verification_diagnostics(
    result: CatalogVerificationResult,
    required: set[VerificationProperty],
    config: ProjectConfig,
) -> tuple[ProjectDiagnostic, ...]:
    diagnostics: list[ProjectDiagnostic] = []
    required_missing = [
        check.property_name.value
        for check in result.checks
        if check.property_name in required
        and check.status is VerificationStatus.NOT_CHECKED
    ]
    if required_missing:
        raise ConfigurationError(
            f"Section {result.section_id!r} is missing required catalog values: "
            f"{', '.join(required_missing)}"
        )
    failed = [
        check.property_name.value
        for check in result.checks
        if check.status is VerificationStatus.FAIL
    ]
    if failed and (
        config.catalog_verification.action_on_fail
        is CatalogVerificationAction.ERROR
    ):
        raise ConfigurationError(
            f"Section {result.section_id!r} failed catalog verification for: "
            f"{', '.join(failed)}"
        )
    for check in result.checks:
        if check.status is VerificationStatus.WARNING:
            diagnostics.append(
                ProjectDiagnostic(
                    severity=DiagnosticSeverity.WARNING,
                    code="CATALOG_PROPERTY_WARNING",
                    message=(
                        f"Catalog property {check.property_name.value} is outside "
                        "the PASS tolerance"
                    ),
                    section_id=result.section_id,
                    context=(
                        ("catalog_value", check.catalog_value),
                        ("computed_value", check.computed_value),
                    ),
                )
            )
        elif check.status is VerificationStatus.FAIL:
            diagnostics.append(
                ProjectDiagnostic(
                    severity=DiagnosticSeverity.WARNING,
                    code="CATALOG_PROPERTY_FAIL",
                    message=(
                        f"Catalog property {check.property_name.value} failed "
                        "verification; action_on_fail=warning permits resolution"
                    ),
                    section_id=result.section_id,
                    context=(
                        ("catalog_value", check.catalog_value),
                        ("computed_value", check.computed_value),
                    ),
                )
            )
        elif check.status is VerificationStatus.NOT_CHECKED:
            diagnostics.append(
                ProjectDiagnostic(
                    severity=DiagnosticSeverity.WARNING,
                    code="CATALOG_EXTENDED_NOT_CHECKED",
                    message=(
                        f"Extended catalog property {check.property_name.value} "
                        "has no catalog value and remains NOT_CHECKED"
                    ),
                    section_id=result.section_id,
                    context=(("computed_value", check.computed_value),),
                )
            )
    return tuple(diagnostics)


def _resolve_unique_section_mechanics(
    sections: tuple[ResolvedSection, ...],
    config: ProjectConfig,
    diagnostics: list[ProjectDiagnostic],
) -> tuple[
    tuple[ResolvedSectionMechanics, ...],
    tuple[CatalogVerificationResult, ...],
]:
    verification_enabled = config.catalog_verification.enabled
    if not verification_enabled:
        diagnostics.append(
            ProjectDiagnostic(
                severity=DiagnosticSeverity.INFO,
                code="CATALOG_VERIFICATION_DISABLED",
                message="Catalog property verification is disabled by project.yaml",
            )
        )
    required: set[VerificationProperty] = set()
    policy: VerificationPolicy | None = None
    if verification_enabled:
        properties, required = _verification_properties(config)
        policy = VerificationPolicy(
            relative_tolerance=config.catalog_verification.relative_tolerance,
            absolute_tolerance=0.0,
            properties_to_check=properties,
        )
    results: list[CatalogVerificationResult] = []
    mechanics_sets: list[ResolvedSectionMechanics] = []
    for section in sections:
        section_id = section.catalog_section.section_id
        try:
            centerline = build_centerline_section(
                section.geometry, section_id=section_id
            )
            gross = compute_gross_properties(centerline)
            advanced = compute_advanced_properties(centerline, gross)
        except (UnsupportedFeatureError, ValidationError) as error:
            message = (
                f"Section {section_id!r} could not be mechanically verified: "
                f"{error}"
            )
            if (
                config.catalog_verification.action_on_fail
                is CatalogVerificationAction.ERROR
            ):
                raise ConfigurationError(message) from error
            diagnostics.append(
                ProjectDiagnostic(
                    severity=DiagnosticSeverity.WARNING,
                    code="CATALOG_VERIFICATION_UNSUPPORTED",
                    message=message,
                    section_id=section_id,
                )
            )
            continue
        result: CatalogVerificationResult | None = None
        design_use_permitted = False
        gate_reason = "Catalog verification is disabled"
        if verification_enabled:
            if policy is None:
                raise ValidationError("verification policy was not constructed")
            result = verify_catalog_properties(
                section,
                gross,
                policy,
                advanced=advanced,
            )
            diagnostics.extend(_verification_diagnostics(result, required, config))
            required_failed = any(
                check.property_name in required
                and check.status
                in (VerificationStatus.FAIL, VerificationStatus.NOT_CHECKED)
                for check in result.checks
            )
            design_use_permitted = not required_failed
            gate_reason = (
                "All required catalog-verification checks permit design use"
                if design_use_permitted
                else "A required catalog-verification check blocks design use"
            )
            results.append(result)
        mechanics_sets.append(
            ResolvedSectionMechanics(
                section_id=section_id,
                gross=gross,
                advanced=advanced,
                verification=result,
                design_use_permitted=design_use_permitted,
                gate_reason=gate_reason,
            )
        )
    return tuple(mechanics_sets), tuple(results)


def _project_provenance(
    config: ProjectConfig,
    members_sha256: str,
    registry: CatalogRegistry,
    etabs_import: ETABSImportResult,
) -> ProjectProvenance:
    return ProjectProvenance(
        project_yaml_path=config.source_path,
        project_yaml_sha256=config.file_sha256,
        members_path=config.files.members.resolved_path,
        members_sha256=members_sha256,
        materials_catalog_path=registry.material_catalog.metadata.source_path,
        materials_catalog_sha256=registry.material_catalog.metadata.file_sha256,
        sections_catalog_path=registry.section_catalog.metadata.source_path,
        sections_catalog_sha256=registry.section_catalog.metadata.file_sha256,
        etabs_path=etabs_import.metadata.source_path,
        etabs_sha256=etabs_import.metadata.file_sha256,
        etabs_program_version=etabs_import.metadata.program_version,
    )


def resolve_project(
    project_yaml_path: str | Path,
    *,
    repository_root: str | Path | None = None,
) -> ResolvedProject:
    """Load and resolve a complete M5 project without performing design."""

    config = load_project_config(
        project_yaml_path,
        repository_root=repository_root,
    )
    members_result = load_members(config.files.members.resolved_path)
    if members_result.metadata.canonical_units != config.design_context.canonical_units:
        raise ConfigurationError(
            "Members workbook canonical units do not match project design context"
        )
    project = Project(
        metadata=config.metadata,
        design_context=config.design_context,
        members=members_result.members,
        scope_evidence=config.scope_evidence,
    )
    registry = CatalogRegistry(
        material_catalog=load_material_catalog(
            config.files.materials_catalog.resolved_path
        ),
        section_catalog=load_section_catalog(
            config.files.sections_catalog.resolved_path
        ),
    )
    mapping = load_etabs_mapping(
        config.files.members.resolved_path,
        worksheet=config.etabs_import.mapping.source_sheet,
    )
    if mapping.file_sha256 != members_result.metadata.file_sha256:
        raise ConfigurationError(
            "members.xlsx changed between Members and ETABS_Mapping reads"
        )
    etabs_import = import_etabs_results(
        config.files.etabs_results.resolved_path,
        config=config.etabs_import.importer,
        mapping=mapping,
    )

    diagnostics: list[ProjectDiagnostic] = [
        ProjectDiagnostic(
            severity=DiagnosticSeverity.WARNING,
            code="ETABS_IMPORT_WARNING",
            message=warning,
        )
        for warning in etabs_import.warnings
    ]
    catalog_inputs: dict[str, tuple[ResolvedSection, Material]] = {}
    for member in members_result.active_members:
        resolved = _catalog_inputs(member, registry, config, diagnostics)
        if resolved is not None:
            catalog_inputs[member.case_id] = resolved

    unique_sections: list[ResolvedSection] = []
    seen_section_ids: set[str] = set()
    for member in members_result.active_members:
        resolved = catalog_inputs.get(member.case_id)
        if resolved is None:
            continue
        section = resolved[0]
        section_id = section.catalog_section.section_id
        if section_id not in seen_section_ids:
            unique_sections.append(section)
            seen_section_ids.add(section_id)
    section_mechanics, verification_results = _resolve_unique_section_mechanics(
        tuple(unique_sections), config, diagnostics
    )

    mapped_by_case = {
        mapped.case_id.strip(): mapped for mapped in etabs_import.mapped_members
    }
    project_case_ids = {member.case_id.strip() for member in members_result.members}
    for mapped_case_id in mapped_by_case:
        if mapped_case_id not in project_case_ids:
            diagnostics.append(
                ProjectDiagnostic(
                    severity=DiagnosticSeverity.WARNING,
                    code="ETABS_MAPPING_UNKNOWN_PROJECT_MEMBER",
                    message="Enabled ETABS mapping does not identify a Members row",
                    case_id=mapped_case_id,
                )
            )

    active_resolved_members: list[ResolvedMember] = []
    for member in members_result.active_members:
        resolved_inputs = catalog_inputs.get(member.case_id)
        if resolved_inputs is None:
            continue
        mapped = mapped_by_case.get(member.case_id.strip())
        if mapped is None:
            message = (
                f"Active project member {member.case_id!r} has no mapped usable "
                "ETABS DemandSet"
            )
            if config.quality_assurance.fail_on_unmapped_etabs_member:
                raise ConfigurationError(message)
            diagnostics.append(
                ProjectDiagnostic(
                    severity=DiagnosticSeverity.WARNING,
                    code="ACTIVE_MEMBER_UNMAPPED",
                    message=message,
                    case_id=member.case_id,
                )
            )
            continue
        section, material = resolved_inputs
        section_demands = transform_demand_set(
            mapped.demand_set,
            member.geometry.orientation_deg,
        )
        active_resolved_members.append(
            ResolvedMember(
                member=member,
                section=section,
                material=material,
                demands=section_demands,
                source_demands=mapped.demand_set,
            )
        )

    provenance = _project_provenance(
        config,
        members_result.metadata.file_sha256,
        registry,
        etabs_import,
    )
    return ResolvedProject(
        project=project,
        project_config=config,
        catalog_registry=registry,
        active_resolved_members=tuple(active_resolved_members),
        section_verification_results=verification_results,
        etabs_import=etabs_import,
        diagnostics=tuple(diagnostics),
        provenance=provenance,
        section_mechanics=section_mechanics,
    )


__all__ = ["resolve_project"]
