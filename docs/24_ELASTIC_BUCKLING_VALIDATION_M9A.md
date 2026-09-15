# M9A Elastic Buckling Validation — Unconstrained Classification Stop Record

## Status and controlled environment

M9A is **stopped, not approved**. The former GLOBAL-only cFSM acceptance
requirement was withdrawn by the engineering owner, and the subsequent failed
official DISTORTIONAL-only fixture caused constrained cFSM to be rejected as a
design-authoritative LOCAL or DISTORTIONAL source. The authorized
unconstrained-FSM continuation reproduced the independent MATLAB solution but
failed the mesh-stable physical-classification and interior-minimum gates. No
production adapter is exposed. Tests in this audit used:

- CPython 3.12.10;
- `pycufsm==0.2.0`, AFL-3.0;
- `numpy==2.2.6`;
- SciPy 1.18.1;
- simply supported strips with one longitudinal half-wave;
- explicit uniform compressive nodal reference stress;
- StructureLab M3A/M3B section properties.

The benchmark was the synthetic sharp-corner lipped channel
`H=100 mm, B1=B2=40 mm, D1=D2=10 mm, t=1 mm`. The deterministic mesh divided
each centerline primitive with `ceil(segment_length / target_size)` equal
segments and preserved the M3 contour order.

## Reference-stress normalization

The same LOCAL and DISTORTIONAL analyses were run with reference stresses of
1 MPa and 10 MPa. Multiplying the returned load factors by their respective
reference stresses produced invariant elastic stresses to floating-point
precision. For example, the LOCAL 50 mm values were
`133.69566117634275 MPa` and `133.69566117636165 MPa`; the DISTORTIONAL 250 mm
values were `394.421651237991 MPa` and `394.4216512379904 MPa`.

This confirms the approved normalization for the audited path:

`Fcr = pyCUFSM load factor * reference stress`.

## `Sect_Props` sensitivity

At half-wavelengths `10, 50, 100, 250, 1000, 2500, 5000, 10000 mm`, the
complete LOCAL-only and DISTORTIONAL-only curves were bit-for-bit unchanged
under these controlled substitutions:

| Field | Baseline | Variants | Maximum observed curve difference |
|---|---:|---:|---:|
| `Cw` | M3B `Cw` | `0`, `10 * M3B_Cw` | `0 MPa` |
| `J` | M3 `J` | `0`, `10 * M3_J` | `0 MPa` |
| `B1` | neutral `0` | `1e9` | `0 MPa` |
| `B2` | neutral `0` | `-1e9` | `0 MPa` |
| `wn` | neutral `None`/empty | every node set to `1e9` | `0 MPa` |

The numerical result agrees with the source audit: none of these fields is
read in the approved constrained axial path. The test values are sensitivity
probes, not proposed section properties.

## Mesh and wavelength behavior

The earlier exploratory sweep used one selected basis column and three
logarithmic wavelength-refinement passes. It is retained as historical
diagnostic evidence only; it is not an acceptance table because a one-entry
modal vector does not select the complete constrained class.

| Maximum strip width (mm) | Nodes | LOCAL wavelength (mm) | LOCAL Fcr (MPa) | DIST wavelength (mm) | DIST Fcr (MPa) |
|---:|---:|---:|---:|---:|---:|
| 10.0 | 21 | 69.5185 | 116.74997 | 354.7920 | 321.89291 |
| 5.0 | 41 | 67.8926 | 121.50615 | 354.8547 | 321.89293 |
| 2.5 | 81 | 67.0111 | 124.44750 | 354.7293 | 321.89157 |
| 1.25 | 161 | 66.5511 | 126.09175 | 355.4191 | 321.86967 |

The continuation then selected every available LOCAL basis column and used a
fixed 13-point focused wavelength grid from 55 to 80 mm. These are the
acceptance-grade successive-mesh observations from that controlled grid:

