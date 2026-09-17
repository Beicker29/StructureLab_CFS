# M10 Supplement — Numerical EWM versus DSM Axial Comparison

## Purpose and basis

This supplement reports actual outputs returned by the engineering-approved
M10 workflow for existing deterministic test fixtures. It is a reporting and
engineering-interpretation record, not a new validation campaign. The cases
are synthetic controlled fixtures rather than production members.

All calculations were executed at full Python floating-point precision through
`design_axial_compression`. Values below are rounded only for presentation.
Canonical force units are N internally; tables show kN where noted. The shared
material has `Fy = 345 MPa`, and every case uses `Pu = 10.000 kN`.

The M10 signs and denominators were checked programmatically for every complete
comparison:

```text
Delta_phiPn = phiPn_DSM - phiPn_EWM
Delta_percent = Delta_phiPn / phiPn_EWM * 100
R_DSM_EWM = phiPn_DSM / phiPn_EWM
UR = Pu / phiPn
Delta_UR = UR_DSM - UR_EWM
```

## Numerical comparison table

| Case / member | Section | Family | Pu (kN) | phiPn EWM (kN) | phiPn DSM (kN) | DSM/EWM | Delta (%) | UR EWM | UR DSM | EWM limit state | DSM limit state | Comparison-governing |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| `M10_BASE_LIPPED` / `CASE_SYN_C_LIPPED` | `SYN_C_LIPPED` | Lipped C | 10.000 | 32.208 | 49.790 | 1.546 | +54.588 | 0.310 | 0.201 | `E3_1_LOCAL_GLOBAL` | `DISTORTIONAL` | EWM |
| `M10_SHORT_LIPPED` / `CASE_SYN_C_LIPPED` | `SYN_C_LIPPED` | Lipped C | 10.000 | 34.254 | 49.790 | 1.454 | +45.357 | 0.292 | 0.201 | `E3_1_LOCAL_GLOBAL` | `DISTORTIONAL` | EWM |
| `M10_GLOBAL_SENSITIVE` / `CASE_SYN_C_LIPPED` | `SYN_C_LIPPED` | Lipped C | 10.000 | 8.470 | 9.055 | 1.069 | +6.913 | 1.181 | 1.104 | `E3_1_LOCAL_GLOBAL` | `LOCAL_GLOBAL_INTERACTION` | EWM |
| `M10_LOCAL_SENSITIVE` / `CASE_SYN_C_LIPPED` | `SYN_C_LIPPED` | Lipped C | 10.000 | 34.254 | 16.957 | 0.495 | -50.496 | 0.292 | 0.590 | `E3_1_LOCAL_GLOBAL` | `LOCAL_GLOBAL_INTERACTION` | DSM |
| `M10_DISTORTIONAL_SENSITIVE` / `CASE_SYN_C_LIPPED` | `SYN_C_LIPPED` | Lipped C | 10.000 | 34.254 | 9.221 | 0.269 | -73.080 | 0.292 | 1.084 | `E3_1_LOCAL_GLOBAL` | `DISTORTIONAL` | DSM |
| `M10_UNLIPPED` / `CASE_SYN_C_UNLIPPED` | `SYN_C_UNLIPPED` | Unlipped C | 10.000 | 18.694 | 44.484 | 2.380 | +137.955 | 0.535 | 0.225 | `E3_1_LOCAL_GLOBAL` | `LOCAL_GLOBAL_INTERACTION` | EWM |

### Additional audit values

| Case | Fy (MPa) | Length (mm) | Delta phiPn (kN) | Delta UR | EWM check | DSM check | Overall status |
|---|---:|---:|---:|---:|---|---|---|
| `M10_BASE_LIPPED` | 345 | 500 | +17.582 | -0.110 | PASS | PASS | PASS |
| `M10_SHORT_LIPPED` | 345 | 100 | +15.536 | -0.091 | PASS | PASS | PASS |
| `M10_GLOBAL_SENSITIVE` | 345 | 2500 | +0.585 | -0.076 | FAIL | FAIL | FAIL |
| `M10_LOCAL_SENSITIVE` | 345 | 100 | -17.297 | +0.298 | PASS | PASS | PASS |
| `M10_DISTORTIONAL_SENSITIVE` | 345 | 100 | -25.033 | +0.793 | PASS | FAIL | FAIL |
| `M10_UNLIPPED` | 345 | 500 | +25.790 | -0.310 | PASS | PASS | PASS |

Positive `Delta phiPn` means DSM has the higher design resistance; negative
means DSM has the lower design resistance. “Comparison-governing” identifies
the lower resistance for this informational comparison. It does not identify a
more correct method and is not a code-required minimum-of-methods rule.

## Engineering interpretation limited to this benchmark set

