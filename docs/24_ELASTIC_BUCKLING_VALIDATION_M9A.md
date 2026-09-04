# M9A Elastic Buckling and Modal Identification Validation

## Reference provenance

The independent references use official CUFSM v5.66 source. The pristine
downloaded archive SHA-256 is
`e43d66ccc5b024ea40ba48c369f88b92c60fb7f0e11c6ce8e06b06f6b62b9104`.

Reference families remain separate:

- `CLASSICAL_CFSM_REFERENCE`: `classify.m`, `base_column.m`, `base_update.m`,
  `mode_class.m`, and official unconstrained `stripmain.m`;
- `FCFSM_REFERENCE`: `stripmain_fcFSM.m`, `SecAnal_fcFSM.m`, and their official
  basis dependencies.

A licensed MATLAB runtime was unavailable, so official `.m` source was
executed with GNU Octave 4.4.1. The original archive remained unchanged. In a
temporary extracted execution tree only, the MATLAB
`eigs(...,'SM','Display',0)` spelling in `stripmain.m` and
`stripmain_fcFSM.m` was replaced by Octave's equivalent options structure with
`disp=0`. Matrices, eigensolver target, mode count, and formulation were not
changed. Pristine and temporary hashes plus exact substitutions are in
`validation/m9a/official_cufsm_v566_source_manifest.json`. No shim is production
code and no pyCUFSM source was modified.

## pyCUFSM capability matrix

| Capability | LOCAL | DISTORTIONAL | GLOBAL |
|---|---|---|---|
| Unconstrained FSM | VALIDATED | VALIDATED | VALIDATED |
| Constrained cFSM `orth=1` | NOT_VALIDATED | NOT_VALIDATED | NOT_VALIDATED |
| Constrained cFSM `orth=2` | SOFTWARE_BLOCKED | SOFTWARE_BLOCKED | SOFTWARE_BLOCKED |

For executable `orth=1, norm=1, ospace=ST, couple=1`, the identical MATLAB
comparison produced critical-load differences of 17.1903, 29.6198, and
457.8378 percent for LOCAL, DISTORTIONAL, and GLOBAL. The `orth=2` public path
stops on the list-to-NumPy-array API defect before any family result exists.
`orth=1` is additional evidence only and is not generalized to `orth=2`.

## Unconstrained solver parity

Official example `C_120X80X15X1` uses E=210000 MPa, nu=0.3, t=1 mm,
17 nodes, S-S ends, and uniform 1 MPa reference compression.

| Half-wavelength (mm) | Official CUFSM | StructureLab/pyCUFSM | Relative difference |
|---:|---:|---:|---:|
| 20.0000 | 503.4277613994 | 503.4277613990 | -6.87e-13 |
| 70.2501 | 78.0960708393 | 78.0960708455 | 7.88e-11 |
| 257.6785 | 148.3672912553 | 148.3672912635 | 5.57e-11 |
| 945.1687 | 127.3320265898 | 127.3320276238 | 8.12e-9 |
| 3466.8942 | 58.0666018789 | 58.0665989270 | -5.08e-8 |
| 10240.0000 | 9.1275146357 | 9.1275139485 | -7.53e-8 |

The maximum absolute relative difference is `7.53e-8`. After the documented
reverse-contour mapping, mode-shape MAC at all six points exceeds
`0.99999999999998`. This validates eigenvalues and eigenvectors without using
pyCUFSM constrained cFSM.

## Classical automatic classification

All classical results use `ospace=1, couple=1, orth=2, norm=1`. Percentages are
G/D/L/O. Direct-sum residuals are below `1e-12`.

### Official C120x80x15x1

| Wavelength (mm) | Official MATLAB G/D/L/O (%) | StructureLab G/D/L/O (%) | Max. difference (pp) |
|---:|---|---|---:|
| 20.0000 | 0.300905 / 0.019248 / 99.385191 / 0.294657 | 0.300903 / 0.019248 / 99.385107 / 0.294789 | 0.000132 |
| 70.2501 | 0.110117 / 0.209182 / 99.593349 / 0.087352 | 0.110115 / 0.209181 / 99.592792 / 0.087912 | 0.000560 |
| 257.6785 | 0.495704 / 13.629044 / 85.759867 / 0.115385 | 0.495701 / 13.629019 / 85.759720 / 0.115561 | 0.000147 |
| 945.1687 | 1.391543 / 95.621653 / 2.961632 / 0.025173 | 1.391541 / 95.621843 / 2.961638 / 0.024977 | 0.000196 |
| 3466.8942 | 98.531206 / 1.424258 / 0.035928 / 0.008608 | 98.531178 / 1.424256 / 0.035929 / 0.008636 | 0.000029 |
| 10240.0000 | 99.987594 / 0.010716 / 0.000713 / 0.000977 | 99.987598 / 0.010715 / 0.000714 / 0.000973 | 0.000013 |

