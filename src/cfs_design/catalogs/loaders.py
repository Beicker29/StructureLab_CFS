"""Explicit versioned catalog loaders producing immutable domain objects."""

from collections.abc import Collection
from pathlib import Path

from cfs_design.core.exceptions import CatalogError, SchemaError, ValidationError
from cfs_design.domain import (
    CatalogSection,
    GeometryConvention,
    Material,
    ResolvedSection,
    SectionFamily,
    SectionGeometry,
    SectionProperties,
    StandardSectionDimensions,
    S100_24_STANDARD_EDITION,
    S100_24_STANDARD_ID,
)

from ._excel import (
    CatalogRow,
    ExcelCatalogReader,
    optional_number,
    optional_text,
    required_boolean,
    required_enum,
    required_integer,
    required_number,
    required_text,
)
from .models import CatalogMetadata, CatalogSource, MaterialCatalog, SectionCatalog
from .schemas import (
    MATERIAL_WORKBOOK_SCHEMA,
    MATERIAL_SCHEMA_VERSION,
    SECTION_SCHEMA_VERSION_V0_2,
    SECTION_WORKBOOK_SCHEMA_V0_1,
    SECTION_WORKBOOK_SCHEMA_V0_2,
    SOURCE_TYPES,
    SUPPORTED_SECTION_SCHEMA_VERSIONS,
)
from .validation import register_unique, reject_orphans, require_reference


def _parse_metadata(
    reader: ExcelCatalogReader,
    supported_versions: tuple[str, ...],
) -> CatalogMetadata:
    values: dict[str, object] = {}
    order: list[str] = []
    seen_rows: dict[str, int] = {}
    for row in reader.rows("Metadata"):
        field_name = required_text(row, "Field")
        register_unique(field_name, seen_rows, row.context, "Field")
        values[field_name] = row.values["Value"]
        order.append(field_name)

    required_fields = ("name", "schema_version", "canonical_units", "description")
    missing = [field for field in required_fields if field not in values]
    if missing:
        raise SchemaError(
            f"{reader.source_path.name}: Metadata is missing required fields: "
            f"{', '.join(missing)}"
        )

    def metadata_text(field: str) -> str:
        value = values[field]
        if not isinstance(value, str) or not value.strip():
            raise SchemaError(
                f"{reader.source_path.name}: Metadata field {field!r} "
                f"must contain non-empty text"
            )
        return value

    schema_version = metadata_text("schema_version")
    if schema_version not in supported_versions:
        raise SchemaError(
            f"{reader.source_path.name}: unsupported schema_version "
            f"{schema_version!r}; supported versions are "
            f"{', '.join(repr(item) for item in supported_versions)}"
        )
    additional_fields = tuple(
        (field, values[field]) for field in order if field not in required_fields
    )
    return CatalogMetadata(
        name=metadata_text("name"),
        schema_version=schema_version,
        canonical_units=metadata_text("canonical_units"),
        description=metadata_text("description"),
        source_path=reader.source_path,
        file_sha256=reader.file_sha256,
        additional_fields=additional_fields,
    )


def _parse_sources(
    reader: ExcelCatalogReader,
) -> tuple[tuple[CatalogSource, ...], dict[str, CatalogRow]]:
    sources: list[CatalogSource] = []
    rows_by_id: dict[str, CatalogRow] = {}
    seen_rows: dict[str, int] = {}
    for row in reader.rows("Sources"):
        source_id = required_text(row, "source_id")
        register_unique(source_id, seen_rows, row.context, "source_id")
        source_type = required_text(row, "source_type")
        if source_type not in SOURCE_TYPES:
            raise row.context.catalog_error(
                "source_type",
                f"Unknown source_type {source_type!r}; expected one of: "
                f"{', '.join(sorted(SOURCE_TYPES))}",
            )
        source = CatalogSource(
            source_id=source_id,
            source_type=source_type,
            organization=optional_text(row, "organization"),
            document_or_catalog=required_text(row, "document_or_catalog"),
            edition_or_date=optional_text(row, "edition_or_date"),
            page_or_table=optional_text(row, "page_or_table"),
            url=optional_text(row, "url"),
            notes=optional_text(row, "notes"),
        )
        sources.append(source)
        rows_by_id[source_id] = row
    return tuple(sources), rows_by_id