| Maximum strip width (mm) | Nodes | Elements | Selected LOCAL columns | LOCAL wavelength (mm) | LOCAL Fcr (MPa) |
|---:|---:|---:|---:|---:|---:|
| 5.0 | 41 | 40 | 78 | 68.4609684 | 121.5170199 |
| 2.5 | 81 | 80 | 158 | 68.4609684 | 124.5210940 |
| 1.25 | 161 | 160 | 318 | 68.4609684 | 126.2218852 |
| 0.625 | 321 | 320 | 638 | 66.3324958 | 126.9623131 |
| 0.3125 | 641 | 640 | 1,278 | 66.3324958 | 127.4110342 |

From 1.25 mm to 0.625 mm, the stress changed by approximately 0.5866%, so
that pair did not satisfy the owner's 0.5% limit. From 0.625 mm to 0.3125 mm,
the stress changed by 0.3534% and the sampled wavelength did not change,
satisfying the 0.5% stress and 1.0% wavelength successive-mesh limits on this
focused grid. Treating 0.3125 mm as the reference, the 0.625 mm stress error
is approximately 0.3522%.

The 0.3125 mm mesh is the defensible reference-mesh candidate for this
synthetic LOCAL study. It has 641 nodes, 640 elements, 2,564 strip degrees of
freedom, and 1,278 selected LOCAL columns. The combined 0.625 mm and 0.3125 mm
13-point run took about 121 seconds in the audit environment; the 0.3125 mm
case accounted for more than 90 seconds and is reasonably characterized as a
roughly 1.5-to-2-minute reference run. Dense core matrices and the selected
basis require more than 200 MB before eigensolver workspace, so peak use is
on the order of a few hundred MB. The 0.625 mm mesh is a practical-default
candidate, but adopting it requires owner approval and does not relax the
acceptance threshold.

Complete-subspace DISTORTIONAL focused-grid checks remained stable through
0.625 mm (`321.900285`, `321.901907`, `321.918575`, and `321.898468 MPa` for
5.0, 2.5, 1.25, and 0.625 mm respectively, with the finest sampled critical
wavelength `353.5534 mm`). The full expanded-interval and wavelength-
refinement gates were not completed after the independent parity stop
triggered. All mesh results remain audit evidence, not production settings.

## Revised unconstrained-FSM benchmark

The revised route used the official `cwlip_P.mat` CUFSM MATLAB result for the
9CS2.5x059 lipped C in uniform compression. This is an in-scope section family
and contains the material, 37-node/36-strip model, 99 half-wavelengths, ten
eigenvalue curves, and ten saved eigenvectors per wavelength. The official
CUFSM repository commit was
`d16e28195d3963ee218be0768e19159b0777fdee`; the fixture SHA-256 was
`05d358291246e1d958ecb96084bf4a4963d28be1e0729a4f98f7b960d4692577`.
The accompanying DSM Guide identifies the following compression results from
the unconstrained curve and displayed deformation shapes:

| Family | CUFSM MATLAB half-wavelength (in) | MATLAB load factor | MATLAB Fcr (ksi) | pyCUFSM load factor | pyCUFSM Fcr (ksi) | Relative load error |
|---|---:|---:|---:|---:|---:|---:|
| LOCAL | 6.6 | 0.124235045625 | 6.832933739 | 0.124235045503 | 6.832933732 | 0.0000000982% |
| DISTORTIONAL | 28.5 | 0.269814119381 | 14.839790095 | 0.269814115534 | 14.839789884 | 0.000001426% |

The reference nodal stress is `55.000050143 ksi`; Fcr is the load factor times
that explicit stress. The geometry-integrated thin-wall area is
`0.8804301064 in^2`. No design-facing Pcr is emitted because the classifier
gate failed; a future accepted path would use authoritative M3 `Ag` and
`Pcr = Ag Fcr`.

With ten retained eigenpairs, the maximum absolute discrepancy across the
complete ten-mode saved lipped-C curve was `7.91044e-5` in load factor; for
the first curve it was `4.41093e-7`. MATLAB-to-pyCUFSM eigenvector MAC was at
least `0.9999999786`. The official sigma fixture independently produced
first-curve maximum absolute error `1.85698e-7` and minimum first-mode MAC
`0.9999999981`, but the sigma geometry is outside the v0.1 production family
and is diagnostic only.

