# M9A pyCUFSM Adapter and StructureLab Modal Identification — Unconstrained Classification Research Stop

## Status and frozen architecture

M9A is implemented and regression-tested but currently stopped pending engineering-owner approval. No production adapter is exposed: M9A returns elastic buckling evidence only and does not calculate DSM slenderness, nominal resistance, resistance factors, utilization, or an EWM/DSM comparison. The engineering owner rejected pyCUFSM 0.2.0 constrained cFSM as a design-authoritative LOCAL or DISTORTIONAL source; the authorized continuation investigated an unconstrained-only route:

`M3 geometry -> pyCUFSM unconstrained FSM -> StructureLab classification -> LOCAL/DISTORTIONAL candidates`

Raw unconstrained eigenvalues and eigenvectors reproduced the official CUFSM MATLAB fixtures to floating-point agreement, but the continuation reached a stop condition: for the official lipped-C compression benchmark the lowest unconstrained branch changes continuously from LOCAL to DISTORTIONAL while its eigenvalue increases. The published `Pcrd` point is selected from deformation character rather than an interior minimum of a separable distortional curve. A classifier threshold can select that point, but the selected wavelength moves under mesh refinement, so robust automated classification and minimum extraction are not yet defensible. See `docs/24_ELASTIC_BUCKLING_VALIDATION_M9A.md` for full validation detail.

The v0.1 production path is frozen as:

```text
StructureLab section geometry
    -> M3 authoritative mechanics
    -> deterministic StructureLab FSM mesh
    -> pyCUFSM 0.2.0 unconstrained FSM eigensolver
    -> eigenvalues and eigenvectors (adapter-internal NumPy values)
    -> StructureLab modal decomposition and identification
    -> MAC branch tracking and ambiguity detection
    -> LOCAL / DISTORTIONAL / GLOBAL / MIXED / UNCLASSIFIED
    -> AUTOMATIC_ACCEPTED or ENGINEERING_REVIEW_REQUIRED
    -> immutable StructureLab ElasticBucklingResult
```

`PcrL` and `PcrD` may be exposed only by automatically accepted LOCAL and DISTORTIONAL results. Global compression design buckling remains owned by M8B/AISI E2. A GLOBAL M9A candidate is diagnostic and is never DSM-input eligible.

## Revised unconstrained responsibility boundary

For any future continuation, pyCUFSM may provide only the ordinary unconstrained finite-strip eigenvalues and eigenvectors. It must not activate cFSM constraints. StructureLab would own mode features, classification, confidence, modal tracking, minimum selection, convergence, and provenance. Classification terminology is limited to `LOCAL`, `DISTORTIONAL`, `GLOBAL`, `MIXED`, and `UNCLASSIFIED`; it must not be described as creating restricted modes. GLOBAL design input remains the analytical M8B/E2 result.

The research prototype investigated a transparent C-section feature set:

- a length-weighted rigid-cross-section least-squares residual for GLOBAL;
- web plate bow relative to its displaced end chord for LOCAL behavior;
- flange/lip assembly displacement relative to the web-flange junction and web chord rotation for DISTORTIONAL behavior;
- a nested rigid / C-distortional kinematic projection using cubic-Hermite web bending and rigid flange-lip subassemblies; and
- full-vector MAC for continuity only, never for family assignment.

All ratios are dimensionless and were numerically invariant to eigenvector scale and sign, coordinate translation, and mechanically equivalent x-mirror orientation. These are proposed research features, not accepted production rules. Thresholds separating the families were not validated independently.

The official lipped-C mode at `6.6 in` had assembly-to-web-bow ratio `0.07852` and was visually LOCAL. The official `28.5 in` mode had ratio `0.80127` and was visually DISTORTIONAL. Between them, the ratio changes smoothly: `0.62048` at `23.1 in`, `0.68898` at `24.8 in`, and `0.74954` at `26.6 in`. Selecting the published point therefore requires a classification boundary near `0.8`, not a mechanically separated eigenbranch.

