# M10B — Exact Official MATLAB CUFSM Example Reproduction Audit

## Status

M10B stopped at the first exact-reproduction discrepancy. M8B, M9A, M9B,
and M10 remain frozen and unchanged. No production equation, adapter,
classification policy, threshold, input contract, or dependency was modified.

The blocker is not an elastic-load disagreement. It occurs earlier, at exact
analysis-option and solver-output parity.

## Objective and benchmark rule

The requested audit asks whether StructureLab reproduces an official MATLAB
CUFSM example with the same geometry, material, stress, boundary conditions,
longitudinal terms, wavelengths, options, and requested number of modes. A
benchmark may not silently replace an official setting with an easier setting.

This rule materially differs from M9A. M9A validated the first unconstrained
mode with `eigenvalue_count=1`. M10B requires the official example's
`neigs=10`. The excellent M9A first-mode comparisons therefore remain valid,
but they cannot be relabeled as exact M10B configuration parity.

## Official provenance

- Repository: `https://github.com/thinwalled/cufsm-git`.
- Release: `v5.66`.
- Archive SHA-256:
  `e43d66ccc5b024ea40ba48c369f88b92c60fb7f0e11c6ce8e06b06f6b62b9104`.
- Runtime reference: GNU Octave 4.4.1 executing the official MATLAB source.
- Exact automatic example:
  `examples/fcFSM_examples/C_120X80X15X1/modelData.m`.
- `modelData.m` SHA-256:
  `3540d3ee6f3ac0fcdbda6e8410945140b9e4d4b298df90a9b257805bfffe3991`.
- M9A runtime capture SHA-256:
  `773ef1eada5bc9cc61e14a4f16a8b4811a66db8ca26f00224720be83e803d94c`.

The official archive remained pristine. M9A's documented Octave-only `eigs`
option spelling shim was present only in the extracted execution copy. Its
mathematical matrices, target, and requested mode count were unchanged. The
pristine and temporary hashes remain recorded in
`validation/m9a/official_cufsm_v566_source_manifest.json`.

## Inventory and benchmark classification

The complete machine-readable inventory is in
`validation/m10b/official_example_inventory.json`.

| Candidate | Classification | M10B disposition |
|---|---|---|
| `C_120X80X15X1` | `AUTOMATIC_CUFSM_EXAMPLE` | Exact replay blocked at `neigs=10` |
| `cwlip_P.mat` | `MANUAL_ENGINEERING_SELECTION_EXAMPLE`; `LEGACY_DSM_EQUATION_EXAMPLE` | Preliminary elastic replay succeeded; suite not finalized after STOP |
| `cnolip_P.mat` | Manual plus legacy | Not suitable for direct S100-24 final DSM parity |
| Curved `C_200X90X20X2` | `OUT_OF_SCOPE_FOR_STRUCTURELAB_V0_1` | Reference only |
| M9A sharp C100 generated cases | `UNSUITABLE_FOR_DIRECT_REPRODUCTION` as official examples | Retained as M9A evidence |
| M10 numerical fixtures | `SYNTHETIC_INTEGRATION_FIXTURE` | Not CUFSM physical-validation evidence |

The M10 fixtures explicitly inject controlled `PcrL` and `PcrD` values. They
remain valid software integration tests, but are not evidence that pyCUFSM or
StructureLab reproduced an official CUFSM physical model.

## Exact automatic input parity

The official `C_120X80X15X1` inputs were passed unchanged through the
StructureLab solver boundary:

| Input | Exact value |
|---|---|
| Centerline topology | 17 nodes, 16 sequential elements |
| Section | C120×80×15×1 mm, sharp corner |
| `E` | 210000 MPa |
| `nu` | 0.3 |
| Reference compression stress | 1 MPa |
| Boundary condition | `S-S` |
| Springs / constraints | 0 / 0 |
| Longitudinal terms | `m_all={1}` at every wavelength |
| Wavelengths | `logspace(log10(20), log10(10240), 145)` mm |
| Requested modes | `neigs=10` |
| fcFSM options | `ospace=1`, `couple=1`, `orth=2`, `norm=1` |

The example is already SI, so no geometry or material-unit conversion was
needed. StructureLab-owned M3 section properties were supplied as required by
the frozen M9A adapter architecture.

## Exact reproduction discrepancy

Official MATLAB/Octave CUFSM completes the 145-wavelength run and stores ten
modes at each point. At wavelength index 132 (one-based),
`L = 5830.597809954256 mm`, its unconstrained result still contains ten modes.

With the same input and `eigenvalue_count=10`, pyCUFSM 0.2.0 returns only nine
positive modes at that wavelength:

```text
ValidationError:
pyCUFSM curve shape (1, 9) differs from (1, 10)
```

When all wavelengths are passed together, pyCUFSM fails earlier while
normalizing the variable-length result:

```text
ValueError:
could not broadcast input array from shape (9,) into shape (10,)
```

The upstream location is `pycufsm/fsm.py:471`; StructureLab independently
detects the unexpected shape in
`src/cfs_design/stability/pycufsm_adapter/_solver.py`.

The runtime was Python 3.12.10, `pycufsm==0.2.0`, `numpy==2.2.6`, and
`scipy==1.18.1`, exactly preserving the frozen M9A dependency set.

