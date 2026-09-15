# M9A pyCUFSM Adapter Audit — Unconstrained Classification Research Stop

## Status

M9A is **stopped, not approved**, and no production adapter is exposed. The
engineering owner has rejected pyCUFSM 0.2.0 constrained cFSM as a
design-authoritative LOCAL or DISTORTIONAL source. The 28.54% failed official
MATLAB DISTORTIONAL comparison is preserved below.

The authorized continuation investigated an unconstrained-only route:

`M3 geometry -> pyCUFSM unconstrained FSM -> StructureLab classification -> LOCAL/DISTORTIONAL candidates`

Raw unconstrained eigenvalues and eigenvectors reproduced the official CUFSM
MATLAB fixtures to essentially floating-point agreement. The continuation
nevertheless reached a new stop condition: for the official lipped-C
compression benchmark, the lowest unconstrained branch changes continuously
from LOCAL to DISTORTIONAL while its eigenvalue increases. The published
`Pcrd` point is selected from deformation character, not from an interior
minimum of a separately identifiable distortional curve. A classifier
threshold can select that point, but the selected wavelength changes under
mesh refinement. Robust automated classification and minimum extraction are
therefore not yet defensible. See
`docs/24_ELASTIC_BUCKLING_VALIDATION_M9A.md`.

No production adapter, DSM equation, resistance, resistance factor,
utilization, or EWM/DSM comparison is implemented by this audit.

## Revised unconstrained responsibility boundary

For any future continuation, pyCUFSM may provide only the ordinary
unconstrained finite-strip eigenvalues and eigenvectors. It must not activate
cFSM constraints. StructureLab would own mode features, classification,
confidence, modal tracking, minimum selection, convergence, and provenance.
Classification terminology is limited to `LOCAL`, `DISTORTIONAL`, `GLOBAL`,
`MIXED`, and `UNCLASSIFIED`; it must not be described as creating restricted
modes. GLOBAL design input remains the analytical M8B/E2 result.

The research prototype investigated a transparent C-section feature set:

- a length-weighted rigid-cross-section least-squares residual for GLOBAL;
- web plate bow relative to its displaced end chord for LOCAL behavior;
- flange/lip assembly displacement relative to the web-flange junction and
  web chord rotation for DISTORTIONAL behavior;
- a nested rigid / C-distortional kinematic projection using cubic-Hermite
  web bending and rigid flange-lip subassemblies; and
- full-vector MAC for continuity only, never for family assignment.

All ratios are dimensionless and were numerically invariant to eigenvector
scale and sign, coordinate translation, and mechanically equivalent x-mirror
orientation. These are proposed research features, not accepted production
rules. Thresholds separating the families were not validated independently.

The official lipped-C mode at `6.6 in` had assembly-to-web-bow ratio `0.07852`
and was visually LOCAL. The official `28.5 in` mode had ratio `0.80127` and was
visually DISTORTIONAL. Between them, the ratio changes smoothly: `0.62048` at
`23.1 in`, `0.68898` at `24.8 in`, and `0.74954` at `26.6 in`. Selecting the
published point therefore requires a classification boundary near `0.8`, not
a mechanically separated eigenbranch.

Under twofold and fourfold element subdivision, that same `0.8` boundary
moved from `28.5 in` to `27.0 in` and `26.5 in`. This violates the required
mesh-stable classification condition. The official unlipped-C fixture labels
its short-wave minimum “Local/Distortional”; the prototype ratio `0.34732`
correctly exposes ambiguity but does not add a clear independent family
benchmark.

Adjacent-wavelength MAC demonstrates why tracking alone cannot resolve the
lipped-C transition. The first branch stays at the first eigenvalue and has
MAC at least `0.99566` through `20.1–35.1 in` while its physical character
changes. Conversely, the sigma diagnostic has first-to-second-mode crossings
with MAC `0.86822` and `0.89708`. A future tracker must use assignment plus
subspace handling for near-degenerate modes and must terminate uncertain
tracks rather than force continuity.