1. **EWM is lower in 4 of 6 complete cases:** base lipped, short lipped,
   global-sensitive, and unlipped.
2. **DSM is lower in 2 of 6 complete cases:** local-sensitive and
   distortional-sensitive.
3. **Largest absolute percentage difference:** `137.955%`, for the single
   unlipped-C case, where DSM resistance is higher.
4. **Smallest absolute percentage difference:** `6.913%`, for the
   global-sensitive case. This is the closest pair in this set; no acceptance
   threshold is implied. The signed range is `-73.080%` to `+137.955%`.
5. **Median absolute difference:** `52.542%` across the six complete cases.
   This describes this deliberately varied benchmark set only.
6. **Largest divergence combinations:** the largest is EWM
   `E3_1_LOCAL_GLOBAL` versus DSM `LOCAL_GLOBAL_INTERACTION` for the unlipped
   fixture. The next largest is EWM `E3_1_LOCAL_GLOBAL` versus DSM
   `DISTORTIONAL` for the distortional-sensitive fixture.
7. **Local sensitivity:** the single controlled local-sensitive case differs by
   `50.496%` in magnitude, close to the set median. One such case is not enough
   to conclude that local-sensitive cases are systematically closer or farther
   apart.
8. **Distortional effect:** in the controlled distortional-sensitive case, DSM
   is governed by distortional buckling and its design resistance is `73.080%`
   below EWM. Thus distortional buckling materially reduces DSM in that tested
   case; this is not generalized to other sections.
9. **Unlipped-C trend:** only one unlipped case is present, so no systematic
   trend can be inferred. In that case DSM resistance is `137.955%` higher and
   EWM is comparison-governing.
10. **Different PASS/FAIL outcomes:** yes. In the distortional-sensitive case,
    EWM passes (`UR = 0.292`) while DSM fails (`UR = 1.084`) for the same
    `Pu`. No case in this set has DSM passing while EWM fails. Both methods fail
    in the global-sensitive case.

These differences are not errors. EWM and DSM are both AISI design routes;
the results show method divergence for these controlled inputs only.

## Engineering-review partial comparison

`M10_REVIEW_REQUIRED` uses member `CASE_SYN_C_LIPPED`, section
`SYN_C_LIPPED`, `Fy = 345 MPa`, length `500 mm`, and `Pu = 10.000 kN`.

- EWM remains valid: `phiPn = 32.208 kN`, `UR = 0.310`, PASS, governed by
  `E3_1_LOCAL_GLOBAL`.
- DSM is `METHOD_NOT_DESIGN_READY` with
  `ENGINEERING_REVIEW_REQUIRED` because the M9A LOCAL candidate requires an
  explicit `EngineeringSelection`.
- No `EngineeringSelection` exists in this fixture.
- DSM resistance, DSM utilization, capacity ratio, `Delta phiPn`,
  `Delta percent`, `Delta UR`, and comparison-governing method are therefore
  absent. M10 reports `PARTIAL_COMPARISON` and does not fabricate a DSM value.

## Controlled length sensitivity snapshot

The existing short, base, and global-sensitive fixtures use the same lipped-C
section, material, `Pu`, and controlled LOCAL/DISTORTIONAL M9A inputs. Only
member length changes. This is a descriptive snapshot, not a parametric study.

| Length (mm) | phiPn EWM (kN) | phiPn DSM (kN) | DSM/EWM | Delta (%) | Comparison-governing |
|---:|---:|---:|---:|---:|---|
| 100 | 34.254 | 49.790 | 1.454 | +45.357 | EWM |
| 500 | 32.208 | 49.790 | 1.546 | +54.588 | EWM |
| 2500 | 8.470 | 9.055 | 1.069 | +6.913 | EWM |

## Exact fixture and test sources

- Fixture constructor:
  `tests/design/comparison/conftest.py::make_m10_request`.
- Lipped, unlipped, short, and global-sensitive cases:
  `tests/design/comparison/test_m10_routing_integration.py::test_lipped_unlipped_short_and_global_sensitive_cases_integrate`.
- Local- and distortional-sensitive cases:
  `tests/design/comparison/test_m10_routing_integration.py::test_local_and_distortional_controlled_dsm_inputs_remain_comparison_ready`.
- Engineering-review case:
  `tests/design/comparison/test_m10_routing_integration.py::test_dsm_engineering_review_creates_partial_comparison_without_fabrication`.
- Metric and denominator definitions:
  `tests/design/comparison/test_m10_comparison.py`.

No M8B, M9A, M9B, or M10 theory, equations, utilization definitions,
comparison metrics, applicability rules, or computational architecture were
changed. No MATLAB/fcFSM, mesh-convergence, pyCUFSM cFSM, full regression, or
M11 work was performed for this supplement.