def load_material_catalog(path: str | Path) -> MaterialCatalog:
    """Load and validate an approved material catalog workbook."""

    with ExcelCatalogReader(path, MATERIAL_WORKBOOK_SCHEMA) as reader:
        metadata = _parse_metadata(reader, (MATERIAL_SCHEMA_VERSION,))
        sources, source_rows = _parse_sources(reader)
        source_ids = source_rows.keys()
        materials: list[Material] = []
        seen_rows: dict[str, int] = {}
        for row in reader.rows("Materials"):
            material_id = required_text(row, "material_id")
            register_unique(material_id, seen_rows, row.context, "material_id")
            source_id = required_text(row, "source_id")
            require_reference(
                source_id,
                source_ids,
                row.context,
                "source_id",
                "Sources.source_id",
            )
            try:
                material = Material(
                    material_id=material_id,
                    designation=required_text(row, "designation"),
                    specification=required_text(row, "specification"),
                    grade=required_text(row, "grade"),
                    fy_mpa=required_number(row, "Fy_MPa"),
                    fu_mpa=required_number(row, "Fu_MPa"),
                    e_mpa=required_number(row, "E_MPa"),
                    nu=required_number(row, "nu"),
                    density_kg_m3=optional_number(row, "density_kg_m3"),
                    source_id=source_id,
                    active=required_boolean(row, "active"),
                    notes=optional_text(row, "notes"),
                )
            except ValidationError as error:
                raise row.context.catalog_error(
                    None,
                    f"Invalid Material domain values: {error}",
                ) from error
            materials.append(material)
        return MaterialCatalog(metadata, sources, tuple(materials))


def _parse_geometries(
    reader: ExcelCatalogReader,
) -> tuple[tuple[SectionGeometry, ...], dict[str, SectionGeometry], dict[str, CatalogRow]]:
    geometries: list[SectionGeometry] = []
    by_id: dict[str, SectionGeometry] = {}
    rows_by_id: dict[str, CatalogRow] = {}
    seen_rows: dict[str, int] = {}
    for row in reader.rows("Geometry"):
        geometry_id = required_text(row, "geometry_id")
        register_unique(geometry_id, seen_rows, row.context, "geometry_id")
        try:
            geometry = SectionGeometry(
                geometry_id=geometry_id,
                section_type=required_enum(row, "section_type", SectionFamily),
                h_mm=required_number(row, "H_mm"),
                b1_mm=required_number(row, "B1_mm"),
                b2_mm=optional_number(row, "B2_mm"),
                d1_mm=optional_number(row, "D1_mm"),
                d2_mm=optional_number(row, "D2_mm"),
                t_mm=required_number(row, "t_mm"),
                ri_mm=required_number(row, "Ri_mm"),
                web_flange_angle_deg=required_number(
                    row,
                    "web_flange_angle_deg",
                ),
                flange_lip_angle_deg=optional_number(
                    row,
                    "flange_lip_angle_deg",
                ),
                geometry_convention=required_enum(
                    row,
                    "geometry_convention",
                    GeometryConvention,
                ),
                notes=optional_text(row, "notes"),
            )
        except ValidationError as error:
            raise row.context.catalog_error(
                None,
                f"Invalid SectionGeometry domain values: {error}",
            ) from error
        geometries.append(geometry)
        by_id[geometry_id] = geometry
        rows_by_id[geometry_id] = row
    return tuple(geometries), by_id, rows_by_id


