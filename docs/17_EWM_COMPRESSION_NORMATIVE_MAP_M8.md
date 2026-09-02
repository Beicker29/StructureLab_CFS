# M8 EWM Compression Normative Map and Stop Record

## Status

**M8 engineering implementation is stopped before resistance code.** The
S100-24 calculation chain was mapped from the registered primary PDF, but the
approved inputs do not establish several quantities and policies required to
execute that chain without an unapproved interpretation.

No EWM equation, resistance factor, buckling calculation, effective-width
calculation, effective-area calculation, design result, or report calculation
was implemented. No approved schema was changed.

This is the M8 stop condition required by the milestone: documenting the gap is
safer than treating `MIDLINE` dimensions as AISI flat or exterior dimensions.

M8A subsequently approved and implemented the dimensional/data-basis
decisions, while still stopping before resistance. The controlling current
contract is [`19_AISI_DIMENSIONAL_CONTRACT_M8A.md`](19_AISI_DIMENSIONAL_CONTRACT_M8A.md).
The findings below remain the historical primary-source record that led to
that migration.

## Primary authority inspected

| Field | Verified value |
|---|---|
| Standard | ANSI/SDI AISI S100-2024 |
| Repository source | `references/standards/AISI_S100-24/ANSI-SDI-AISI-S100-2024-SDI-AISI-S100-2024-C.pdf` |
| SHA-256 | `6ec32742f056d08a0823557d9ce58b69d84312e64a6e656b8ba4b3b10cf4b4ca` |
| Relevant specification pages | 1, 5, 26, 43-47, 1-1 to 1-13, and 2-1 to 2-14 |

The cited page numbers in this document are the printed specification page
numbers, not PDF viewer indexes. All descriptions below are short original
paraphrases. The PDF remains the normative authority.

## Contract preservation audit

The M8 audit did not modify any approved input or standard file. Hashes after
the documentation change are:

| Approved file | SHA-256 |
|---|---|
| `data/catalogs/materials_catalog.xlsx` | `586a312c4787b1b97e8af8e8efec2c86a7b1e23c9f95db09521379cdc62fb80d` |
| `data/catalogs/sections_catalog.xlsx` | `ac1e38570bf9e86da01e53cc2e05df2a22ef2a05406e27ea2c6ab8abca522b53` |
| `projects/PRJ_001/members.xlsx` | `288d2fe4bea7cbe514884db6fec52e5b5b13a433e2d3ac64a5d1136fad855ee8` |
| `projects/PRJ_001/ETABS_results.xlsx` | `be2fc3b9b9d9fa57ca648fca533017bad6c4b572db2adbd7538d70b7cdd300ab` |
| `projects/PRJ_001/project.yaml` | `759e66a3eb6829b74e3cc3f1cffbb9974a073359081a7f90c7e7ae8bc6921932` |
| registered S100-24 PDF | `6ec32742f056d08a0823557d9ce58b69d84312e64a6e656b8ba4b3b10cf4b4ca` |

## Required calculation sequence established from S100-24

For a concentrically compressed member, the normative sequence is:

```text
A1 and B4 applicability
    -> Appendix 2 global elastic buckling
    -> E2 nominal yielding/global strength and Fn
    -> Appendix 1 effective widths evaluated at Fn
    -> E3.1 effective area and local/global interacting nominal strength
    -> E4 distortional strength where applicable
    -> E1 smallest applicable available axial strength
```

For pure axial compression, Appendix 1 states that the element stress is
`Fn`. The effective widths therefore follow directly after E2; no
effective-area/stress iteration was identified for this uniform compression
case. That conclusion does not authorize implementing the chain while its
required geometry remains unresolved.

## Normative equation map

The implementation targets are proposed locations only. None exists as an M8
calculation implementation at this stop point.