Under twofold and fourfold element subdivision, that same `0.8` boundary moved from `28.5 in` to `27.0 in` and `26.5 in`. This violates the required mesh-stable classification condition. The official unlipped-C fixture labels its short-wave minimum “Local/Distortional”; the prototype ratio `0.34732` correctly exposes ambiguity but does not add a clear independent family benchmark.

Adjacent-wavelength MAC demonstrates why tracking alone cannot resolve the lipped-C transition. The first branch stays at the first eigenvalue and has MAC at least `0.99566` through `20.1–35.1 in` while its physical character changes. Conversely, the sigma diagnostic has first-to-second-mode crossings with MAC `0.86822` and `0.89708`. A future tracker must use assignment plus subspace handling for near-degenerate modes and must terminate uncertain tracks rather than force continuity.

Ten eigenpairs reproduce all ten modes in the official lipped-C saved file. No universal `n_eigs` is justified. In the official unlipped-C sweep, asking the pyCUFSM multi-wavelength wrapper for 8 or more eigenpairs fails when a long-wave station returns only six positive modes; one-wavelength calls retain the available modes without modifying pyCUFSM. A future adapter would need per-wavelength collection and an eigenpair-count convergence rule, neither of which is exposed here.

## Revised global responsibility and normative confirmation

## Final pyCUFSM capability decision

pyCUFSM constrained cFSM is not used in production and no attempt is made to
repair, monkey-patch, or replace it.

| Capability | LOCAL | DISTORTIONAL | GLOBAL |
|---|---|---|---|
| Unconstrained FSM | VALIDATED | VALIDATED | VALIDATED |
| Constrained cFSM `orth=1, norm=1, ospace=ST, couple=1` | NOT_VALIDATED | NOT_VALIDATED | NOT_VALIDATED |
| Constrained cFSM `orth=2, norm=1, ospace=ST, couple=1` | SOFTWARE_BLOCKED | SOFTWARE_BLOCKED | SOFTWARE_BLOCKED |

The `orth=1` comparison uses the identical executable configuration in official
MATLAB CUFSM and pyCUFSM. Its critical-load differences are 17.19 percent
LOCAL, 29.62 percent DISTORTIONAL, and 457.84 percent GLOBAL. These results are
not generalized to `orth=2`.

The pyCUFSM 0.2.0 public `orth=2` path fails in
`cfsm.base_update -> analysis.k_kg_global` because a Python list is supplied to
the compiled argument `m_a`, which requires a NumPy array. The audit also
records active translated defects in `constr_xz_y`, `base_vectors`, and
`mode_class`. Exact evidence is in
`validation/m9a/pycufsm_020_cfsm_capability_audit.json` and an executable test
preserves the public-API failure.

## Dependency and license boundary

The reproducible environment is exactly:

- `pycufsm==0.2.0`, AFL-3.0;
- `numpy==2.2.6`;
- the installed SciPy version captured at run time;
- adapter version `M9A-1`.

All production pyCUFSM imports are confined to
`src/cfs_design/stability/pycufsm_adapter/`. The dependency is external,
unmodified, and not vendored. `THIRD_PARTY_NOTICES.md` records the released
artifact and license. No later upstream license is attributed retroactively to
version 0.2.0.

## M3 ownership and solver translation

The adapter supplies StructureLab-owned `Sect_Props` on every solve:

| StructureLab source | pyCUFSM field | Mapping |
|---|---|---|
| M3A area, centroid, inertias | `A`, `cx`, `cy`, `Ixx`, `Iyy`, `Ixy` | Direct, mm/MPa system |
| M3A principal properties | `phi`, `I11`, `I22` | Angle converted to radians; inertias direct |
| M3A torsion constant | `J` | Direct |
| M3B shear center | `x0`, `y0` | Centroid-relative values converted to absolute mesh coordinates |
| M3B warping constant | `Cw` | Direct and authoritative |
| No approved M3 value | `B1`, `B2`, `wn` | API-neutral `0`, `0`, `None`; unused in the validated axial path |

