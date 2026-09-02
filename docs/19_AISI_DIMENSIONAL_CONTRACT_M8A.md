# M8A AISI Dimensional Contract

## Status and authority

This document fixes the dimensional contract required before any M8B
resistance implementation. It is based on the repository primary source,
ANSI/SDI AISI S100-2024, SHA-256
`6ec32742f056d08a0823557d9ce58b69d84312e64a6e656b8ba4b3b10cf4b4ca`.
Printed specification page numbers are used below. Definitions are paraphrased;
the PDF remains authoritative.

M8A creates inputs and applicability checks only. It does not calculate an
effective width, effective area, buckling force, nominal or design resistance,
utilization, or member pass/fail result.

## Dimensional requirements verified from S100-24

| AISI symbol | Engineering meaning in this contract | Requirement | Families | Unit | Exactly available from current `Geometry`? | Explicit catalog input? |
|---|---|---|---|---|---|---|
| `w` | Flat width of the web as a uniformly compressed stiffened element | A1.3 flat-width definition, p. 5; B4.1 Table B4.1-1, p. 26; Appendix 1 Section 1.1(a), pp. 1-1 to 1-2 | `C_LIPPED`, `C_UNLIPPED` | mm | No. `H_mm` is a full centerline segment. | Yes |
| `h` | Flat web depth for the web slenderness limit in bending | B4.1 Table B4.1-1, p. 26 | `C_LIPPED`, `C_UNLIPPED` | mm | No. | Yes; it is the same physical web flat width recorded for `w`, with a different action-specific AISI symbol. |
| `b` / `w` | Flat width of each edge-stiffened flange; Appendix 1 uses `w` for the same element in its simple-lip calculation | B4.1 Table B4.1-1, p. 26; Appendix 1 Section 1.3(a), pp. 1-12 to 1-13 | `C_LIPPED` | mm | No. `B1_mm` and `B2_mm` are centerline segments. | Yes, separately for each flange. |
| `d` / `w` | Flat width of each unstiffened flange | B4.1 Table B4.1-1, p. 26; Appendix 1 Section 1.2.1(a), p. 1-9 | `C_UNLIPPED` | mm | No. | Yes, separately for each flange. |
| `b_o` | Out-to-out width of each edge-stiffened flange | B4.1 Table B4.1-1, p. 26 | `C_LIPPED` | mm | No. | Yes, separately for each flange. |
| `d` | Flat depth of each simple lip edge stiffener | B4.1 Table B4.1-1, p. 26; Appendix 1 Section 1.3(a), pp. 1-12 to 1-13 | `C_LIPPED` | mm | No. `D1_mm` and `D2_mm` are centerline segments. | Yes, separately for each lip. |
| `d_o` | Out-to-out width/depth of each unstiffened simple lip, used with its associated flange `b_o` | B4.1 Table B4.1-1, p. 26 | `C_LIPPED` | mm | No. | Yes, separately for each lip. |
| `D` | Overall depth of each simple lip edge stiffener used by the Section 1.3 stiffener model | Appendix 1 Section 1.3(a), Eqs. 1.3-1 through 1.3-11 and Table 1.3-1, pp. 1-12 to 1-13 | `C_LIPPED` | mm | No. | Yes, separately for each lip. It is not identified with `d_o`. |
| `h_o` | Out-to-out web depth used by the analytical distortional-buckling route | Appendix 2 Section 2.3.3.1, Eqs. 2.3.3.1-1 through 2.3.3.1-7, pp. 2-13 to 2-14 | `C_LIPPED` when that E4 route is used | mm | No. | Yes |
| `t` | Base steel thickness | B4.1 Table B4.1-1 and Appendix 1 Sections 1.1-1.3 | Both | mm | Yes: `Geometry.t_mm`. | No duplicate field. |
| `R` | Inside bend radius | B4.1 Table B4.1-1 | Both | mm | Yes: `Geometry.ri_mm`. | No duplicate field. A zero value does not authorize any other dimensional inference. |
| `theta` | Angle between a flange and its simple lip | Appendix 1 Section 1.3(a) | `C_LIPPED` | degrees | Yes: `Geometry.flange_lip_angle_deg`. | No duplicate field. |

Appendix 2 Table 2.3.3-1 labels its local `b`, `d`, and `h` as mid-line
dimensions. Those existing mechanical quantities remain supplied by
`CenterlineSection`/M3 when E4 is implemented; they are not duplicates of the
flat or out-to-out fields above.

## Repository field mapping

The completed table above is the basis for these unambiguous field names.
They are intentionally physical names rather than bare AISI letters.

| `AISI_Dimensions` field | AISI symbol/use | Verified reference |
|---|---|---|
| `geometry_id` | Physical geometry association | Catalog key |
| `standard_id` | Normative authority identity | ANSI/SDI AISI S100-2024 |
| `standard_edition` | Edition-specific interpretation | 2024 |
| `web_flat_width_mm` | `w` for compression; `h` for bending | B4.1; Appendix 1 Section 1.1 |
| `flange_1_flat_width_mm`, `flange_2_flat_width_mm` | `b`/`w` when edge-stiffened; `d`/`w` when unstiffened | B4.1; Appendix 1 Sections 1.2.1 and 1.3 |
| `web_out_to_out_depth_mm` | `h_o` | Appendix 2 Section 2.3.3.1 |
| `flange_1_out_to_out_width_mm`, `flange_2_out_to_out_width_mm` | `b_o` | B4.1 |
| `lip_1_flat_width_mm`, `lip_2_flat_width_mm` | lip `d` | B4.1; Appendix 1 Section 1.3 |
| `lip_1_out_to_out_width_mm`, `lip_2_out_to_out_width_mm` | lip `d_o` | B4.1 |
| `lip_1_overall_depth_mm`, `lip_2_overall_depth_mm` | lip `D` | Appendix 1 Section 1.3 |
| `source_id` | Provenance of the asserted dimensions | Existing `Sources.source_id` |
| `notes` | Optional non-normative clarification | Catalog metadata |