| Rule / calculation | S100-24 clause | Equation / table | Inputs required | Proposed repository target | Validation source | Notes |
|---|---|---|---|---|---|---|
| Specification member scope | A1.1, p. 1 | — | thickness, forming process, qualifying steel product, load-carrying use, dynamic-effects context when relevant | existing `normative.applicability` | Primary PDF | M7 can evaluate thickness but deliberately leaves the other facts indeterminate. |
| LRFD geographic applicability | A1.2.3, p. 1 | — | governing country and LRFD selection | existing `normative.applicability` | Primary PDF | LRFD is associated with the United States and Mexico; governing country is not in `DesignContext`. |
| Ordinary EWM applicability limits | B4.1, p. 26 | Table B4.1-1 | `w`, `b`, `bo`, `d`, `do`, `t`, `R`, `Is`, `Ia`, edge-stiffener type, intermediate-stiffener counts, `Fy` as applicable | existing `normative.applicability` | Primary PDF | The table explicitly distinguishes flat and out-to-out dimensions. M7 correctly returns `INDETERMINATE` for the current geometry. |
| Route outside B4.1 | B4.2, p. 27 | — | test or rational-analysis evidence and calibrated factors | future, outside ordinary M8 route | Primary PDF | Not a silent fallback for missing dimensions. |
| Governing axial strength | E1, p. 43 | — | all applicable results from E2 through E4 | future `design.ewm.compression` | Primary PDF | The available axial strength is the smallest applicable value. |
| Flexural elastic forces | Appendix 2, 2.3.1, pp. 2-3 to 2-4 | Eqs. 2.3.1-1 and 2.3.1-2 | `E`, `Ix`, `Iy`, `KxLx`, `KyLy` | future global-buckling component | Primary PDF plus independent arithmetic | Both axes must be considered for the supported C sections. |
| Torsional elastic force | Appendix 2, 2.3.1, p. 2-3 | Eq. 2.3.1-3 | `E`, `G`, `Cw`, `J`, `ro`, `KtLt` | future global-buckling component | Primary PDF plus independent arithmetic | Requires M3B properties and an approved property-authority policy. |
| Flexural-torsional coefficient | Appendix 2, 2.3.1, p. 2-3 | Eq. 2.3.1-4 | `xo`, `ro`, `KxLx`, `KtLt` | future global-buckling component | Primary PDF plus independent arithmetic | For a singly symmetric C, the equation uses the symmetry-axis convention established by the section coordinates. |
| Polar radius about shear center | Appendix 2, 2.3.1, p. 2-4 | Eq. 2.3.1-7 | `Ix`, `Iy`, `A`, `xo`, `yo` | future global-buckling component | Primary PDF plus independent arithmetic | Must use one coherent gross-property set. |
| Global compression buckling stress | Appendix 2, 2.3.1.1, p. 2-5 | Eq. 2.3.1.1-1 | governing `Pcre`, `Ag` | future global-buckling component | Primary PDF plus independent arithmetic | `Fcre = Pcre / Ag`. |
| Pure flexural candidate | Appendix 2, 2.3.1.1.1, pp. 2-5 to 2-6 | Eq. 2.3.1.1.1-1 | `E`, `I`, `KL` for each applicable axis | future global-buckling component | Primary PDF plus independent arithmetic | The smallest flexural force is retained. |
| Singly symmetric C flexural-torsional candidate | Appendix 2, 2.3.1.1.2, p. 2-6 | Eq. 2.3.1.1.2-1 | `Pex`, `Pt`, `beta` | future global-buckling component | Primary PDF plus independent arithmetic | S100-24 requires the smaller of the flexural result and this coupled result; Euler flexure alone is insufficient. |
| Elastic force/stress conversion | Appendix 2, 2.1, p. 2-1 | Eq. 2.1-1 | `Ag`, `Fcr` or `Pcr` | shared future buckling mechanics | Primary PDF | Compression conversion normally uses gross area. |
| Nominal yielding/global axial strength | E2, p. 43 | Eq. E2-1 | `Ag`, `Fn` | future `design.ewm.compression` | Primary PDF plus independent arithmetic | `Pne = Ag Fn`. |
| Global column curve | E2, p. 43 | Eqs. E2-2 through E2-4 | `Fy`, `Fcre` | future `design.ewm.compression` | Primary PDF plus independent arithmetic | Two branches meet at the verified `lambda_c = 1.5` boundary. |
| E2 LRFD factor | E2, p. 43 | stated factor | `Pne`, `phi_c = 0.85` | future resistance-factor authority | Primary PDF | Factor must be applied once and nominal strength retained separately. |
| Uniformly compressed stiffened element | Appendix 1, 1.1(a), pp. 1-1 to 1-2 | Eqs. 1.1-1 through 1.1-4 | flat width `w`, `t`, `E`, `mu`, plate coefficient `k`, stress `f = Fn` | future `design.ewm.effective_width` | Primary PDF plus independent plate benchmark | Applies to the C-section web under uniform axial compression; the general supported-edge value is `k = 4`. |
| Uniformly compressed unstiffened element | Appendix 1, 1.2.1(a), p. 1-9 | Section 1.1(a) with `k = 0.43` | flat width `w`, `t`, `E`, `mu`, `Fn` | future `design.ewm.effective_width` | Primary PDF plus independent plate benchmark | Applies to each unlipped C flange under uniform axial compression. |
| Uniformly compressed flange with simple lip edge stiffener | Appendix 1, 1.3(a), pp. 1-12 to 1-13 | Eqs. 1.3-1 through 1.3-11 and Table 1.3-1 | flange flat dimension `w`, lip flat depth `d`, lip overall depth `D`, `theta`, `t`, `E`, `Fn`, `Is`, `Ia` | future `design.ewm.effective_width` | Primary PDF plus independent lipped-element benchmark | Produces flange portions `b1`, `b2` and reduced stiffener width `ds`. Current `D1_mm`/`D2_mm` are not declared to be either AISI `d` or `D`. |
| Effective area | E3.1, pp. 44-45 | explanatory requirement following Eq. E3.1-1 | effective width of every component element and `t` | future `design.ewm.effective_area` | Primary PDF plus independent section assembly | S100-24 requires summing thickness times the effective width of each element. An approved reconciliation with M3 gross area is needed. |
| EWM local/global interacting nominal strength | E3.1, p. 44 | Eq. E3.1-1 | `Ae`, `Fn`, `Pne` | future `design.ewm.compression` | Primary PDF plus full benchmark | `Pn-l = Ae Fn`, limited not to exceed `Pne`. |
| E3 LRFD factor | E3, p. 44 | stated factor | `Pn-l`, `phi_c = 0.85` | future resistance-factor authority | Primary PDF | Nominal and LRFD design strengths must remain distinct. |
| Distortional limit state for edge-stiffened C | E4, pp. 46-47 | Eqs. E4-1 through E4-3; stated `phi_c = 0.85` | `Ag`, `Fy`, `Pcrd` | scope decision required before implementation | Primary PDF | E4 expressly applies to C sections with edge-stiffened flanges; its exception does not remove edge-stiffener distortional modes. |
| Elastic distortional force for eligible lipped C | Appendix 2, 2.3.3.1, pp. 2-13 to 2-14 | Eqs. 2.3.3.1-1 through 2.3.3.1-7 and Table 2.3.3-1 | flange-plus-lip properties, out-to-out web depth `ho`, restraint length/stiffness, `E`, `G`, `mu`, `Ag` | scope decision required before implementation | Primary PDF plus independent benchmark | Table 2.3.3-1 explicitly labels its `b`, `d`, and `h` as **mid-line** dimensions. That separate wording is evidence that S100-24 does not use “mid-line,” “flat,” and “out-to-out” interchangeably. |