def _parse_properties(
    reader: ExcelCatalogReader,
) -> tuple[
    tuple[SectionProperties, ...],
    dict[str, SectionProperties],
    dict[str, CatalogRow],
]:
    properties: list[SectionProperties] = []
    by_section_id: dict[str, SectionProperties] = {}
    rows_by_id: dict[str, CatalogRow] = {}
    seen_rows: dict[str, int] = {}
    for row in reader.rows("Properties"):
        section_id = required_text(row, "section_id")
        register_unique(section_id, seen_rows, row.context, "section_id")
        try:
            section_properties = SectionProperties(
                section_id=section_id,
                a_mm2=required_number(row, "A_mm2"),
                x_bar_mm=required_number(row, "x_bar_mm"),
                y_bar_mm=required_number(row, "y_bar_mm"),
                ix_mm4=required_number(row, "Ix_mm4"),
                iy_mm4=required_number(row, "Iy_mm4"),
                ixy_mm4=optional_number(row, "Ixy_mm4"),
                i1_mm4=optional_number(row, "I1_mm4"),
                i2_mm4=optional_number(row, "I2_mm4"),
                theta_p_deg=optional_number(row, "theta_p_deg"),
                sx_pos_mm3=required_number(row, "Sx_pos_mm3"),
                sx_neg_mm3=required_number(row, "Sx_neg_mm3"),
                sy_pos_mm3=required_number(row, "Sy_pos_mm3"),
                sy_neg_mm3=required_number(row, "Sy_neg_mm3"),
                rx_mm=required_number(row, "rx_mm"),
                ry_mm=required_number(row, "ry_mm"),
                j_mm4=required_number(row, "J_mm4"),
                cw_mm6=optional_number(row, "Cw_mm6"),
                x0_mm=optional_number(row, "x0_mm"),
                y0_mm=optional_number(row, "y0_mm"),
                property_basis=required_text(row, "property_basis"),
                source_id=required_text(row, "source_id"),
                notes=optional_text(row, "notes"),
            )
        except ValidationError as error:
            raise row.context.catalog_error(
                None,
                f"Invalid SectionProperties domain values: {error}",
            ) from error
        properties.append(section_properties)
        by_section_id[section_id] = section_properties
        rows_by_id[section_id] = row
    return tuple(properties), by_section_id, rows_by_id


def _parse_sections(
    reader: ExcelCatalogReader,
) -> tuple[tuple[CatalogSection, ...], dict[str, CatalogRow]]:
    sections: list[CatalogSection] = []
    rows_by_id: dict[str, CatalogRow] = {}
    seen_rows: dict[str, int] = {}
    for row in reader.rows("Sections"):
        section_id = required_text(row, "section_id")
        register_unique(section_id, seen_rows, row.context, "section_id")
        try:
            section = CatalogSection(
                section_id=section_id,
                designation=required_text(row, "designation"),
                family=required_enum(row, "family", SectionFamily),
                manufacturer=optional_text(row, "manufacturer"),
                geometry_id=required_text(row, "geometry_id"),
                source_id=required_text(row, "source_id"),
                active=required_boolean(row, "active"),
                notes=optional_text(row, "notes"),
            )
        except ValidationError as error:
            raise row.context.catalog_error(
                None,
                f"Invalid CatalogSection domain values: {error}",
            ) from error
        sections.append(section)
        rows_by_id[section_id] = row
    return tuple(sections), rows_by_id


def _parse_standard_dimensions(
    reader: ExcelCatalogReader,
    geometries: dict[str, SectionGeometry],
    source_ids: Collection[str],
) -> tuple[StandardSectionDimensions, ...]:
    dimensions: list[StandardSectionDimensions] = []
    seen_rows: dict[str, int] = {}
    for row in reader.rows("AISI_Dimensions"):
        geometry_id = required_text(row, "geometry_id")
        standard_id = required_text(row, "standard_id")
        standard_edition = required_integer(row, "standard_edition")
        key = f"{geometry_id}\x1f{standard_id}\x1f{standard_edition}"
        register_unique(
            key,
            seen_rows,
            row.context,
            "geometry_id, standard_id, standard_edition",
        )
        require_reference(
            geometry_id,
            geometries.keys(),
            row.context,
            "geometry_id",
            "Geometry.geometry_id",
        )
        source_id = required_text(row, "source_id")
        require_reference(
            source_id,
            source_ids,
            row.context,
            "source_id",
            "Sources.source_id",
        )
        if (
            standard_id != S100_24_STANDARD_ID
            or standard_edition != S100_24_STANDARD_EDITION
        ):
            raise row.context.catalog_error(
                "standard_id, standard_edition",
                "Unsupported standard-specific dimension identity "
                f"({standard_id!r}, {standard_edition!r}); expected "
                f"({S100_24_STANDARD_ID!r}, {S100_24_STANDARD_EDITION!r})",
            )
        try:
            record = StandardSectionDimensions(
                geometry_id=geometry_id,
                standard_id=standard_id,
                standard_edition=standard_edition,
                web_flat_width_mm=required_number(row, "web_flat_width_mm"),
                flange_1_flat_width_mm=required_number(
                    row, "flange_1_flat_width_mm"
                ),
                flange_2_flat_width_mm=required_number(
                    row, "flange_2_flat_width_mm"
                ),
                web_out_to_out_depth_mm=optional_number(
                    row, "web_out_to_out_depth_mm"
                ),
                flange_1_out_to_out_width_mm=optional_number(
                    row, "flange_1_out_to_out_width_mm"
                ),
                flange_2_out_to_out_width_mm=optional_number(
                    row, "flange_2_out_to_out_width_mm"
                ),
                lip_1_flat_width_mm=optional_number(row, "lip_1_flat_width_mm"),
                lip_2_flat_width_mm=optional_number(row, "lip_2_flat_width_mm"),
                lip_1_out_to_out_width_mm=optional_number(
                    row, "lip_1_out_to_out_width_mm"
                ),
                lip_2_out_to_out_width_mm=optional_number(
                    row, "lip_2_out_to_out_width_mm"
                ),
                lip_1_overall_depth_mm=optional_number(
                    row, "lip_1_overall_depth_mm"
                ),
                lip_2_overall_depth_mm=optional_number(
                    row, "lip_2_overall_depth_mm"
                ),
                source_id=source_id,
                notes=optional_text(row, "notes"),
            )
            record.validate_for_section_family(geometries[geometry_id].section_type)
        except ValidationError as error:
            raise row.context.catalog_error(
                None,
                f"Invalid StandardSectionDimensions domain values: {error}",
            ) from error
        dimensions.append(record)
    return tuple(dimensions)


