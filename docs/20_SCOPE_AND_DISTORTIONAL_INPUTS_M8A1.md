# M8A.1 Scope Evidence and Distortional Inputs

## Status and primary authority

M8A.1 completes typed inputs and eligibility gates only. It implements no
effective width, buckling force, nominal/design resistance, utilization, E4
strength, DSM strength, or pyCUFSM integration.

The governing source is ANSI/SDI AISI S100-2024, repository SHA-256
`6ec32742f056d08a0823557d9ce58b69d84312e64a6e656b8ba4b3b10cf4b4ca`.
The implementation was checked directly against A1.1 and A1.2.3 on printed
specification page 1, A3.1-A3.2 on printed pages 14-19, and Appendix 2 Section
2.3.3.1 on printed pages 2-13 to 2-14. Descriptions below are original
paraphrases; the PDF remains authoritative.

## Project scope-evidence contract

Project YAML schema `0.2.0` adds `aisi_scope_evidence`. Each engineering
declaration carries a controlled value/state and a nonblank `basis`:

| YAML path | Typed values | Purpose |
|---|---|---|
| `governing_country.country` | `UNITED_STATES`, `MEXICO`, `CANADA`, `UNKNOWN` | Evaluates only the A1.2.3 design-format route. |
| `structure_application.application` | `BUILDING`, `OTHER_STRUCTURE`, `UNKNOWN` | Distinguishes the A1.1 branch that requires dynamic-effects allowances. |
| `cold_formed_to_shape.state` | `TRUE`, `FALSE`, `UNKNOWN` | Declares the forming-process fact. |
| `structural_load_carrying_use.state` | `TRUE`, `FALSE`, `UNKNOWN` | Declares structural load-carrying use. |
| `dynamic_effects_addressed.state` | `TRUE`, `FALSE`, `UNKNOWN` | Resolves the nonbuilding branch only. |

Every mapping also has `basis`. `UNKNOWN` is a first-class state and never
means `FALSE`. In schema `0.2.0`, the evidence section and its fields are
required so missing provenance cannot be hidden. Legacy schema `0.1.0` remains
loadable; its missing declarations become typed `UNKNOWN` values with an
explicit legacy-contract basis, so M7 stays `INDETERMINATE`.

The production project is a template and therefore records `UNKNOWN` rather
than inventing evidence. Its controlled migration is:

- schema: `0.1.0` -> `0.2.0`;
- prior SHA-256:
  `759e66a3eb6829b74e3cc3f1cffbb9974a073359081a7f90c7e7ae8bc6921932`;
- current SHA-256:
  `a2e13a538d086e1048035d8b47b4f6d53f6d3d41196d6a98ff431aac36c94d42`.

## Why steel-product qualification is not project evidence

A1.1 identifies carbon or low-alloy sheet, strip, plate, or bar. A3.1 then
ties unrestricted or restricted use to individual steel specifications,
grades, elongation groups, thickness/class qualifications, and required test
reports. A3.2 provides a separate route for other steels with additional
chemical, mechanical, documentation, coating/welding, and ductility
conditions as applicable.

The current material contract has a free-text specification and grade plus
strengths and source, but it does not establish product form, carbon/low-alloy
class, A3 route, elongation classification, or route-specific evidence.
Consequently `qualifying_steel_product` cannot safely be asserted once at
project level. M7 retains a member-material check as `INDETERMINATE` and
reports the material ID/specification/grade/source it could observe.

The minimal future change is a versioned, edition-keyed material-qualification
record rather than a project Boolean. A proposed separate
`AISI_Material_Qualification` worksheet would key
`material_id + standard_id + standard_edition` and record controlled product
form, steel class, A3 qualification route, three-state qualification status,
source/basis, and only the route-specific facts needed to audit that status
(including elongation basis where applicable). Existing material values would
remain unchanged. This proposal requires separate owner approval; M8A.1 does
not modify `materials_catalog.xlsx`.

## M7 A1.1 and A1.2.3 behavior

M7 now receives optional `AISIProjectScopeEvidence`:

- supporting `TRUE` declarations make the corresponding condition evaluable;
- an explicit failed A1.1 condition yields `NOT_APPLICABLE`;
- missing/`UNKNOWN` evidence yields `INDETERMINATE`;
- a declared building does not require the nonbuilding dynamic-effects fact;
- `OTHER_STRUCTURE + FALSE` dynamic-effects evidence yields
  `NOT_APPLICABLE`;
- LRFD is applicable for `UNITED_STATES` and `MEXICO`, not for the declared
  Canadian route; unknown country remains indeterminate.

These project checks do not infer facts from project name/location, member
forces, material free text, bracing, or ETABS data. The unresolved
material-qualification check remains independent and prevents an overall
`APPLICABLE` conclusion until its contract is approved.

## Explicit distortional restraint length

Members schema `0.2.0` adds these optional `Members` columns:

- `distortional_unbraced_length_mm`;
- `distortional_restraint_source`.

The first maps to Appendix 2 Section 2.3.3.1 symbol `Lm`: the distance between
discrete restraints that restrict distortional buckling. The second is a
required nonblank basis whenever `Lm` is supplied. `Lm` must be finite and
greater than zero. Both cells may be blank where the future calculation does
not require them; supplying only one is invalid.

`Lm` is a distinct restraint declaration. It is never populated from
`Lb_mm`, `lateral_brace_spacing_mm`, translation restraint, torsion restraint,
or warping restraint. M1 stores it on immutable `Restraints`; the member loader
maps it once, and M5 preserves the same value in `ResolvedMember`. Future EWM
code must read the resolved member rather than reopening Excel.

Members schema `0.1.0` remains loadable and yields `None` for both new fields.
The production workbook migration target is `0.1.0 -> 0.2.0`, preserving all
existing cells and adding blank values only. Its prior SHA-256 is
`288d2fe4bea7cbe514884db6fec52e5b5b13a433e2d3ac64a5d1136fad855ee8`.
The new digest will be recorded after the controlled physical workbook
migration and verification.

## Analytical E4 software limitation

Appendix 2 Section 2.3.3.1 limits its analytical compression solution to open
sections with stiffened flanges of equal dimension and sends members outside
its geometric criteria to the Section 2.2 numerical route. Table 2.3.3-1
explicitly defines its `b`, `d`, and `h` as mid-line dimensions. Therefore
equal-flange eligibility is not based solely on the flat/out-to-out fields:

- both M3 `MIDLINE` flange and lip pairs must be exactly equal;
- the paired standard-specific flange/lip dimensions must also be exactly
  equal so the resolved physical record does not contradict that condition;
- the S100 dimensional record supplies the separate out-to-out web depth;
- explicit `Lm` and its source must be present for future execution.

The equality tolerance is exactly `0.0 mm`; no fuzzy comparison, rounding, or
conversion among mid-line, flat, and out-to-out bases is permitted. An unequal
lipped C remains normatively evaluated by the applicable S100 rules, but its
software status is `UNSUPPORTED` with the Section 2.2 numerical route noted.
Missing required E4 data is `INVALID_INPUT`, not a fabricated value.

The numerical Section 2.2 procedure is future capability requiring separate
implementation and validation. M8A.1 neither implements it nor assumes that
pyCUFSM satisfies it.

## Protected-contract audit

M8A.1 does not authorize changes to these files. Their expected unchanged
digests are:

| File | SHA-256 |
|---|---|
| `materials_catalog.xlsx` | `586a312c4787b1b97e8af8e8efec2c86a7b1e23c9f95db09521379cdc62fb80d` |
| `sections_catalog.xlsx` | `df50a4c5e6ba75485f7e7e491a074bbd67bb4e922e5105ced486b23d91c3d9f0` |
| `ETABS_results.xlsx` | `be2fc3b9b9d9fa57ca648fca533017bad6c4b572db2adbd7538d70b7cdd300ab` |
| `AGENTS.md` | `875d0f22c3f1f104dc1bab2879f35101568fbded0c695fe7d47cad66efff1547` |
| S100-24 PDF | `6ec32742f056d08a0823557d9ce58b69d84312e64a6e656b8ba4b3b10cf4b4ca` |

No dependency is added. The required spreadsheet `@oai/artifact-tool` runtime
is unavailable in this session, so physical `members.xlsx` migration and
render verification remain pending unless the owner separately authorizes the
same controlled `openpyxl` fallback previously limited to the section catalog.