CUTWP never replaces M3 properties. Its open-section `Cw` result is rejected
for pyCUFSM 0.2.0 because the audited indexing defect can return zero.

## Deterministic mesh and convergence contract

Each straight M3 centerline primitive is divided into
`ceil(length / target_strip_width)` equal strips. Original vertices, contour
order, thickness, and identifiers are retained. Sectorial coordinates at
inserted nodes use exact linear interpolation along each straight thin-wall
segment.

Production-mesh acceptance requires an explicitly finer
`reference_strip_width_mm`. If it is absent, mesh convergence is unavailable
and the candidate requires engineering review. The comparison covers:

- critical stress;
- critical half-wavelength;
- dominant-family agreement;
- mode-shape MAC on shared M3 vertices.

For the official C120 reference, 10 mm is the practical audited mesh and
7.5 mm is the reference mesh. This is a recommendation for that validation
case, not a globally hard-coded mesh. A 20 mm mesh is not approved for
DISTORTIONAL production results. Certain globally finer subdivision patterns
(6, 5, and 2.5 mm in this audit) make the classical basis numerically
rank-deficient; they are explicitly NOT_VALIDATED instead of being presumed
superior merely because they are finer.

## StructureLab classical modal decomposition

The independent implementation is referenced to official CUFSM v5.66
`base_column.m`, `base_update.m`, `mode_class.m`, and `classify.m`:

1. obtain topology-dependent G/D ingredients;
2. form StructureLab global longitudinal vectors from translations, principal
   bending, and M3B warping;
3. form the distortional complement and complete natural G/D/L/O basis;
4. apply the selected other-space, orthogonalization, and normalization rules;
5. solve the direct-sum representation with rank-revealing least squares,
   preserving basis rank, dimension, condition number, and residual;
6. aggregate coefficient Euclidean norms by G, D, L, and O and normalize to
   100 percent;
7. preserve reconstruction residual and basis diagnostics.

The production reference configuration is exactly
`ospace=1, couple=1, orth=2, norm=1`: ST other space, uncoupled `m=1` basis,
axial modal orthogonalization, and Euclidean vector normalization. Other basis
configurations receive `BASIS_CONFIGURATION_NOT_VALIDATED` until separately
validated.

## Tracking and adaptive wavelength search

At adjacent wavelengths, branches are assigned by maximizing total real-vector
MAC over a one-to-one assignment. MAC is sign- and scale-invariant. Branch
identity is independent of solver eigenvalue order; `mode_index` changes are
preserved and generate `BRANCH_TRANSITION` at a critical candidate. Low MAC
generates `MODE_CROSSING`.

The wavelength search:

1. consumes a broad, strictly increasing initial grid;
2. detects interior LOCAL and DISTORTIONAL critical neighborhoods per tracked
   branch;
3. inserts geometric midpoints on both sides of each candidate;
4. repeats nested comparison until stress, location, family, and MAC gates pass
   or the explicit iteration limit is reached;
5. geometrically expands a boundary when an L/D branch is still falling there;
6. stores every added wavelength and boundary-expansion decision in
   `WavelengthSearchEvidence`.

GLOBAL boundary descent does not expand the M9A search because global design
remains M8B-owned.

## Acceptance and engineering review

`M9A_CONSERVATIVE_QA_1` contains transparent software-QA gates, not AISI
coefficients:

- dominant participation at least 90 percent;
- leading-to-runner-up separation at least 50 percentage points;
- neighboring selected-family participation at least 80 percent and change no
  greater than 15 percentage points;
- branch MAC at least 0.90;
- direct-sum residual no greater than `1e-8`;
- mesh stress and wavelength changes no greater than 0.5 and 1.0 percent;
- wavelength-search stress and location changes no greater than 0.5 and
  1.0 percent;
