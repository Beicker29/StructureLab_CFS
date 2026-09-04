# M10B.1 — Controlled pyCUFSM Release Compatibility Audit

## Disposition

The audit found an official published release that reproduces the exact
10-mode MATLAB CUFSM example: `pycufsm==0.1.7`.  It is the most recent passing
release, but it is older than the frozen production dependency `0.2.0` and is
therefore a **controlled downgrade candidate**, not a dependency upgrade.

No production code, dependency declaration, input contract, or normative
implementation was changed.  pyCUFSM was not patched or monkey-patched,
`neigs=10` was retained throughout, constrained cFSM was not re-audited, and
M11 was not started.

The complete machine-readable evidence, including all 145 returned mode
counts for each release, exact wavelengths, PyPI artifact hashes, index-132
eigenvalues, MATLAB MAC values, and focused M9A comparisons is in
`validation/m10b/pycufsm_release_compatibility_audit.json`.

## Official releases and environments

All nine releases published on PyPI were downloaded as their official wheels
and installed into separate temporary virtual environments.  Every wheel
declares `AFL-3.0`.

| Releases | Declared Python | Declared NumPy | Declared SciPy | Tested runtime |
|---|---:|---:|---:|---|
| 0.1.0–0.1.2 | >=3.8 | >=1.17 | >=1.4 | Python 3.12.10 / NumPy 1.26.4 / SciPy 1.11.4 |
| 0.1.3 | >=3.8 | >=1.17 | >=1.4 | Python 3.12.10 / NumPy 1.26.4 / SciPy 1.11.4 |
| 0.1.4–0.2.0 | >=3.10 | >=1.23.5 | >=1.10.0 | Python 3.12.10 / NumPy 1.26.4 / SciPy 1.11.4 |

Installation succeeded for every release.  A second isolated `0.1.7`
environment used the exact frozen numerical stack Python 3.12.10, NumPy
2.2.6, and SciPy 1.18.1; it also passed the exact reproduction.

No development or master branch was evaluated.

## Exact MATLAB configuration

The input was taken from official CUFSM v5.66 example
`examples/fcFSM_examples/C_120X80X15X1/modelData.m` and its preserved runtime
capture:

- sharp-corner C120×80×15×1 mm;
- 17 nodes and 16 elements;
- `E = 210000 MPa`, `nu = 0.3`, reference compression stress `1 MPa`;
- simply supported (`S-S`), `m = 1`;
- the exact 145 captured half-wavelengths generated from 20 to 10240 mm;
- `neigs = 10`.

## Exact mode-count results

| Release | Installation | Complete batch | Returned modes over all 145 points | Index 132 at 5830.597809954256 mm | Deterministic |
|---|---|---|---|---:|---|
| 0.1.0 | PASS | `(145, 10)` | 10 at every wavelength | 10 | YES |
| 0.1.1 | PASS | `(145, 10)` | 10 at every wavelength | 10 | YES |
| 0.1.2 | PASS | `(145, 10)` | 10 at every wavelength | 10 | YES |
| 0.1.3 | PASS | `(145, 10)` | 10 at every wavelength | 10 | YES |
| 0.1.4 | PASS | `(145, 10)` | 10 at every wavelength | 10 | YES |
| 0.1.5 | PASS | `(145, 10)` | 10 at every wavelength | 10 | YES |
| 0.1.6 | PASS | `(145, 10)` | 10 at every wavelength | 10 | YES |
| **0.1.7** | **PASS** | **`(145, 10)`** | **10 at every wavelength** | **10** | **YES** |
| 0.2.0 | PASS | `ValueError` | indices 1–131: 10; 132–142: 9; 143–144: 8; 145: 7 | 9 | YES per wavelength |

At index 132, `0.1.7` returns the finite positive tenth eigenvalue
`1033959.5669200151`.  All ten eigenvalues agree with official MATLAB CUFSM to
within `4.44e-6 %`, and the minimum corresponding-mode MAC is
`0.999999999999988`.  Releases `0.1.0`–`0.1.3` also pass, with a maximum
index-132 eigenvalue difference of `2.17e-6 %` and minimum MAC effectively
equal to one.