Dominant family agrees at every point. The 257.6785 mm point is automatically
recognized as L/D interaction rather than forced into an accepted family.

### Additional supported sharp-corner cases

Official CUFSM functions were also run independently for sharp
`C100x40x10x1` and sharp unlipped `C100x40x1` inputs. Six wavelengths per case
cover LOCAL, DISTORTIONAL where applicable, GLOBAL, and L/D transition regions.

| Case | Points | Max. load-factor relative difference | Max. participation difference | Minimum MAC | Dominant-family agreement |
|---|---:|---:|---:|---:|---|
| C100x40x10x1 | 6 | 8.46e-8 | 0.009846 pp | 0.99999999999997 | all points |
| C100x40x1 | 6 | 7.57e-8 | 0.000070 pp | 0.99999999999979 | all points |

The automatic MATLAB percentages, StructureLab percentages, MAC values, exact
basis options, normalization, orthogonalization, and other-space definition are
preserved in
`validation/m9a/official_cufsm_v566_classical_additional.json`. No manual DSM
Guide label is an automatic target.

Translation by `(137,-419) mm`, x-mirroring, eigenvector sign reversal, and
nonzero scaling preserve the validated results within recorded floating-point
tolerances.

## Official fcFSM validation

The full 145-wavelength official C120 fcFSM curves and shapes were generated,
not merely six selected probes. StructureLab values below are the validated
unconstrained curve interpreted by the owned classifier; official `curveL`,
`curveD`, and `curveG` remain validation references and are never substituted
into production.

| Family | Official fcFSM LF @ wavelength | StructureLab LF @ wavelength | LF difference | Critical-region max. | MAC | Decision |
|---|---:|---:|---:|---:|---:|---|
| LOCAL | 68.75529 @ 99.3486 mm | 68.66906 @ 99.3486 mm | -0.1254% | 0.1754% | 0.999967 | VALIDATED |
| DISTORTIONAL | 126.89119 @ 829.9773 mm | 123.46517 @ 829.9773 mm | -2.7000% | 3.1716% | 0.998201 | PARTIALLY_VALIDATED |
| GLOBAL | 9.127757 @ 10240 mm | 9.127514 @ 10240 mm | -0.0027% | 0.0049% | 1.000000 | VALIDATED, QA only |

The DISTORTIONAL difference is investigated rather than hidden. Official
fcFSM `curveD` is a force-based constrained-family eigenproblem; StructureLab
identifies the D minimum on the independently validated unconstrained curve.
The family, critical wavelength, curve neighborhood, and mode shape agree, and
the 2.70 percent difference lies in the required 2-5 percent documented band.
No constrained fcFSM value enters production.

At 257.6785 mm, official fcFSM reports 93.3405 percent LOCAL while classical
CUFSM reports 85.7599 percent LOCAL and 13.6290 percent DISTORTIONAL.
StructureLab preserves `ENGINEERING_REVIEW_REQUIRED` with L/D-interaction and
reference-disagreement evidence.

The official curved-corner `C_200X90X20X2_CurvedConer` example independently
shows LOCAL, DISTORTIONAL, and GLOBAL regions. It remains an
`FCFSM_REFERENCE`: curved-corner MIDLINE geometry is outside the approved M3
sharp-corner contract and is not converted or passed into production.

## Mesh convergence

For the C120 reference:

| Family | Practical 10 mm | Reference 7.5 mm | Stress difference | Wavelength difference | Shared-vertex MAC |
|---|---:|---:|---:|---:|---:|
| LOCAL | 68.655972 MPa @ 99.3486 mm | 68.655223 MPa @ 99.3486 mm | 0.001091% | 0% | 0.999999999550 |
| DISTORTIONAL | 122.026677 MPa @ 829.9773 mm | 122.020218 MPa @ 829.9773 mm | 0.005293% | 0% | 0.999999999711 |