These results validate the ordinary pyCUFSM 0.2.0 finite-strip eigen-solution
against MATLAB. They do not validate automated family extraction.

## Physical-feature classifier research

The research prototype used only unconstrained eigenvectors and M3-style
cross-section topology. It did not activate or reconstruct a constrained cFSM
solution. The transparent dimensionless features were:

1. length-weighted residual from a best-fit rigid cross-section translation
   and rotation;
2. web bow relative to the displaced chord between web-flange junctions;
3. flange/lip assembly displacement relative to its web junction after
   removing web-chord rotation; and
4. participation in a nested kinematic model with a cubic-Hermite bending web
   and rigid flange-lip subassemblies.

The candidate `assembly_to_web_bow` ratio is invariant to displacement scale
and sign. Coordinate translation and mirrored geometry/displacement produced
the same value to the displayed precision. All projection fractions were also
unchanged to approximately `1e-15`.

At the official LOCAL point (`6.6 in`), the projection fractions were
`GLOBAL=0.417862`, `DISTORTIONAL=0.346290`, `LOCAL=0.235849`, while the
assembly-to-web-bow ratio was `0.078523`. At the official DISTORTIONAL point
(`28.5 in`), they were `0.436285`, `0.555682`, `0.008033`, with ratio
`0.801272`. A GLOBAL example at `200.9 in` had rigid fraction `0.999933`.

The direct projection alone would incorrectly make GLOBAL the largest
component at the visually LOCAL point, so it cannot be an accepted classifier.
The assembly/web ratio separates the two labeled examples, but its transition
is continuous rather than categorical:

| Half-wavelength (in) | Load factor | Assembly/web ratio |
|---:|---:|---:|
| 21.5 | 0.255729005 | 0.546249 |
| 23.1 | 0.259139545 | 0.620477 |
| 24.8 | 0.262025672 | 0.688981 |
| 26.6 | 0.265315853 | 0.749540 |
| 28.5 | 0.269814119 | 0.801272 |
| 30.5 | 0.276128759 | 0.844315 |

A switch threshold of `0.6`, `0.7`, or `0.8` selects a different first
DISTORTIONAL point. Relative to the official 28.5-in value, representative
earlier selections differ by 3.956% at 23.1 in, 2.887% at 24.8 in, and 1.667%
at 26.6 in. Choosing `0.8` reproduces the reference because it was calibrated
to it, not because a separate mathematical minimum exists. This is not an
independent validation.

The official guide expressly notes that the compression distortional mode is
not readily apparent and identifies the local-to-distortional transition by
examining the deformation shape. The saved lowest eigenvalue rises
monotonically from 20 to 36 in. Therefore the 28.5-in design value is not an
interior minimum of a curve consisting only of confidently classified
DISTORTIONAL points. It is a judgment at a smooth modal transition.

## Tracking, eigenpair count, and crossing behavior

Full-vector MAC was evaluated as
`|a^T b|^2 / ((a^T a)(b^T b))`. It is invariant to sign and magnitude and was
used only for continuity. Through the lipped-C transition from 20.1 to
35.1 in, adjacent first-mode MAC never fell below `0.99566` and the best match
remained eigenvalue 1. MAC therefore tracks one continuous branch but cannot
decide where its family changes.

The sigma diagnostic contains actual ordering changes: the first mode best
matches the next wavelength's second mode at 12.3-to-13.2 in (`MAC=0.86822`)
and 14.2-to-15.2 in (`MAC=0.89708`). A deterministic Hungarian maximum-MAC
assignment detects both. Values below a validated continuity threshold, and
near-degenerate clusters, would require subspace tracking and an ambiguous
status. No threshold strategy has yet been independently validated, so no
production tracker is implemented.