Ten eigenpairs reproduce all ten modes in the official lipped-C saved file.
No universal `n_eigs` is justified. In the official unlipped-C sweep, asking
the pyCUFSM multi-wavelength wrapper for 8 or more eigenpairs fails when a
long-wave station returns only six positive modes; one-wavelength calls retain
the available modes without modifying pyCUFSM. A future adapter would need
per-wavelength collection and an eigenpair-count convergence rule, neither of
which is exposed here.

## Revised global responsibility and normative confirmation

Direct review of the verified ANSI/SDI AISI S100-2024 source confirmed the
owner's split of responsibilities:

- E2 determines `Pne` for yielding/global buckling from `Ag`, `Fy`, and
  Appendix 2 global elastic buckling stress `Fcre`;
- E3.2 uses E2 `Pne` together with local elastic buckling force `Pcrℓ` from
  Appendix 2;
- E4 uses yield force `Py = Ag Fy` together with distortional elastic buckling
  force `Pcrd` from Appendix 2; and
- Appendix 2 Section 2.1 permits numerical elastic buckling and defines the
  compression conversion `Pcr = Ag Fcr`.

The exact equation map is recorded in
`docs/25_DSM_COMPRESSION_NORMATIVE_MAP_M9B_PREPARATION.md`. That document is
preparation only; M9B equations are not implemented.

## Dependency and ownership boundary

The audited external solver is `pycufsm==0.2.0` (AFL-3.0). StructureLab M3A
and M3B remain authoritative for section mechanics. Production code must
always pass an adapter-built `sect_props` value to `strip_new`; allowing
`sect_props=None` would make `strip_new` invoke CUTWP and would violate the
approved ownership boundary.

The reproducible NumPy constraint selected by this audit is exactly
`numpy==2.2.6`. The full audited FSM/cFSM path executes with that version.
With NumPy 2.4.3, both CUTWP and the compiled FSM assembly fail because
one-element arrays can no longer be assigned or converted as scalars. No
broader range has been demonstrated, so a broader range is not asserted.

## Deterministic M3 to `Sect_Props` mapping

The following mapping was confirmed against the 0.2.0 API and CUTWP on an
asymmetric lipped C, the same section translated by `(123, -456) mm`, and an
x-mirrored copy. `Sect_Props` is adapter-internal and must never cross the
adapter boundary.

| StructureLab source | pyCUFSM field | Transformation and meaning |
|---|---|---|
| `gross.a_mm2` | `A` | None; thin-wall gross area, mm² |
| `gross.x_bar_mm` | `cx` | None; centroid x-coordinate in mesh coordinates, mm |
| `gross.y_bar_mm` | `cy` | None; centroid y-coordinate in mesh coordinates, mm |
| `gross.ix_mm4` | `Ixx` | None; centroidal x-axis inertia, mm⁴ |
| `gross.iy_mm4` | `Iyy` | None; centroidal y-axis inertia, mm⁴ |
| `gross.ixy_mm4` | `Ixy` | None; both use positive `integral(x y dA)`, mm⁴ |
| `gross.theta_p_deg` | `phi` | Convert degrees to radians; rotation to major principal axis |
| `gross.i1_mm4` | `I11` | None; major principal inertia, mm⁴ |
| `gross.i2_mm4` | `I22` | None; minor principal inertia, mm⁴ |
| `gross.j_mm4` | `J` | None; M3 Saint-Venant torsion constant, mm⁴ |
| `gross.x_bar_mm + advanced.x0_mm` | `x0` | Convert centroid-relative offset to absolute shear-center x-coordinate, mm |
| `gross.y_bar_mm + advanced.y0_mm` | `y0` | Convert centroid-relative offset to absolute shear-center y-coordinate, mm |
| `advanced.cw_mm6` | `Cw` | None; authoritative M3B warping constant, mm⁶ |
| no approved M3 value | `B1` | API-compatible neutral `0.0`; mechanically inactive in audited axial paths |
| no approved M3 value | `B2` | API-compatible neutral `0.0`; mechanically inactive in audited axial paths |
| no approved M3 value | `wn` | API-compatible neutral `None`; mechanically inactive and not fabricated |

