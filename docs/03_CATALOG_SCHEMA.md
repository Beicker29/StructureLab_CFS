# Catalog Schemas and Loading

The Excel workbooks are immutable, versioned input contracts. M2 reads them at
the catalog boundary and produces M1 domain objects; downstream packages do not
know how Excel is stored.

```text
Excel
  -> authoritative schema validation
  -> contextual row parsing
  -> catalog-level uniqueness/reference validation
  -> M1 domain construction and intrinsic validation
  -> immutable catalog container
  -> CatalogRegistry
```

## Supported schema and authority

The materials and section loaders support legacy `0.1.0` and current `0.2.0`;
any other declared version raises
`SchemaError` rather than triggering a best-effort parse. Section `0.1.0`
contains no standard-specific dimensions. Section `0.2.0` requires the
separate `AISI_Dimensions` worksheet even when it contains only its header.

Required worksheets and column names are defined independently in
`cfs_design.catalogs.schemas`. The workbook's `Schema` worksheet remains
required documentation but is not trusted as the application's sole schema
authority. Column positions are discovered from names; numeric positions are
not hard-coded.

## Metadata and sources

Both catalogs parse `Metadata` fields including `name`, `schema_version`,
`canonical_units`, and `description`, while retaining other supplied metadata
as immutable key/value pairs. The loader also records the resolved source path
and SHA-256 of the workbook bytes without modifying the file.

Each `Sources` row becomes an immutable `CatalogSource`. IDs are unique within
their workbook, required source fields must be populated, and source types use
the controlled v0.1 vocabulary. Materials, section identities, and section
properties must reference an existing source.

## Materials catalog

`data/catalogs/materials_catalog.xlsx` requires:

- `Metadata`;
- `Materials`;
- `Sources`; and
- `Schema`.

Schema `0.2.0` additionally requires `AISI_Material_Qualification`, even when
the sheet contains only its header. Its exact fields and A3 route validation
are documented in
[`21_AISI_MATERIAL_QUALIFICATION_M8A2.md`](21_AISI_MATERIAL_QUALIFICATION_M8A2.md).
The unique key is `(material_id, standard_id, standard_edition)`; every record
references both `Materials.material_id` and `Sources.source_id`. Formulas are
prohibited in qualification evidence.

Every nonblank `Materials` row becomes the existing M1 `Material` object.
Catalog validation checks unique `material_id`, unique source IDs, and material
source references. Physical rules such as `Fy > 0`, `Fu >= Fy`, `E > 0`, and
Poisson-ratio limits remain authoritative in `Material` and are not duplicated
by the loader.

Active and inactive rows are both preserved. `active_materials` is a filtered
tuple view; it does not remove inactive illustrative entries from the catalog.
Project use of inactive materials is deferred to M5.

## Sections catalog

`data/catalogs/sections_catalog.xlsx` requires:

- `Metadata`;
- `Sections` for `CatalogSection` identity;
- `Geometry` for `SectionGeometry`;
- `Properties` for catalog-supplied `SectionProperties`;
- `AISI_Dimensions` for edition-specific normative dimensions in schema
  `0.2.0`;
- `Sources`; and
- `Schema`.

The three engineering worksheets remain separate while parsing. The loader
validates unique section IDs, geometry IDs, property section IDs, and source
IDs. Every section must reference one existing geometry and exactly one
property row. Section and property sources must exist. Orphan geometry and
property rows are catalog-quality errors.

`AISI_Dimensions` uses the unique key
`(geometry_id, standard_id, standard_edition)` and references both an existing
geometry and an existing `Sources.source_id`. M8A implements only
`ANSI_SDI_AISI_S100`, edition `2024`. Common web/flange flat widths are
mandatory whenever a row exists. A `C_LIPPED` row additionally requires the
complete web out-to-out, flange out-to-out, and lip flat/out-to-out/overall
set; those lipped-only fields must be blank for `C_UNLIPPED`. Missing complete
records are permitted and do not generate zeros or inferred values.

The exact field-to-symbol mapping and dimensional meanings are in
[`19_AISI_DIMENSIONAL_CONTRACT_M8A.md`](19_AISI_DIMENSIONAL_CONTRACT_M8A.md).
No `Geometry` field changed meaning in the `0.1.0 -> 0.2.0` migration.

For each valid identity row, the loader constructs a `ResolvedSection` and
thereby checks section/property IDs plus `CatalogSection.family` against
`SectionGeometry.section_type`. Unknown enum text is rejected; it is never
silently converted to `OTHER`.

Inactive sections remain present and resolvable. `active_sections` provides a
filtered immutable view only.

## Cell parsing

- Entirely blank rows are ignored.
- A partially populated meaningful row is an error with workbook, worksheet,
  row, and field context where practical.
- Required numeric fields accept finite Excel numeric values only; malformed
  text and booleans are not coerced.
- Optional blank numeric cells become `None`, never zero.
- Native Excel booleans and controlled `TRUE`/`FALSE` text are accepted.
  Arbitrary truthiness is prohibited.
- The loader opens workbooks with cached formula results (`data_only=True`) and
  never evaluates formulas. A required formula cell without a usable cached
  value fails explicitly.

Domain constructors continue to enforce intrinsic physical invariants. Loader
errors add catalog/row context without reimplementing those invariants.

## Immutable containers and public API

`MaterialCatalog` preserves metadata, sources, all materials, and immutable
standard-specific material qualifications.
`SectionCatalog` preserves metadata, sources, identities, geometries,
properties, standard-specific dimensions, and resolved sections. Public
collections and active views are tuples; lookup indexes are private read-only
mappings.

`CatalogRegistry` is an immutable, non-global access point:

```python
from cfs_design.catalogs import (
    CatalogRegistry,
    load_material_catalog,
    load_section_catalog,
)

registry = CatalogRegistry(
    load_material_catalog(materials_path),
    load_section_catalog(sections_path),
)
material = registry.get_material(material_id)
section = registry.get_section(section_id)  # ResolvedSection
dimensions = registry.get_standard_dimensions(
    geometry_id,
    "ANSI_SDI_AISI_S100",
    2024,
)
qualification = registry.find_material_qualification(
    material_id,
    "ANSI_SDI_AISI_S100",
    2024,
)
```

Missing required IDs raise `CatalogError`; lookups do not return `None`.

## Deliberately deferred

M2 reads supplied catalog properties and standard dimensions exactly as
values. It does not calculate
area, centroid, inertia, section modulus, radii, `J`, `Cw`, or shear-center
coordinates. It does not compare catalog values with geometry-derived values.
Those calculations and `CatalogVerificationResult` belong to M3. In
particular, M2 never converts `MIDLINE` geometry into AISI dimensions.

M2 also does not load `project.yaml`, `members.xlsx`, or ETABS exports and does
not implement project resolution, AISI methods, pyCUFSM, resistance, or
utilization.

Material `specification` and `grade` do not by themselves establish the A1.1
steel-product/A3 qualification route. M8A.2 resolves that only through an
exact, sourced qualification record. Missing legacy or current evidence stays
`INDETERMINATE`; no catalog string is inferred.