The unique key is
`(geometry_id, standard_id, standard_edition)`. M8A implements only standard
ID `ANSI_SDI_AISI_S100`, edition `2024`. The normative-source provenance ID
`ANSI_SDI_AISI_S100_2024` is a different identifier and is not a catalog-key
value.

For every dimensional row, the web and both flange flat widths are required.
For `C_LIPPED`, all web out-to-out, flange out-to-out, and lip flat,
out-to-out, and overall dimensions are also required. The lipped-only fields
must be blank for `C_UNLIPPED`. Absence of the entire keyed row is valid and
means that standard-specific dimensions are unavailable; a partially
populated row is invalid.

## Meaning of the three dimensional bases

- `MIDLINE` in `Geometry` means the complete lengths of the ideal straight
  centerline segments used by M3's sharp-corner mechanical model.
- A flat width excludes corner regions and is measured in the element plane,
  following the S100-24 A1.3 definition.
- An out-to-out dimension spans the specified exterior extent and is used only
  where S100-24 calls for that basis.

These bases are not aliases. M8A provides no formula among them and makes no
inference even when `Ri_mm = 0`. `Geometry` remains the only mechanics input;
`AISI_Dimensions` is the only standard-specific dimensional source.

## Catalog version and provenance

Section catalog schema `0.1.0` is the legacy contract and has no normative
dimension sheet. Schema `0.2.0` adds the separate `AISI_Dimensions` sheet and
retains all prior sheets and field meanings unchanged. The production catalog
may contain only the header because its illustrative sections have no trusted
source for these values. Synthetic test rows must identify a test source.

Each dimensional row references the existing `Sources` sheet. Unknown
geometries, unknown sources, duplicate composite keys, unsupported standard
editions, nonfinite/nonpositive values, inconsistent family fields, and
partial rows are errors. A blank sheet below its header is valid.

### Controlled production-workbook migration

The production `sections_catalog.xlsx` was migrated in place from schema
`0.1.0` to `0.2.0` with these audit digests:

- Before: `ac1e38570bf9e86da01e53cc2e05df2a22ef2a05406e27ea2c6ab8abca522b53`
- After: `df50a4c5e6ba75485f7e7e491a074bbd67bb4e922e5105ced486b23d91c3d9f0`

The spreadsheet skill's required `@oai/artifact-tool` runtime was unavailable.
With explicit owner authorization, `openpyxl` was used only for this controlled
migration. No visual render through `artifact-tool` was possible. Independent
programmatic checks confirmed the seven-sheet order, all 17 approved columns,
declared field types, zero data rows and zero formulas in `AISI_Dimensions`,
loader compatibility, and cell-for-cell preservation of `Sections`, `Geometry`,
`Properties`, and `Sources`.

## Resolution and missing-data behavior

M2 loads immutable `StandardSectionDimensions` values and offers exact-key
lookup. M5 attaches the applicable values to the resolved section so design
code never reopens Excel. An unknown key is never represented by zero and
MIDLINE geometry never creates a record. M7 evaluates B4.1 dimensional rules
only from an explicit matching record; otherwise the rule remains
`INDETERMINATE`.

## Mechanical-property authority

Catalog `Properties` remain sourced QA/reference claims. M3A/M3B produce one
coherent computed set (`A`, centroid and inertias, section moduli, radii,
`J`, `Cw`, and shear-center quantities) for future design. M5 must preserve
that complete set together with its verification result and QA gate. Design is
permitted to use the computed set only when the configured required catalog
verification permits it; it must never splice catalog and computed values.

```text
Catalog Properties -> verification against M3 computed properties
                   -> QA gate -> design uses one coherent M3 set
```

## Normative elastic constants

S100-24's symbol list prescribes `E = 203000 MPa`, `G = 78000 MPa`, and
`mu = 0.30`; Appendix 2 Section 2.3.1 repeats the `E` and `G` values for its
elastic-buckling equations. M8A centralizes these as immutable normative
constants with references. They do not overwrite `Material.E`, `Material.nu`,
or its derived `G`. Future S100 calculations use the normative values where
the verified provision prescribes them.

## E4 scope conclusion

E1 requires the least applicable strength from E2 through E4. E4 expressly
addresses open C sections with edge-stiffened flanges; its exception does not
remove distortional buckling of the edge-stiffened flange. Therefore a future
complete `C_LIPPED` EWM axial-compression result must include E4. M8A records
the required `h_o` input but implements no E4 equation. M8B is incomplete until
E4 and its verified elastic distortional input are implemented and validated.

## Project-level applicability gap resolved by M8A.1

A1.1 requires facts about cold forming, qualifying steel product, structural
load-carrying use, and treatment of dynamic effects where relevant. A1.2.3
requires the governing country to resolve the LRFD geographic route. Current
project metadata does not establish these facts. This is a separate contract
gap and does not justify guessing.

M8A.1 adds a versioned project evidence model for country, forming, structural
use, structure application, and dynamic effects. Each declaration includes a
controlled state/value and basis. Missing legacy evidence remains
indeterminate. Material/product qualification was verified as material-
specific under A1.1 and A3.1-A3.2, so it was not hidden behind a project-level
Boolean and remains a separate contract stop. See
[`20_SCOPE_AND_DISTORTIONAL_INPUTS_M8A1.md`](20_SCOPE_AND_DISTORTIONAL_INPUTS_M8A1.md).
