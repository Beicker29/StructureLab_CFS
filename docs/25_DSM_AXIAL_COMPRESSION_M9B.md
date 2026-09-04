# M9B — S100-24 DSM Axial Compression

## Status and scope

M9B implements ANSI/SDI AISI S100-2024 LRFD concentric axial-compression
resistance for the approved catalog lipped and unlipped C-section scope. It
consumes the shared `MemberDesignInput`, the analytical global result shared
with M8B, and frozen M9A elastic-buckling results. M10 comparison and DSM
flexure have not started.

The primary source is the registered local S100-24 PDF with SHA-256
`6ec32742f056d08a0823557d9ce58b69d84312e64a6e656b8ba4b3b10cf4b4ca`.
The implementation uses concise equation identifiers and original paraphrases;
the PDF remains authoritative.

## Normative map and quantity ownership

| Quantity | Authority | Clause/equation |
|---|---|---|
| `Pcre`, `Fcre` | Shared StructureLab M8B analytical global mechanics | Appendix 2 Sections 2.3.1 and 2.3.1.1 |
| `Pne` | Shared StructureLab E2 column curve | E2-1 through E2-4 |
| `Pcrl` | M9A accepted or explicitly engineer-selected LOCAL result | Appendix 2 Sections 2.1/2.2; Eq. 2.1-1 |
| `Pcrd` | M9A accepted or explicitly engineer-selected DISTORTIONAL result | Appendix 2 Sections 2.1/2.2; Eq. 2.1-1 |
| `Py` | M3 gross area and resolved material yield stress | E4-3, `Py = Ag Fy` |
| `Pnl` | M9B DSM local calculation | E3.2-1 and E3.2-2 |
| `Pnd` | M9B DSM distortional calculation | E4-1 through E4-3 |
| `Pn` | Smallest applicable nominal axial strength | E1 |
| `phi_c` | Central normative constant, applied once | E2/E3/E4, LRFD `0.85` |

pyCUFSM GLOBAL output is never a design input. Catalog reference properties do
not replace the coherent M3 mechanics bundle.

## Current S100-24 equations

S100-24 uses smooth rational equations rather than the historical DSM power
expressions. For the approved no-hole scope and `lambda_l <= 5`:

```text
lambda_l = sqrt(Pne / Pcrl)
Pnl = min(Pne, 1.2 * (1 + 0.10 lambda_l^2)
                    / (1 + 0.55 lambda_l^2) * Pne)
```

The exact intersection with the `Pne` cap is
`lambda_l = sqrt(20/43) = 0.6819943394704735`. Values at or below this
intersection use `PNE_UPPER_BOUND`; larger values use `LOCAL_REDUCTION`. No
comparison tolerance modifies this normative boundary.

For applicable distortional buckling, no holes, and `lambda_d <= 5`:

```text
lambda_d = sqrt(Py / Pcrd)
Pnd = min(Py, 1.2 * (1 + 0.05 lambda_d^2)
                  / (1 + 0.67 lambda_d^2) * Py)
```

The exact cap intersection is
`lambda_d = sqrt(20/61) = 0.5725983343138682`. Values at or below it use
`PY_UPPER_BOUND`; larger values use `DISTORTIONAL_REDUCTION`.

E4 applies to the approved lipped C section because its flange has an edge
stiffener. It is `NOT_APPLICABLE` to the approved unstiffened C section; that
case uses `Pn = Pnl`. Otherwise E1 gives `Pn = min(Pnl, Pnd)`. Exact equality is
resolved deterministically to `LOCAL_GLOBAL_INTERACTION` without changing the
capacity.

## Architecture and review policy

```text
MemberDesignInput
    + shared M8B Appendix 2/E2 global calculation
    + M9A ElasticBucklingResult
        -> M9B E3.2 and E4 equations
        -> E1 governing nominal strength
        -> centralized LRFD phi_c
        -> immutable DSMCompressionResistance + CalculationTrace
```

An `AUTOMATIC_ACCEPTED` M9A candidate may enter M9B directly. A
review-required family blocks M9B unless the frozen M9A result contains a valid,
explicitly confirmed `EngineeringSelection` referencing candidates of that
same family. The DSM result records `AUTOMATIC`, `ENGINEERING_SELECTED`, or
`MIXED` input basis and never relabels a manual selection as automatic.

`M9AUnavailable` carries an explicit upstream reason and provenance into an
M9B `UNSUPPORTED` result. Missing family evidence, case-ID mismatch,
rank-deficient meshes, unsupported M9A topology, and unresolved ambiguity do
not produce a resistance.

## Result and numerical safety

`DSMCompressionResistance` is immutable and retains `Py`, `Pne`, `Pcrl`,
`lambda_l`, `Pnl`, optional applicable `Pcrd`, `lambda_d`, `Pnd`, `Pn`,
`phi_c`, `phi_c Pn`, governing limit state, equation references, M9A
provenance, diagnostics, warnings, applicability, readiness, and trace.
Normative applicability and software-support status are retained as separate
fields; one is never used as a substitute for the other.

All force, stress, area, and slenderness inputs must be positive and finite.
E3.2 and E4 inputs above their explicit `lambda <= 5` ranges return
`UNSUPPORTED`; no Commentary extension is silently used. No NumPy, pyCUFSM, or
MATLAB object escapes the stability adapter.

## Independent benchmark

`validation/m9b/dsm_axial_compression_hand_fixture.json` is an independently
worked S100-24 equation fixture using exact rational arithmetic:

| Input/result | Value |
|---|---:|
| `Pne` / `Pcrl` | 50,000 / 20,000 N |
| `lambda_l` / `Pnl` | 1.5811388301 / 31,578.9474 N |
| `Py` / `Pcrd` | 69,000 / 30,000 N |
| `lambda_d` / `Pnd` | 1.5165750888 / 36,332.9398 N |
| `Pn` / `phi_c Pn` | 31,578.9474 / 26,842.1053 N |

The fixture derives directly from E3.2-1/E3.2-2 and E4-1/E4-2, not from a
StructureLab output or an unverified 2006 equation.

## Validation and limitations

Targeted tests cover both cap/reduction branches, exact boundaries,
continuity, monotonic reduction, upper bounds, the `lambda = 5` endpoint,
nonfinite inputs, E1 governing/equality behavior, LRFD application, M8B `Pne`
reuse, M9A automatic/review/selection/unsupported states, lipped/unlipped
applicability, provenance, dependency direction, and absence of M10/flexure.

Remaining limitations are the frozen M9A limitations, the singly symmetric
M8B global route, no holes, no built-up sections, no end conditions outside the
validated M9A scope, no DSM flexure, no utilization, and no EWM/DSM comparison.