The official lipped-C file retains ten eigenpairs, and pyCUFSM reproduced all
ten. Candidate values at the labeled points are unchanged when fewer pairs are
requested, but that does not establish a universal count. For the official
unlipped C, the multi-wavelength wrapper succeeds through six requested pairs
and fails for 8, 9, 10, or 12 because its longest wavelength returns only six
positive modes while other wavelengths return more. One-wavelength calls can
retain the available modes without patching pyCUFSM. Any future route must
collect per wavelength and increase the requested count until both family
candidates and their neighboring tracks are stable. M9A has not established a
universal `n_eigs`.

## Revised mesh and wavelength sensitivity

The official lipped-C mesh was subdivided without changing its piecewise-
linear contour. At the fixed reference wavelengths:

| Subdivision | Nodes | LOCAL factor at 6.6 in | DIST factor at 28.5 in | 10-wavelength, 6-mode runtime |
|---:|---:|---:|---:|---:|
| 1x | 37 | 0.124235045503 | 0.269814115534 | 0.18 s |
| 2x | 73 | 0.124105859825 | 0.269578287925 | 0.71 s |
| 4x | 145 | 0.124090433214 | 0.269533144941 | 5.75 s |

The 2x-to-4x changes are `0.01243%` LOCAL and `0.01675%` DISTORTIONAL. A
0.1-in local search put the minimum at `6.7 in` for all three meshes and
remained interior. The corresponding factors were `0.1242156942`,
`0.1240862238`, and `0.1240708933`.

Classification did not remain stable. With the prototype ratio threshold
chosen to recover the official 28.5-in DISTORTIONAL point, the first accepted
point moved from `28.5 in` at 1x to `27.0 in` at 2x and `26.5 in` at 4x. The
underlying 20-to-36-in curve was strictly increasing at every mesh. Thus mesh
refinement changes the classified boundary even though the eigenvalues are
well converged.

For a 54-wavelength, two-eigenpair research sweep, runtimes were `0.94 s`,
`4.03 s`, and `31.43 s` for 37, 73, and 145 nodes. This steep dense-solver
growth reinforces the need for a geometry-relative production mesh, but a
production rule was not selected. The prior `0.3125 mm` reference and
`0.625 mm` practical candidates remain evidence for the earlier synthetic
section only and must not be hard-coded universally.

## Revised M9A stop conclusion

The unconstrained solver itself passes the independent MATLAB numerical gate.
The automated classification/minimum-extraction architecture does not:

- the reference distortional value lies on a smooth, monotonically rising
  transition rather than at an interior family-curve minimum;
- matching it requires an arbitrary shape threshold calibrated to the answer;
- the calibrated classification boundary moves under mesh refinement;
- MAC confirms continuous modal evolution and cannot supply the family split;
- the unlipped-C official example is deliberately local/distortional
  ambiguous; and
- no second clear, independent in-scope benchmark exists in the identified
  official fixture set to validate thresholds.

These facts trigger the owner-defined stop conditions for non-robust physical
classification, mesh-dependent classification, lack of an interior stable
DISTORTIONAL minimum, and reliance on an arbitrary threshold. No classifier,
adapter, dependency, result model, or DSM calculation is promoted to
production.

## Independent constrained-mode benchmark failure

The highest-available independent source found was the official MATLAB CUFSM
repository maintained by the original CUFSM project. Its saved
`sigma_P_D.mat` result is a DISTORTIONAL-only cFSM analysis created in MATLAB
and contains the input mesh, material, wavelengths, mode selections, and
expected curve. The audit used official CUFSM repository commit
`d16e28195d3963ee218be0768e19159b0777fdee`; the fixture SHA-256 was
`15aefa13deb4ac062e02d09b1a06b557cc762b69d679f90bca99383c2b4dc9a4`.
The pyCUFSM release tag was commit
`0c45defae65eaa3de99ad8f40f8a9610e7c30f08` (`v0.2.0`).

The stored first-mode curve has its minimum load factor at:

- half-wavelength: `65.8` source length units;
- load factor: `0.7956149759822446`.

With `pycufsm==0.2.0`, the same saved material, nodes, elements, wavelengths,
simply-supported boundary condition, and all 11 distortional selections gave:

- half-wavelength: `49.8` source length units;
- load factor: `1.0226565085710555`.

The critical load factor differs by 28.54% and the critical wavelength by
24.32%; the maximum absolute first-mode curve difference is
`28.896166166719595`. This is not an acceptable numerical tolerance. The
fixture's sigma section is also outside the supported v0.1 C-section family,
so it cannot replace a supported-family fixture even if it passed.

### Controlled issue #25 topology comparison

| Quantity | A: exact saved mesh | B: straight-flat `n_r=1` topology |
|---|---:|---:|
| Nodes | 45 | 45 |
| Elements | 44 | 44 |
| cFSM main nodes | 15 | 12 |
| cFSM corner nodes | 13 | 10 |
| cFSM subnodes | 30 | 33 |
| Available distortional columns | 11 | 8 |
| Selected distortional columns | 11 | 8 |
| Critical half-wavelength | 49.8 | 49.8 |
| Critical load factor | 1.0226565085710555 | 1.0226550814002098 |

Variant B changes only the rounded intermediate coordinates of two intended
straight diagonal flats so they lie exactly on their endpoint-defined lines;
the largest movement is `0.0075` source length units. Relative A-to-B load
change is `1.39555e-6` (0.0001396%), wavelength change is zero, and the
critical-mode full-vector MAC is `0.9999992362`. The topology change therefore
removes three spurious main/corner classifications and three distortional
columns without materially changing the pyCUFSM solution.

Against MATLAB, variant B still has 28.5364% critical-load error and 24.3161%
critical-wavelength error. The MATLAB-to-pyCUFSM MAC is `0.55925` at the two
respective minima and only `0.66959` when compared at the common 65.8
wavelength. The normalized transverse patterns show a different dominant
deformation region. The modes are not mechanically equivalent enough to
support acceptance.

This controlled result does not support issue #25 as the cause. Modal
selection was complete in each topology (11/11 and 8/8 columns), and the saved
normalization, natural-basis, uncoupled, ST-space configuration was preserved.
The remaining candidates are a constrained-solver implementation difference
or a MATLAB/pyCUFSM version difference that the available v0.2.0 validation
suite does not resolve. Resolving it would require work outside this audit's
approved boundary or modifying the external solver.

The official pyCUFSM v0.2.0 test suite contains MATLAB CUFSM signature-curve
fixtures, including a lipped-C compression example, but its test helper
explicitly turns off every cFSM class before comparing curves. It therefore
supports unconstrained solver QA only and does not provide the independently
verified constrained LOCAL and DISTORTIONAL results required here.

No independent constrained LOCAL reference was established before this stop.
The acceptance conditions say to stop if an independent local or
distortional benchmark fails; production implementation therefore did not
begin.

## Global solver QA and retained GLOBAL-only limitation

The independent M8B analytical calculation for equal effective lengths of
2500 mm gives:

- `Fcre = 60.736047377025045 MPa`;
- governing analytical mode: flexural-torsional.

At the same 2500 mm half-wavelength, unconstrained FSM converged toward the
same result:

| Maximum strip width (mm) | Unconstrained FSM Fcr (MPa) |
|---:|---:|
| 10.0 | 60.78841 |
| 5.0 | 60.68065 |
| 2.5 | 60.65371 |

The 2.5 mm result differs from M8B by approximately 0.136%, establishing that
the mesh, material constants, loading sign, and load-factor normalization can
represent the mechanically equivalent global response.

GLOBAL-only cFSM does not reproduce it:

| Maximum strip width (mm) | GLOBAL-only cFSM Fcr at 2500 mm (MPa) |
|---:|---:|
| 10.0 | 545.49873 |
| 5.0 | 545.49928 |
| 2.5 | 545.49985 |

The discrepancy is approximately 798% and is mesh-stable. Selecting the four
global basis vectors one at a time showed that one component produces no valid
positive eigenvalue at the long wavelengths; pyCUFSM then fails while packing
the empty result. Supplying CUTWP-generated properties produced the identical
GLOBAL curve, so this is not caused by the StructureLab `Sect_Props` mapping
or by M3B `Cw`.

