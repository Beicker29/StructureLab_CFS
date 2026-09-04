# M9A Elastic Buckling Validation — Stop Record

## Status and controlled environment

M9A is **stopped, not approved**. Tests in this audit used:

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

DISTORTIONAL convergence is stable. LOCAL convergence was still changing by
about 1.32% from the 2.5 mm to 1.25 mm meshes; because the GLOBAL gate failed
first, no production tolerance or final mesh was approved from these
exploratory values.

## Mandatory global QA failure

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

This is the owner's explicit stop condition “global QA fails.” A wavelength
heuristic, the agreeing unconstrained curve, or a different modal label cannot
be substituted for the required explicit constrained GLOBAL basis.

## NumPy compatibility result

The exact `numpy==2.2.6` environment executes CUTWP, unconstrained FSM, and the
LOCAL/DISTORTIONAL/GLOBAL cFSM calls described above. Repeating with NumPy
2.4.3 and the same pyCUFSM/SciPy versions fails in:

- CUTWP, when a one-element `np.diff` array is assigned to a scalar; and
- compiled FSM assembly, when a one-element `argwhere` array is converted to
  `int`.

The selected reproducible constraint is therefore `numpy==2.2.6`; no broader
compatible interval is claimed without evidence.

## Acceptance checklist at stop

- [x] Proposed `Sect_Props` mapping is deterministic from M3A/M3B.
- [x] M3B is the authoritative `Cw`; CUTWP `Cw` is rejected.
- [x] Actual field use and internal warping reconstruction are audited.
- [x] `Cw`, `J`, `B1`, `B2`, and `wn` sensitivities are understood.
- [x] Absolute shear-center and principal-axis mappings are verified.
- [x] Exact NumPy compatibility environment is reproducible.
- [x] Reference-stress normalization is verified at two levels.
- [ ] LOCAL mesh convergence is approved.
- [x] DISTORTIONAL mesh and wavelength behavior is stable in the audit.
- [ ] GLOBAL cFSM QA passes — **mandatory blocker**.
- [ ] `ElasticBucklingResult` is exposed — intentionally not implemented.

M9B remains deferred.