## Required plate-element interpretation

Subject to final eligibility, the primary PDF establishes these pure axial
classifications for the current shapes:

| Family | Element | S100-24 treatment | Required dimensional meaning |
|---|---|---|---|
| `C_UNLIPPED` | web | uniformly compressed stiffened element, Appendix 1 Section 1.1 | web flat width `w` |
| `C_UNLIPPED` | each flange | uniformly compressed unstiffened element, Appendix 1 Section 1.2.1 | flange flat width `w` |
| `C_LIPPED` | web | uniformly compressed stiffened element, Appendix 1 Section 1.1 | web flat width `w` |
| `C_LIPPED` | each flange plus simple lip | uniformly compressed element with simple lip edge stiffener, Appendix 1 Section 1.3 | flange flat dimension `w`, lip flat depth `d`, lip overall depth `D`, and lip angle `theta` |

For B4.1, the same physical elements require additional table-specific
dimensions. Its notation uses flat web width `w`, flat edge-stiffened element
width `b`, out-to-out edge-stiffened element width `bo`, flat unstiffened
element width `d`, and out-to-out unstiffened element width `do`.

## Stop condition 1: AISI dimensions are unavailable

### Exact missing quantities

At minimum, the approved section geometry does not explicitly supply:

- web flat width;
- each flange flat width;
- for `C_LIPPED`, each lip flat depth;
- for `C_LIPPED`, each lip overall depth `D` used by Appendix 1 Section 1.3;
- for `C_LIPPED`, flange out-to-out width `bo` and lip out-to-out width `do`
  used by Table B4.1-1;