Families and participation remain stable. The 20 mm mesh differs by 1.18419
percent in DISTORTIONAL stress and is rejected by the 0.5 percent production
gate. Subdivision patterns at 6, 5, and 2.5 mm make the classical basis
numerically rank-deficient and fail the reconstruction gate; they are retained
as NOT_VALIDATED limits, not selected as reference meshes.

The 10/7.5 mm pair is an audited recommendation for this case. Every production
case must preserve its actual practical/reference widths and pass its own
comparison.

## Wavelength convergence

The C120 initial logarithmic grid contained 145 points from 20 to 10240 mm.
Adaptive critical-neighborhood refinement evaluated 157 points in three
iterations and resolved all LOCAL/DISTORTIONAL boundaries.

| Family | Refined stress | Refined wavelength | Last stress change | Last location change | MAC | Status |
|---|---:|---:|---:|---:|---:|---|
| LOCAL | 68.655773 MPa | 99.888078 mm | 0.000291% | 0.5401% | 0.999999 | AUTOMATIC_ACCEPTED |
| DISTORTIONAL | 122.000734 MPa | 821.036810 mm | 0% | 0% | 1.000000 | AUTOMATIC_ACCEPTED |

The implementation also has an executable regression proving that a falling
L/D minimum at a search boundary expands the range. All refinement points,
iteration counts, boundary flags, and comparison diagnostics are preserved in
`WavelengthSearchEvidence` and `CalculationTrace`.

## Engineering review and manual cases

The 2006 DSM Guide `cwlip_P.mat` selections are
`ENGINEERING_REFERENCE_CASES`, never automatic gates:

| Manual point | Official / StructureLab LF | Shape MAC | Official classical G/D/L/O (%) | StructureLab disposition |
|---|---:|---:|---|---|
| 6.6 in, labeled LOCAL | 0.124235046 / 0.124235057 | 1.000000 | 0.609598 / 53.567599 / 45.629847 / 0.192956 | ENGINEERING_REVIEW_REQUIRED; L/D interaction |
| 28.5 in (`28.52 in` annotation), engineering D selection | 0.269814119 / 0.269814129 | 1.000000 | 3.745045 / 89.753041 / 6.442518 / 0.059396 | ENGINEERING_REVIEW_REQUIRED; no automatic dominance, deficient basis rank, reconstruction error |

StructureLab reproduces their unconstrained FSM curve and relevant shapes,
detects ambiguity, and exposes candidates and provenance. The exact official
segmented contour is used only by adapter-internal reference QA; this does not
add curved-corner production support. At 28.5 in the basis rank is 147/148 and
the `2.17e-5` residual independently forces review. StructureLab does not
fabricate `PcrL` or `PcrD`. A future confirmed `EngineeringSelection` remains
distinguishable from an automatic result.

## Test coverage and remaining limitations

M9A tests cover unconstrained eigenvalue and mode-shape parity; classical
participation for three supported sharp C cases; official fcFSM LOCAL,
DISTORTIONAL, GLOBAL, and L/D interaction evidence; direct-sum reconstruction;
sign, scale, translation, and mirror invariance; MAC assignment, crossing,
branch transition, and L/D morphing; accepted, review-required, and non-unique
cases; production/reference mesh stress, wavelength, family, and MAC; adaptive
wavelength refinement and boundary expansion; exact dependency and
MATLAB/Octave provenance; the executable pyCUFSM `orth=2` blocker; adapter
isolation; no raw NumPy/pyCUFSM escape; and full M0-M8B regression.

Known limitations are the exact pyCUFSM/NumPy pins, unsupported constrained
pyCUFSM cFSM, unsupported curved corners and non-S-S features, numerical-rank
limits for certain fine-mesh patterns, QA-only global FSM results, manual DSM
Guide selections requiring engineering review, and absence of every M9B DSM
resistance calculation.

## Final repository verification

The editable package installation completed successfully with the frozen
dependencies. The complete repository suite then completed with `590 passed`
and no failures. The emitted warnings are retained deprecation warnings from
the pinned pyCUFSM 0.2.0/NumPy execution path; they were not suppressed and do
not change any validation status recorded above.
