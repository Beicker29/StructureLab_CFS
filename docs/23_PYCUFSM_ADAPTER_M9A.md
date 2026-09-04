# M9A pyCUFSM Adapter and StructureLab Modal Identification

## Status and frozen architecture

M9A is implemented and regression-tested and awaits engineering-owner approval.
M9B has not started. M9A returns elastic buckling evidence only; it does not
calculate DSM slenderness, nominal resistance, resistance factors, utilization,
or an EWM/DSM comparison.

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

`PcrL` and `PcrD` may be exposed only by automatically accepted LOCAL and
DISTORTIONAL results. Global compression design buckling remains owned by
M8B/AISI E2. A GLOBAL M9A candidate is diagnostic and is never DSM-input
eligible.

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

`ElasticBucklingResult` preserves the mesh, tracked modes, candidates, accepted
and review-required subsets, mesh/wavelength convergence, adaptive-search
metadata, solver provenance, validation provenance, QA policy, and
`CalculationTrace`. Convenience accessors expose an accepted `local_result`,
accepted `distortional_result`, and QA-only `global_diagnostic`.

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