- an approved rule that reconciles AISI element areas based on flat widths with
  the M3 full gross area based on centerline-segment lengths.

### Exact provisions requiring them

- A1.3 definitions, specification p. 5: flat width excludes corners and is
  measured in the element plane.
- B4.1, Table B4.1-1, specification p. 26: method limits use `w`, `b`, `bo`,
  `d`, and `do` with the flat/out-to-out meanings stated in the table notes.
- Appendix 1 Section 1.1, Eqs. 1.1-1 through 1.1-4: the plate reduction begins
  from flat width `w`.
- Appendix 1 Section 1.2.1: the unstiffened-element calculation uses the
  Section 1.1 chain and its flat width.
- Appendix 1 Section 1.3, Eqs. 1.3-1 through 1.3-11 and Table 1.3-1: the
  simple-lip calculation uses flange flat dimension `w`, lip flat depth `d`,
  and overall lip depth `D`.

### Why current `MIDLINE` values are not enough

M3 defines `H_mm`, `B1_mm`, `B2_mm`, `D1_mm`, and `D2_mm` as complete straight
**centerline** segment lengths between ideal sharp intersection vertices. It
does not define tangent points, physical outside faces, free-edge offsets,
corner material, overlap/miter behavior at ideal intersections, or an AISI
flat-width measurement rule.

Although a zero-length mathematical corner may suggest an equality in a
zero-thickness line model, the approved contract never states that its
centerline segments are AISI flat widths. Adopting that equality would be a
new engineering interpretation, not a unit conversion. It would still not
provide the exterior dimensions or the separate Section 1.3 overall lip
depth. Formulas such as subtracting or adding fractions of `t` would invent a
through-thickness corner and free-edge model that M3 deliberately does not
contain.

The distinction is reinforced within S100-24 itself: Appendix 2 Table 2.3.3-1
expressly uses mid-line `b`, `d`, and `h`, while B4.1 and Appendix 1 expressly
call for flat or out-to-out dimensions.

### M8A disposition

M8A adds a separate `AISI_Dimensions` worksheet keyed by `geometry_id`,
`standard_id`, and `standard_edition`; a single `geometry_convention` flag
cannot represent the flat, out-to-out, overall, and mid-line bases required at
the same time. The versioned fields are:

- `web_flat_width_mm`;
- `flange_1_flat_width_mm`, `flange_2_flat_width_mm`;
- `web_out_to_out_depth_mm`;
- `flange_1_out_to_out_width_mm`, `flange_2_out_to_out_width_mm`;
- `lip_1_flat_width_mm`, `lip_2_flat_width_mm`;
- `lip_1_out_to_out_width_mm`, `lip_2_out_to_out_width_mm`;
- `lip_1_overall_depth_mm`, `lip_2_overall_depth_mm`;
- `source_id` and optional notes.

They are not columns on `Geometry`. Section 1.3 `D` and B4.1 `d_o` remain
separate fields and no conversion from `MIDLINE` is implemented. The
production illustrative rows remain absent because no trusted source supplies
the values.

Affected future modules would be the section schema and loader, domain
geometry, M3 geometry translation/verification, M7 B4.1 applicability, M8
plate-element derivation/effective area, the future pyCUFSM adapter, resolved
snapshots, migrations, and validation fixtures.

## Stop condition 2: design-property authority — resolved by M8A

Appendix 2 global compression requires a coherent set of `A`, `Ix`, `Iy`,
`J`, `Cw`, `xo`, and `yo`. M3A/M3B can calculate these quantities, but:

- `ResolvedMember.section.properties` contains the supplied catalog
  `SectionProperties`;
- `ResolvedProject.section_verification_results` preserves comparisons but
  does not preserve the complete M3A/M3B property objects as the member's
  declared design-property source;
- project QA can permit a catalog verification failure with
  `action_on_fail: warning`;
- existing documentation requires catalog and computed values to remain
  separate, but does not select which coherent set governs normative design.