def load_section_catalog(path: str | Path) -> SectionCatalog:
    """Load, join, and validate an approved section catalog workbook."""

    with ExcelCatalogReader(path, SECTION_WORKBOOK_SCHEMA_V0_1) as reader:
        metadata = _parse_metadata(reader, SUPPORTED_SECTION_SCHEMA_VERSIONS)
        if metadata.schema_version == SECTION_SCHEMA_VERSION_V0_2:
            reader.validate_schema(SECTION_WORKBOOK_SCHEMA_V0_2)
        sources, source_rows = _parse_sources(reader)
        geometries, geometry_by_id, geometry_rows = _parse_geometries(reader)
        properties, properties_by_id, property_rows = _parse_properties(reader)
        sections, section_rows = _parse_sections(reader)
        standard_dimensions = (
            _parse_standard_dimensions(
                reader,
                geometry_by_id,
                source_rows.keys(),
            )
            if metadata.schema_version == SECTION_SCHEMA_VERSION_V0_2
            else ()
        )

        source_ids = source_rows.keys()
        section_ids = section_rows.keys()
        referenced_geometry_ids: set[str] = set()
        resolved_sections: list[ResolvedSection] = []
        for section in sections:
            row = section_rows[section.section_id]
            require_reference(
                section.source_id,
                source_ids,
                row.context,
                "source_id",
                "Sources.source_id",
            )
            require_reference(
                section.geometry_id,
                geometry_by_id.keys(),
                row.context,
                "geometry_id",
                "Geometry.geometry_id",
            )
            require_reference(
                section.section_id,
                properties_by_id.keys(),
                row.context,
                "section_id",
                "Properties.section_id",
            )
            section_properties = properties_by_id[section.section_id]
            property_row = property_rows[section.section_id]
            require_reference(
                section_properties.source_id,
                source_ids,
                property_row.context,
                "source_id",
                "Sources.source_id",
            )
            referenced_geometry_ids.add(section.geometry_id)
            try:
                section_dimensions = tuple(
                    item
                    for item in standard_dimensions
                    if item.geometry_id == section.geometry_id
                )
                resolved_sections.append(
                    ResolvedSection(
                        section,
                        geometry_by_id[section.geometry_id],
                        section_properties,
                        section_dimensions,
                    )
                )
            except ValidationError as error:
                raise row.context.catalog_error(
                    None,
                    f"Invalid ResolvedSection consistency: {error}",
                ) from error

        reject_orphans(
            set(geometry_rows) - referenced_geometry_ids,
            reader.source_path.name,
            "Geometry",
            "geometry",
        )
        reject_orphans(
            set(property_rows) - set(section_ids),
            reader.source_path.name,
            "Properties",
            "property",
        )
        return SectionCatalog(
            metadata=metadata,
            sources=sources,
            sections=sections,
            geometries=geometries,
            properties=properties,
            resolved_sections=tuple(resolved_sections),
            standard_dimensions=standard_dimensions,
        )


__all__ = ["load_material_catalog", "load_section_catalog"]