- non-unique minima within 0.5 percent require review.

The thresholds are explicit, preserved in every result, and are not changed by
benchmark identity. Review reasons include no dominant family, L/D interaction,
neighboring-wavelength sensitivity, mode crossing, branch transition,
non-unique minimum, smooth L/D morphing, basis sensitivity, unvalidated basis,
reconstruction failure, mesh sensitivity, incomplete wavelength convergence,
and classical/fcFSM disagreement.

## Result boundary and future engineering selection

`ElasticBucklingResult` preserves the mesh, tracked modes, candidates, accepted and review-required subsets, mesh/wavelength convergence, adaptive-search metadata, solver provenance, validation provenance, QA policy, and `CalculationTrace`. Convenience accessors expose an accepted `local_result`, accepted `distortional_result`, and QA-only `global_diagnostic`.

### Issue #25 corner-topology audit

The exact saved mesh has 45 nodes, 44 elements, 15 cFSM main nodes, 13 corner nodes, 30 subnodes, and 11 available/selected distortional columns. Three of its main-node classifications are artifacts of rounded decimal coordinates on two intended straight diagonal flats: intermediate points miss pyCUFSM's `1e-7 rad` collinearity test.

A controlled `n_r=1`-style variant retained all 45 nodes and 44 elements, but snapped only those intermediate flat nodes onto their endpoint-defined lines. The largest coordinate adjustment was `0.0075` source length units. That produced 12 main nodes, 10 corner nodes, 33 subnodes, and 8 available/selected distortional columns. Its result was `1.0226550814002098` at `49.8`, compared with `1.0226565085710555` at `49.8` for the exact mesh. The A-to-B relative load change was `0.0001396%`, wavelength change was zero, and full-vector modal assurance criterion (MAC) was `0.9999992362`.

Thus the controlled topology change removes the extra cFSM classifications but does not restore or materially improve MATLAB parity. Upstream issue #25 is relevant to mode counting in general, but it is not demonstrated as the cause of this benchmark discrepancy.

At their respective minima, the MATLAB-to-pyCUFSM full-vector MAC was `0.55936`. Comparing at the MATLAB critical wavelength (`65.8`) increased the best MAC only to `0.66968`. Normalized transverse fold-node patterns also differed mechanically: the MATLAB mode was dominated by opposing outer and central fold-line motions, while pyCUFSM's first mode was dominated by one outer return. The mode shapes are not defensibly equivalent.

The fixture is an official solver-level constrained reference, but its sigma section is outside the v0.1 C-section production family. It therefore both fails as a solver benchmark and cannot substitute for the still-missing supported-family benchmark. The difference could not be attributed to corner topology, incomplete modal selection, normalization, or a controlled input transformation. pyCUFSM's constrained solver was added after v0.1.7; the official v0.2.0 tests deliberately disable cFSM when comparing saved MATLAB curves, so no release-level constrained parity evidence resolves the difference. Under the owner's stop conditions, M9A stops here rather than expose provisional results.

`EngineeringSelection` exists only as an immutable future review record. It
requires selected family, wavelength, stress, load, reason, candidate IDs,
explicit engineer confirmation, confirmer identity, and provenance. The M9A
workflow never creates one automatically, and an engineering selection can
never masquerade as `AUTOMATIC_ACCEPTED`.

No raw pyCUFSM or NumPy object escapes the adapter boundary.

## Remaining limitations

- only simply supported uniform axial-reference-stress signature analyses with
  one longitudinal half-wave are production-validated;
- curved corners, holes, springs, non-S-S boundaries, and multiple longitudinal
  terms are unsupported;
- only lipped and unlipped C sections within the approved M3 contract are
  supported;
- mesh patterns whose classical basis loses numerical rank remain unsupported;
- manual DSM Guide selections remain engineering references;
- no DSM resistance equation is implemented.