## LOCAL / DISTORTIONAL / GLOBAL parity

For `0.1.7`, the maximum absolute first-eigenvalue differences against the
official MATLAB reference points are:

| Family | Maximum difference |
|---|---:|
| LOCAL | `8.44e-11 %` |
| DISTORTIONAL | `8.10e-7 %` |
| GLOBAL | `5.06e-6 %` |

The representative first-mode MAC values at 20, 945.1687334012785, and 10240
mm are all greater than `0.99999999999999`.  The passing releases therefore
preserve elastic and modal parity in every family for which official reference
modes are available.

## Root cause

The discrepancy is caused by release `0.2.0` eigenvalue filtering and then
exposed as a public batch-output shape defect:

1. Releases through `0.1.7` keep positive, sufficiently real eigenvalues and
   do not impose the new upper bound.
2. Release `0.2.0` adds `real(eigenvalue) < 1e6`.  The tenth finite positive
   value at index 132 is `1033959.5669200151`, so it is discarded.
3. The `0.2.0` batch normalizer allocates every row to the maximum observed
   mode count and assigns a 9-value row to a 10-value slice, producing
   `ValueError: could not broadcast input array from shape (9,) into shape
   (10,)`.

The evidence excludes the alternatives requested in the audit:

- **positive/negative handling:** the missing tenth index-132 value is finite
  and positive;
- **solver dimension:** the 68-DOF dense generalized eigensolve completes;
- **numerical singularity:** no singular result explains this finite rejected
  mode;
- **dependency compatibility:** `0.1.7` passes under both dependency stacks;
- **non-determinism:** two independent per-wavelength passes produced
  identical counts and first eigenvalues for every release.

## Focused M9A compatibility of 0.1.7

The candidate was compared with `0.2.0` on the exact frozen numerical stack,
always requesting ten modes.

| Case | Returned modes | Max first-eigenvalue difference vs 0.2.0 | Min first-mode MAC vs 0.2.0 | Max first-eigenvalue difference vs MATLAB |
|---|---:|---:|---:|---:|
| C120×80×15×1 | 10 | `0 %` | `1.0` | `1.37e-5 %` |
| C100×40×10×1 | 10 | `0 %` | `1.0` | `9.16e-6 %` |
| C100×40×1 | 10 | `0 %` | `1.0` | `6.28e-6 %` |

The identical first eigenvalues and unit-MAC eigenvectors are identical inputs
to the StructureLab-owned modal classifier, so the approved classification
results are numerically preserved.  Critical results are:

| Result | 0.1.7 candidate | Approved M9A | Difference |
|---|---:|---:|---:|
| `PcrL` at 99.34862496587871 mm | 21287.407879736867 N | 21287.407879784492 N | `-2.24e-10 %` |
| `PcrD` at 829.9773149766452 mm | 38274.20305928717 N | 38274.2036585331 N | `-1.57e-6 %` |

This numerical result does not make `0.1.7` a drop-in production dependency.
The current adapter imports `pycufsm.solve`, introduced by the later package
layout; `0.1.7` exposes `pycufsm.cfsm`/`pycufsm.analysis`, so an unmodified
StructureLab import stops with `ModuleNotFoundError: No module named
'pycufsm.solve'`.  Numerical regression risk is low, but adapter/API migration
risk is high and requires a separate authorized change and full regression.

## Dependency decision

Keep `pycufsm==0.2.0` frozen for production.  Record `0.1.7` as the official
exact-reproduction candidate, but do not adopt it during M10B.1.  A future
owner-authorized milestone may evaluate a controlled downgrade plus the
required adapter compatibility work.  It must preserve the M9A numerical and
classification evidence and rerun the complete repository suite before any
dependency change is accepted.

M10B.1 did not make that architectural decision and did not proceed to M11.
