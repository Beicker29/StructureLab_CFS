# M8A.2 AISI Material Qualification

## Status and authority

M8A.2 implements a typed, edition-specific evidence contract for AISI S100-24
material applicability. It calculates no strength, reduction, effective width,
or utilization. The primary source is the repository S100-24 PDF, SHA-256
`6ec32742f056d08a0823557d9ce58b69d84312e64a6e656b8ba4b3b10cf4b4ca`.
A3.1 and A3.2 were checked directly on printed specification pages 14 through
19. The descriptions below are original paraphrases; the PDF remains
authoritative.

The code supports legacy material schema `0.1.0` and the new contract schema
`0.2.0`. The production workbook was migrated under explicit owner
authorization. The required `artifact-tool` runtime was unavailable, so visual
render validation through that tool was not possible; `openpyxl` was used only
for this controlled physical migration.

## Requirement map

| AISI requirement | Clause | Route | Existing repository field | Missing evidence field | Required provenance | Representation |
|---|---|---|---|---|---|---|
| Structural steel specification provides mandatory mechanical properties | A3.1 | A3.1 | `Material.specification` identifies the supplied specification but does not prove its requirements | `mandatory_mechanical_properties_state` | qualification source and basis | controlled requirement state |
| Specification requires reports confirming mechanical properties | A3.1 | A3.1 | none | `test_reports_required_state` | qualification source and basis | controlled requirement state |
| Tensile/yield ratio for the high-elongation group | A3.1.1 | A3.1/A3.2 as applicable | `Material.Fu` and `Material.Fy` | none duplicated | existing material source plus qualification basis | loader evaluates existing `Fu/Fy >= 1.08` |
| Minimum elongation and permitted gauge/test basis | A3.1.1-A3.1.2 | A3.1/A3.2 as applicable | none | elongation percent, gauge length, test standard, group | qualification source and basis | explicit numeric/test evidence |
| Less-than-3-percent group is limited to multiple-web roofing, siding, or decking | A3.1.3 | A3.1/A3.2 as applicable | current C family establishes a single-web member | `elongation_group` | qualification source and basis | current single-web C result is `NOT_APPLICABLE` |
| Other steel conforms to chemical/mechanical requirements of a published specification | A3.2(a) | A3.2 | `Material.specification`, `Fy`, `Fu` remain referenced, not copied | `chemical_mechanical_conformance_state` | qualification source and basis | controlled requirement state |
| Properties determined by producer/supplier/purchaser under the reference specification | A3.2(b) | A3.2 | none | `properties_determined_per_reference_state` | qualification source and basis | controlled requirement state |
| Coating requirements established for coated sheet | A3.2(c) | A3.2 | none | `coating_requirements_state` | qualification source and basis | `SATISFIED` or explicitly `NOT_APPLICABLE` |
| Weld suitability established when welding is intended | A3.2(d) | A3.2 | no connection/welding design in v0.1 | `welding_requirements_state` | qualification source and basis | `SATISFIED` or explicitly `NOT_APPLICABLE` |
| Production identification/documentation, or master-coil overstrength alternative | A3.2 | A3.2 | none | production-identification and 10-percent-overstrength states | qualification source and basis | conditional controlled states |
| Alternative ductility thresholds and approved test | A3.2.1 | A3.2 | none | local/uniform elongation and ductility test standard | qualification source and basis | explicit evidence; member-use result remains indeterminate |

The material row already owns `material_id`, specification, grade, `Fy`, `Fu`,
`E`, `nu`, density and its source. None of those values is duplicated in the
qualification row.

## Schema 0.2 worksheet

`AISI_Material_Qualification` is keyed by
`(material_id, standard_id, standard_edition)`. It contains:

| Field | Type | Requirement |
|---|---|---|
| `material_id` | text | existing `Materials.material_id` |
| `standard_id` | controlled text | `ANSI_SDI_AISI_S100` in M8A.2 |
| `standard_edition` | integer | `2024` in M8A.2 |
| `qualification_route` | enum | `A3_1` or `A3_2` |
| `qualification_state` | enum | `QUALIFIED`, `NOT_QUALIFIED`, `INDETERMINATE` |
| `product_form` | enum | `SHEET`, `STRIP`, `PLATE`, `BAR`, `UNKNOWN` |
| `steel_classification` | enum | `CARBON`, `LOW_ALLOY`, `UNKNOWN` |
| `elongation_group` | enum | `A3_1_1_GE_10`, `A3_1_2_GE_3_LT_10`, `A3_1_3_LT_3`, `A3_2_1_ALTERNATIVE_DUCTILITY`, `UNKNOWN` |
| `minimum_elongation_percent` | optional number | required for qualified A3.1 elongation groups |
| `elongation_gauge_length_mm` | optional number | 50 or 200 mm as permitted by the selected group |
| `elongation_test_standard` | optional controlled text | `ASTM_A370` or `ASTM_A1058` for qualified A3.1 groups |
| `mandatory_mechanical_properties_state` | requirement state | A3.1 evidence |
| `test_reports_required_state` | requirement state | A3.1 evidence |
| `chemical_mechanical_conformance_state` | requirement state | A3.2 evidence |
| `properties_determined_per_reference_state` | requirement state | A3.2 evidence |
| `coating_requirements_state` | requirement state | A3.2 conditional evidence |
| `welding_requirements_state` | requirement state | A3.2 conditional evidence |
| `production_identification_state` | requirement state | A3.2 documentation branch |
| `master_coil_10_percent_overstrength_state` | requirement state | A3.2 fallback branch |
| `local_elongation_percent` | optional number | A3.2.1 evidence |
| `uniform_elongation_percent` | optional number | A3.2.1 evidence |
| `ductility_test_standard` | optional text | A3.2.1 approved-test identity |
| `source_id` | text | existing `Sources.source_id`; mandatory |
| `basis` | text | nonblank engineering/document basis; mandatory |
| `notes` | optional text | non-normative clarification |

Every requirement-state field uses `SATISFIED`, `NOT_SATISFIED`,
`NOT_APPLICABLE`, or `UNKNOWN`. Qualified records reject mixed A3.1/A3.2.1
evidence, missing route facts, unknown product/class/group, unsupported
standards, bad references, duplicate keys, partial rows, and formulas.

## Qualification semantics

- A missing exact-key record is an explicit missing outcome and makes the M7
  material check `INDETERMINATE`.
- `INDETERMINATE` is not converted to a failure.
- A sourced `NOT_QUALIFIED` record makes the corresponding normative check
  `NOT_APPLICABLE`; it is not a software `UNSUPPORTED` result.
- A valid `QUALIFIED` A3.1.1 or A3.1.2 route makes the material check
  `APPLICABLE`.
- A3.1.2 remains distinguishable so a future authorized engine can apply its
  prescribed material-strength treatment. M8A.2 computes none of it.
- A3.1.3 is `NOT_APPLICABLE` to the current resolved single-web C member.
- A3.2.1 remains `INDETERMINATE` at member level because the approved member
  contract does not distinguish purlin, girt, and curtain-wall-stud use. No
  member field was added or inferred.

Specification and grade strings, even familiar ones, never create a
qualification record.

## Catalog API and compatibility

`MaterialCatalog` and `CatalogRegistry` expose exact-key `find_...` and
`get_material_qualification(...)` lookups. The former returns `None` for
missing evidence; the latter raises an explicit catalog error. Schema `0.1.0`
continues to load all legacy materials and exposes an empty qualification
tuple. Schema `0.2.0` requires the worksheet even when it has only its header.

No production qualification evidence has been invented. The production
worksheet contains exactly the approved 25-column header and zero data rows.

## Controlled physical migration

Only `data/catalogs/materials_catalog.xlsx` was migrated:

- schema: `0.1.0` -> `0.2.0`;
- previous SHA-256:
  `586a312c4787b1b97e8af8e8efec2c86a7b1e23c9f95db09521379cdc62fb80d`;
- new SHA-256:
  `7d8933e97de272f4ec6b5105a8f17ce48130d2bbcac6be6e2eaf9e25ff243910`;
- worksheet order: `Metadata`, `Materials`,
  `AISI_Material_Qualification`, `Sources`, `Schema`;
- 25 qualification columns and 25 matching `Schema` declarations;
- zero qualification data rows and zero introduced formulas;
- all 36 pre-existing `Materials` cells, all 16 pre-existing `Sources` cells,
  and all 147 pre-existing `Schema` cells preserved semantically cell by cell;
- the only pre-existing populated-cell value changed was the authorized
  `Metadata.schema_version` value.

The migration check reloaded the written workbook and verified sheet order,
headers, declared field types, empty production content, absence of formulas,
and preservation of pre-existing cell values and styles. `openpyxl` normalized
the internal type/style serialization of the already empty `Sources!G2` cell;
its value, formatting semantics, comment, and hyperlink state remained empty
and unchanged. The other protected contracts, `AGENTS.md`, and the normative
PDF were hash-checked separately and were not modified.

The focused catalog/contract regression set passed with `92 passed`. After
updating synthetic fixtures to use the now-existing production worksheet, the
full suite passed with `504 passed in 17.28s`.