The engineering owner subsequently assigned design-authoritative global
buckling to StructureLab's existing analytical E2/M8B path. The agreeing
unconstrained long-wave value remains solver-health evidence for geometry,
thickness, elastic constants, compression sign, normalization, and global FSM
mechanics. GLOBAL-only constrained cFSM remains a documented third-party
diagnostic limitation and must never be used as the future DSM `Pcre` input.

Selecting all four requested global columns rather than a one-entry vector did
not alter the audited 2.5 mm result (`545.49980 MPa`), because the additional
columns did not supply a lower valid positive eigenvalue. The failed
experiment is therefore preserved, but it is no longer an M9A blocker by
itself.

The source-path review also found that `y_dofs()` constructs distortional
columns through null spaces relative to the global columns before the later
mode selection. That dependency means the global behavior cannot be assumed
irrelevant to the DISTORTIONAL subspace. The failed official constrained
DISTORTIONAL comparison prevents a numerical non-contamination conclusion.

## NumPy compatibility result

The exact `numpy==2.2.6` environment executes CUTWP, unconstrained FSM, and the
LOCAL/DISTORTIONAL/GLOBAL cFSM calls described above. Repeating with NumPy
2.4.3 and the same pyCUFSM/SciPy versions fails in:

- CUTWP, when a one-element `np.diff` array is assigned to a scalar; and
- compiled FSM assembly, when a one-element `argwhere` array is converted to
  `int`.

The selected reproducible constraint is therefore `numpy==2.2.6`; no broader
compatible interval is claimed without evidence.

## Controlled project text normalization

`projects/PRJ_001/project.yaml` underwent an explicitly authorized
`CONTROLLED_TEXT_NORMALIZATION`, not an `INPUT_CONTRACT_CHANGE`.

- old working-tree SHA-256:
  `b4e094554d70d5b2dd7421af14a3592fc583f2c82a0a99ba1e68938beed591f2`;
- canonical approved SHA-256:
  `a2e13a538d086e1048035d8b47b4f6d53f6d3d41196d6a98ff431aac36c94d42`;
- reason: CRLF to LF only.

Before/after verification confirmed identical UTF-8 text after newline
normalization, 112 lines in each representation, equal parsed YAML objects and
top-level key order, identical indentation signatures, and a byte delta
consisting only of replacing 112 CRLF pairs with LF. Reconstructing CRLF from
the canonical bytes reproduced the old SHA exactly. The existing expected
fingerprint test was not changed. `.gitattributes` now contains only the
additional explicit rule
`projects/PRJ_001/project.yaml text eol=lf` for this protected text artifact.

After normalization and before further M9A audit work, the complete suite
passed: `556 passed in 22.81s`.

## Acceptance checklist at stop

- [x] Proposed `Sect_Props` mapping is deterministic from M3A/M3B.
- [x] M3B is the authoritative `Cw`; CUTWP `Cw` is rejected.
- [x] Actual field use and internal warping reconstruction are audited.
- [x] `Cw`, `J`, `B1`, `B2`, and `wn` sensitivities are understood.
- [x] Absolute shear-center and principal-axis mappings are verified.
- [x] Exact NumPy compatibility environment is reproducible.
- [x] Reference-stress normalization is verified at two levels.
- [x] LOCAL successive-mesh criterion met on the controlled focused grid.
- [x] DISTORTIONAL successive-mesh criterion met on the controlled focused grid.
- [ ] Expanded-interval wavelength convergence is approved.
- [ ] Independent constrained LOCAL benchmark passes.
- [ ] Independent constrained DISTORTIONAL benchmark passes — **STOP**.
- [x] Unconstrained long-wave global QA agrees with M8B within about 0.136%.
- [x] GLOBAL-only cFSM limitation retained as diagnostic, not design input.
- [ ] `ElasticBucklingResult` is exposed — intentionally not implemented.

M9B remains deferred.
