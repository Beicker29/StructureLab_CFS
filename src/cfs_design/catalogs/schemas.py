"""Authoritative versioned schemas for approved catalog workbooks."""

from dataclasses import dataclass


SUPPORTED_SCHEMA_VERSION = "0.1.0"
MATERIAL_SCHEMA_VERSION = "0.1.0"
SECTION_SCHEMA_VERSION_V0_1 = "0.1.0"
SECTION_SCHEMA_VERSION_V0_2 = "0.2.0"
SUPPORTED_SECTION_SCHEMA_VERSIONS = (
    SECTION_SCHEMA_VERSION_V0_1,
    SECTION_SCHEMA_VERSION_V0_2,
)


@dataclass(frozen=True, slots=True)
class SheetSchema:
    name: str
    columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkbookSchema:
    sheets: tuple[SheetSchema, ...]


METADATA_COLUMNS = ("Field", "Value", "Description")
SCHEMA_COLUMNS = (
    "Sheet",
    "Field",
    "Required",
    "Type",
    "Unit",
    "Description",
    "Validation / Notes",
)
SOURCE_COLUMNS = (
    "source_id",
    "source_type",
    "organization",
    "document_or_catalog",
    "edition_or_date",
    "page_or_table",
    "url",
    "notes",
)
MATERIAL_COLUMNS = (
    "material_id",
    "designation",
    "specification",
    "grade",
    "Fy_MPa",
    "Fu_MPa",
    "E_MPa",
    "nu",
    "density_kg_m3",
    "source_id",
    "active",
    "notes",
)
SECTION_COLUMNS = (
    "section_id",
    "designation",
    "family",
    "manufacturer",
    "geometry_id",
    "source_id",
    "active",
    "notes",
)
GEOMETRY_COLUMNS = (
    "geometry_id",
    "section_type",
    "H_mm",
    "B1_mm",
    "B2_mm",
    "D1_mm",
    "D2_mm",
    "t_mm",
    "Ri_mm",
    "web_flange_angle_deg",
    "flange_lip_angle_deg",
    "geometry_convention",
    "notes",
)
PROPERTY_COLUMNS = (
    "section_id",
    "A_mm2",
    "x_bar_mm",
    "y_bar_mm",
    "Ix_mm4",
    "Iy_mm4",
    "Ixy_mm4",
    "I1_mm4",
    "I2_mm4",
    "theta_p_deg",
    "Sx_pos_mm3",
    "Sx_neg_mm3",
    "Sy_pos_mm3",
    "Sy_neg_mm3",
    "rx_mm",
    "ry_mm",
    "J_mm4",
    "Cw_mm6",
    "x0_mm",
    "y0_mm",
    "property_basis",
    "source_id",
    "notes",
)
AISI_DIMENSION_COLUMNS = (
    "geometry_id",
    "standard_id",
    "standard_edition",
    "web_flat_width_mm",
    "flange_1_flat_width_mm",
    "flange_2_flat_width_mm",
    "web_out_to_out_depth_mm",
    "flange_1_out_to_out_width_mm",
    "flange_2_out_to_out_width_mm",
    "lip_1_flat_width_mm",
    "lip_2_flat_width_mm",
    "lip_1_out_to_out_width_mm",
    "lip_2_out_to_out_width_mm",
    "lip_1_overall_depth_mm",
    "lip_2_overall_depth_mm",
    "source_id",
    "notes",
)

MATERIAL_WORKBOOK_SCHEMA = WorkbookSchema(
    sheets=(
        SheetSchema("Metadata", METADATA_COLUMNS),
        SheetSchema("Materials", MATERIAL_COLUMNS),
        SheetSchema("Sources", SOURCE_COLUMNS),
        SheetSchema("Schema", SCHEMA_COLUMNS),
    )
)

SECTION_WORKBOOK_SCHEMA_V0_1 = WorkbookSchema(
    sheets=(
        SheetSchema("Metadata", METADATA_COLUMNS),
        SheetSchema("Sections", SECTION_COLUMNS),
        SheetSchema("Geometry", GEOMETRY_COLUMNS),
        SheetSchema("Properties", PROPERTY_COLUMNS),
        SheetSchema("Sources", SOURCE_COLUMNS),
        SheetSchema("Schema", SCHEMA_COLUMNS),
    )
)

SECTION_WORKBOOK_SCHEMA_V0_2 = WorkbookSchema(
    sheets=(
        SheetSchema("Metadata", METADATA_COLUMNS),
        SheetSchema("Sections", SECTION_COLUMNS),
        SheetSchema("Geometry", GEOMETRY_COLUMNS),
        SheetSchema("Properties", PROPERTY_COLUMNS),
        SheetSchema("AISI_Dimensions", AISI_DIMENSION_COLUMNS),
        SheetSchema("Sources", SOURCE_COLUMNS),
        SheetSchema("Schema", SCHEMA_COLUMNS),
    )
)

# The unversioned name denotes the current section-catalog contract.
SECTION_WORKBOOK_SCHEMA = SECTION_WORKBOOK_SCHEMA_V0_2

SOURCE_TYPES = frozenset({"STANDARD", "MANUFACTURER", "PAPER", "OTHER"})

__all__ = [
    "MATERIAL_WORKBOOK_SCHEMA",
    "MATERIAL_SCHEMA_VERSION",
    "SECTION_WORKBOOK_SCHEMA",
    "SECTION_WORKBOOK_SCHEMA_V0_1",
    "SECTION_WORKBOOK_SCHEMA_V0_2",
    "SECTION_SCHEMA_VERSION_V0_1",
    "SECTION_SCHEMA_VERSION_V0_2",
    "SUPPORTED_SCHEMA_VERSION",
    "SUPPORTED_SECTION_SCHEMA_VERSIONS",
]