For the asymmetric audit section, StructureLab and CUTWP agreed to floating
point precision for `A`, `cx`, `cy`, `Ixx`, `Iyy`, `Ixy`, `phi`, `I11`,
`I22`, `J`, `x0`, and `y0`. The nonzero angle was
`phi = -0.035986593579496705 rad`; mirroring x changed its sign. The
StructureLab absolute shear center was `(-17.6003455676, 5.24305244936) mm`
and translated and mirrored exactly as expected.

### Principal-angle API inconsistency

`pycufsm.solve.cfsm.y_dofs()` uses `cos(phi)` and `sin(phi)` directly, and
CUTWP returns radians. Therefore the constrained M9A path requires radians.
`pycufsm.pre.stresses.stress_gen()` instead multiplies `phi` by `pi/180`.
M9A avoids that inconsistent helper by passing uniform axial nodal stress
explicitly. This decision is limited to the authorized uniform-compression
reference state.

## Actual runtime field use in pyCUFSM 0.2.0

The audit traced `strip_new -> strip -> cFSM` and searched every Python access
to `sect_props` in the installed 0.2.0 release.

| Branch with explicit nodal stress | Fields read by solver path | Fields not read |
|---|---|---|
| Unconstrained FSM | none | all `Sect_Props` fields |
| LOCAL-only cFSM | `A`, `cx`, `cy`, `phi`, `x0`, `y0` | `Ixx`, `Iyy`, `Ixy`, `I11`, `I22`, `J`, `Cw`, `B1`, `B2`, `wn` |
| DISTORTIONAL-only cFSM | `A`, `cx`, `cy`, `phi`, `x0`, `y0` | same inactive fields |
| GLOBAL-only cFSM | `A`, `cx`, `cy`, `phi`, `x0`, `y0` | same inactive fields |

`A`, `cx`, `cy`, `phi`, `x0`, and `y0` are read for every constrained run
because `strip()` builds the complete natural modal basis before selecting a
LOCAL, DISTORTIONAL, or GLOBAL subspace. `J`, `Cw`, `B1`, `B2`, and `wn` are
present in the TypedDict but are not read by this execution path.

### Modal-vector selection correction

The `glob`, `dist`, `local`, and `other` arrays select individual basis
columns. A one-entry value such as `local=[1]` selects only the first local
column; it does not mean “select the complete local class.” Any future adapter
must first obtain the actual mode counts and select every column in the
requested class. Repeating the lipped-C audit with all 318 local columns on the
1.25 mm mesh changed the refined-grid result only slightly, from the previous
single-column value, but this API distinction is mandatory for correctness.

## cFSM internal warping reconstruction

`strip()` calls `cfsm.y_dofs()` whenever any constrained mode is selected.
`y_dofs()`:

1. traverses the element topology from the first element;
2. forms each sectorial increment from node coordinates relative to the
   absolute `x0` and `y0` shear-center coordinates;
3. accumulates an area-weighted mean using element thickness and `A`;
4. obtains the unit warping vector as the mean minus the accumulated raw field;
5. places that vector in the fourth global longitudinal-displacement basis.

This reconstruction is independent of `Sect_Props["Cw"]` and
`Sect_Props["wn"]`. It is also independent of `J`, `B1`, and `B2`.

## CUTWP role and known limitation

CUTWP is secondary QA only. It may compare `A`, centroid, `Ix`, `Iy`, `Ixy`,
principal properties, `J`, and shear-center coordinates for the currently
audited open C sections. It is never called in the production path.

`CUTWP_Cw_status = KNOWN_UNRELIABLE_IN_PYCUFSM_0_2_0`

