# M9A Elastic Buckling Validation — Independent Benchmark Stop Record

## Status and controlled environment

M9A is **stopped, not approved**. The former GLOBAL-only cFSM acceptance
requirement was withdrawn by the engineering owner. Continuation reached the
independent constrained-mode validation gate, where the available official
CUFSM DISTORTIONAL-only fixture did not reproduce. No production adapter is
exposed. Tests in this audit used:

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

Three logarithmic refinement passes bracketed each constrained minimum. All
reported minima were interior to the `10–2000 mm` initial wavelength range.

| Maximum strip width (mm) | Nodes | LOCAL wavelength (mm) | LOCAL Fcr (MPa) | DIST wavelength (mm) | DIST Fcr (MPa) |
|---:|---:|---:|---:|---:|---:|
| 10.0 | 21 | 69.5185 | 116.74997 | 354.7920 | 321.89291 |
| 5.0 | 41 | 67.8926 | 121.50615 | 354.8547 | 321.89293 |
| 2.5 | 81 | 67.0111 | 124.44750 | 354.7293 | 321.89157 |
| 1.25 | 161 | 66.5511 | 126.09175 | 355.4191 | 321.86967 |
| 0.625 | 321 | 66.3325 | 126.96231 | 353.5534 | 321.89847 |
| 0.3125 | 641 | 66.3325 | 127.41103 | not run | not run |

The continuation selected every available constrained basis column rather
than treating a one-entry modal vector as the whole class. For the complete
LOCAL subspace, the stress change from the 0.625 mm to 0.3125 mm mesh was
0.3534%, and the sampled critical wavelength was unchanged. This satisfies
the owner's successive-mesh limits of 0.5% stress and 1.0% wavelength for
that controlled grid. DISTORTIONAL was already well inside both limits.

These values remain exploratory rather than a production configuration. The
0.3125 mm local mesh required 641 nodes and 1,278 local basis columns; even a
13-point focused wavelength grid took approximately two minutes in the audit
environment. The full wavelength-refinement and expanded-interval gates were
not completed after the independent benchmark stop triggered.

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