Choosing catalog values for some terms and M3 values for missing terms would
be the arbitrary mixture expressly prohibited by M8. Choosing all M3 values
would also be a new design-authority policy not yet represented in the
resolved domain.

The minimal no-schema proposal is to approve M3A/M3B as the design mechanics
authority and have M5 preserve one immutable computed mechanics bundle per
resolved section, with catalog properties retained only as sourced claims and
QA comparisons. The alternative is to approve catalog properties as the
design authority and make every required global-buckling property and its QA
acceptance mandatory. The owner must select one policy before M8 code.

M8A selects the coherent M3A/M3B computed set as the future design-property
authority. `ResolvedProject.section_mechanics` preserves it with its catalog
verification and `design_use_permitted` gate. Catalog properties remain QA
claims; a design calculation may not mix the two sets.

## Stop condition 3: elastic constants — resolved by M8A

S100-24's symbols and Appendix 2 Section 2.3.1 identify `E = 203,000 MPa` and
`G = 78,000 MPa`; the symbols identify `mu = 0.30`. The current catalog
examples instead contain `E = 200,000 MPa`, `nu = 0.30`, and the domain derives
`G = E/[2(1+nu)]` (approximately `76,923 MPa`). M8 also instructs the future
engine to consume resolved material values.

These are materially different inputs to global and plate buckling. Silently
overriding the catalog would violate its single-source policy; silently using
the catalog would not reproduce the constants printed by the controlling
standard. Deriving `G` from the printed `E` and `mu` also does not exactly
reproduce the separately printed rounded `G`.

Before implementation, the owner must approve whether S100-24 constants are
mandatory normative design constants, whether active catalog entries must be
validated against them, or whether a documented jurisdiction/material rule
permits resolved alternatives. The decision affects the material validation
policy, M8 buckling/effective-width equations, traces, and benchmarks. M8A
centralizes the printed `E`, `G`, and `mu` as immutable normative constants for
the clauses that prescribe them. Material values remain untouched and no
material schema or value was changed.

## M7 scope gate after M8A.1

M8A.1 versions project evidence so forming, load-carrying use, application,
dynamic effects, and governing country are evaluable without assumptions.
Legacy/missing declarations remain indeterminate. The qualifying steel-product
condition remains material-specific and indeterminate pending a separate
material-catalog contract approval.

- material-specific A1.1/A3 qualification;
- B4.1 element dimensions when no explicit production record exists.

Per `DesignEligibility`, M8 can execute only for normative `APPLICABLE` and
software `SUPPORTED`. It cannot replace these remaining facts with assumptions.

## Lipped-C distortional scope decision

S100-24 E1 requires the smallest result from E2 through E4 where applicable.
E4 expressly applies to open C sections with edge-stiffened flanges, and its
exception does not exclude distortional modes involving edge-stiffened
flanges. Therefore, a complete axial design strength for `C_LIPPED` cannot be
reported from E2 plus E3.1 alone.

E4 is not the E3.2 DSM local-buckling route, but its strength equation uses an
elastic distortional buckling result. The M8 scope excludes “distortional DSM
strength” and pyCUFSM without explicitly resolving whether the common E4
limit state belongs in M8. Before future implementation, the owner must
confirm either:

1. M8 includes E4 for `C_LIPPED`, using the permitted analytical Appendix 2
   Section 2.3.3.1 route where its conditions are met; or
2. M8 may calculate only a clearly incomplete E2/E3.1 component result for a
   lipped C and must not label it member design strength.

M8A resolves the choice: a complete future `C_LIPPED` axial EWM member result
must include E4. M8A implements no E4 equation; M8B cannot be declared complete
without the verified E4 route and benchmark.

## Remaining conditions before M8B resistance resumes

1. Populate each production section's schema-0.2 AISI dimensional row from a
   trusted, traceable source; absence must continue blocking execution.
2. Add and approve the material-specific A1.1/A3 qualification contract needed
   for an `APPLICABLE` result.
3. Implement every applicable E2/E3.1/E4 component from the primary source,
   with CalculationTrace coverage and independent benchmarks.

Only after those decisions can the equation-level implementation, trace,
independent benchmark, and `docs/18_EWM_COMPRESSION_VALIDATION_M8.md` be
created without guessing.