The first divergent layer is therefore:

```text
ANALYSIS_OPTION_AND_SOLVER_OUTPUT_PARITY
```

No `PcrL`, `PcrD`, wavelength, MAC, participation, `Pnl`, `Pnd`, `Pn`, or
`phiPn` value can honestly be accepted as an exact-settings M10B result after
this failure.

## Prohibited substitutions not applied

- `neigs=10` was not replaced by `eigenvalue_count=1`.
- pyCUFSM was not patched or monkey-patched.
- StructureLab's expected-shape validation was not weakened.
- No automatic classifier, mode threshold, or production equation was tuned.

Using one requested mode would reproduce the already approved M9A first-mode
evidence, including the documented LOCAL, DISTORTIONAL, GLOBAL, and MAC
comparisons. It would not reproduce this official example's exact analysis
settings and is therefore not accepted for M10B without an explicit owner
change to the benchmark rule.

## Preliminary manual lipped observation

Before the automatic blocker was isolated, the exact 2006 DSM Guide
`cwlip_P.mat` segmented contour was replayed through the validation-only
adapter path with all 99 official wavelengths and `neigs=10`. This did not
alter production geometry support.

| Manual point | CUFSM LF | StructureLab LF | Difference | MAC after exact in→mm DOF conversion |
|---|---:|---:|---:|---:|
| LOCAL, 6.6 in | 0.124235045625098 | 0.124235056685175 | +0.000008903% | 0.999999999999998 |
| DISTORTIONAL, 28.5 in (`28.52 in` published annotation) | 0.269814119381267 | 0.269814128822829 | +0.000003499% | 0.999999999999997 |

The maximum relative difference among all recorded replayed modes was
`0.0090724%`. These are preliminary observations only; they do not override
the required STOP or constitute a completed permanent benchmark suite.

The inch-to-millimetre conversion used exactly `25.4 mm/in`. For MAC, official
translational DOFs were converted by the same exact factor while rotational
DOFs remained dimensionless. Eigenvector sign and scale were removed by MAC.

## Normative-version audit

The official 2006 Guide files are associated with AISI 2002 examples and
Appendix 1 AISI 2004 DSM equations. The inspected MATLAB postprocessors select
and plot elastic points; they are not ANSI/SDI AISI S100-24 DSM calculators.

The historical local and distortional formulas use the legacy power-law
expressions and thresholds (`0.776` and `0.561`). StructureLab S100-24 uses the
approved rational E3.2/E4 equations and derived transition values. The
classification is therefore `LEGACY_NOT_EQUIVALENT`. A legacy final-capacity
difference must not be treated as a StructureLab defect.

The unlipped guide example also conservatively assigns a mixed first minimum
to both LOCAL and DISTORTIONAL. Under frozen M9B/S100-24 applicability,
DISTORTIONAL is not applicable to an unlipped C. Direct final-capacity parity
would therefore be normatively invalid.

## Deferred comparison layers

Because the automatic exact-settings case failed before eigensolution
normalization, the following M10B layers were not completed:

- automatic critical LOCAL and DISTORTIONAL comparisons;
- automatic GLOBAL elastic QA;
- exact-setting mode-shape and G/D/L/O comparisons;
- permanent manual `EngineeringSelection` example packaging;
- S100-24 variable-by-variable `Pnl`, `Pnd`, `Pn`, and `phiPn` comparison;
- master benchmark results table and runnable example suite.

No empty, fabricated, or one-mode-substituted values are reported for those
layers.

## Recommended next decision

Owner authorization is required for one of these materially different paths:

1. approve a controlled dependency-upgrade audit for a released pyCUFSM
   version that can preserve the official ten-mode output; or
2. explicitly relax M10B from exact setting parity to a first-mode benchmark
   with `eigenvalue_count=1`, clearly labeled as a benchmark deviation.

Neither path is authorized by the current milestone. M9A/M9B production must
not be changed implicitly.

## `tmp/` cleanup gate

- Resolved path:
  `D:\Users\byomayusa\Documents\GitHub\StructureLab_CFS\tmp`.
- Size before cleanup check: `2,401,484,427 bytes` (`2.237 GiB`).
- Cleanup performed: **no**.
- Space recovered: `0 bytes`.

Cleanup was not authorized by the milestone's own prerequisites because the
permanent executable M10B evidence was not completed before STOP. Moreover,
`git ls-files -- tmp` reports tracked files, directly failing the required
"no tracked files under tmp" check. Unique official execution material also
remains there pending the owner decision. Nothing was deleted.

## Files added and verification scope

Only validation and documentation records were added:

- `validation/m10b/official_example_inventory.json`;
- `validation/m10b/exact_reproduction_blocker.json`;
- this document.

No runnable example was added because doing so with `neigs=1` would misstate
exact parity. No test or full regression was run because production code did
not change and the exact benchmark cannot proceed past its solver boundary.
M11 was not started.

## Conclusion

Input parity is proven through the solver call boundary. Exact result parity
is not established because pyCUFSM 0.2.0 cannot execute the official automatic
example with its published `neigs=10` setting across all 145 wavelengths. This
is a validation blocker, not evidence of a wrong S100-24 resistance equation.