For the asymmetric lipped-C audit, M3B returned
`Cw = 90,414,212.67855942 mm^6` while CUTWP returned exactly zero. The same
zero was observed for the symmetric lipped-C audit. Inspection identifies an
upstream node-index error in CUTWP's unit-warping loop; pyCUFSM is not patched
or modified. M3B remains authoritative because its independent exact
sectorial-integration benchmarks, translation, mirror, and dimensional-scaling
tests were already approved in M3B.

## Global-basis path and independent-validation stop

The source path creates global and distortional longitudinal-displacement
bases together in `y_dofs()`. In particular, the distortional basis is formed
from null spaces constructed relative to the global columns before modal
selection. Local columns are appended separately in `base_vectors()`, but the
complete natural basis is still assembled before selection. Consequently the
known GLOBAL-only behavior cannot be declared harmless to DISTORTIONAL solely
from code inspection; numerical evidence is required.

The official MATLAB CUFSM repository contains a saved constrained
DISTORTIONAL fixture, `sigma_P_D.mat`. Its stored solution has a minimum load
factor `0.7956149759822446` at `65.8` length units. Running
`pycufsm==0.2.0` with the same material, nodes, elements, wavelengths,
simply-supported condition, and all 11 stored distortional-mode selections
gave `1.0226565085710555` at `49.8` length units. Those differ by 28.54% in
critical load factor and 24.32% in critical wavelength. The maximum absolute
difference over the stored first-mode curve was `28.896166166719595`.

### Issue #25 corner-topology audit

The exact saved mesh has 45 nodes, 44 elements, 15 cFSM main nodes, 13 corner
nodes, 30 subnodes, and 11 available/selected distortional columns. Three of
its main-node classifications are artifacts of rounded decimal coordinates on
two intended straight diagonal flats: intermediate points miss pyCUFSM's
`1e-7 rad` collinearity test.

A controlled `n_r=1`-style variant retained all 45 nodes and 44 elements, but
snapped only those intermediate flat nodes onto their endpoint-defined lines.
The largest coordinate adjustment was `0.0075` source length units. That
produced 12 main nodes, 10 corner nodes, 33 subnodes, and 8 available/selected
distortional columns. Its result was
`1.0226550814002098` at `49.8`, compared with
`1.0226565085710555` at `49.8` for the exact mesh. The A-to-B relative load
change was `0.0001396%`, wavelength change was zero, and full-vector modal
assurance criterion (MAC) was `0.9999992362`.

Thus the controlled topology change removes the extra cFSM classifications
but does not restore or materially improve MATLAB parity. Upstream issue #25
is relevant to mode counting in general, but it is not demonstrated as the
cause of this benchmark discrepancy.

At their respective minima, the MATLAB-to-pyCUFSM full-vector MAC was
`0.55936`. Comparing at the MATLAB critical wavelength (`65.8`) increased the
best MAC only to `0.66968`. Normalized transverse fold-node patterns also
differed mechanically: the MATLAB mode was dominated by opposing outer and
central fold-line motions, while pyCUFSM's first mode was dominated by one
outer return. The mode shapes are not defensibly equivalent.

The fixture is an official solver-level constrained reference, but its sigma
section is outside the v0.1 C-section production family. It therefore both
fails as a solver benchmark and cannot substitute for the still-missing
supported-family benchmark. The difference could not be attributed
to corner topology, incomplete modal selection, normalization, or a controlled
input transformation. pyCUFSM's constrained solver was added after v0.1.7;
the official v0.2.0 tests deliberately disable cFSM when comparing saved
MATLAB curves, so no release-level constrained parity evidence resolves the
difference. Under the owner's stop conditions, M9A stops here rather than
expose provisional results.

The `Sect_Props` dependency audit itself remains closed without fabricating
`B1`, `B2`, or `wn`. No raw pyCUFSM output or provisional elastic value is
exposed.
