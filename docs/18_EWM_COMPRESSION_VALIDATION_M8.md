# M8B EWM Axial-Compression Validation

## Status and authority

M8B implements the ANSI/SDI AISI S100-2024 LRFD effective-width route for
concentric axial compression within the approved sharp-corner, orthogonal,
singly symmetric `C_UNLIPPED` and `C_LIPPED` scope. The registered primary PDF
has SHA-256
`6ec32742f056d08a0823557d9ce58b69d84312e64a6e656b8ba4b3b10cf4b4ca`.
All equations in the audit table below were checked directly against that PDF.

The engine boundary is immutable `MemberDesignInput`. Successful benchmarks
use synthetic, explicit AISI dimensions and A3 qualification evidence; they do
not populate or relax production contracts. Numeric expectations are fixed in
tests and do not call the production EWM function that they validate.

## Validation philosophy

Validation separates four concerns:

1. direct equation arithmetic and piecewise boundaries;
2. coherent M3A/M3B mechanics consumption and dimensional sanity;
3. complete unlipped and lipped capacity chains, including E4;
4. blocked-state, trace, dependency, and production regressions.

All calculations retain full floating precision. `pytest.approx` comparisons
use its explicit test tolerance only for comparing independently established
reference values; no rounding enters production calculations.

## Independent C_UNLIPPED benchmark

The controlled section has explicit dimensions `w_web=100 mm`, two
`w_flange=40 mm` elements, `t=1 mm`, `Ag=180 mm2`, `Fy=345 MPa`, and
`KxLx=KyLy=KtLt=2500 mm`. M3 supplies `Ix=283333.3333333333 mm4`,
`Iy=28444.444444444445 mm4`, `J=60 mm4`,
`Cw=50196078.43137255 mm6`, `x0=-23.006535947712415 mm`, and `y0=0`.

| Quantity | Independent result |
|---|---:|
| `ro` | 47.5541739676496 mm |
| `Pex`, `Pey`, `Pt` | 90826.67943509166, 9118.286249169987, 9185.06160997131 N |
| `beta` | 0.7659410885749315 |
| coupled `Pcre` / `Fcre` | 8955.76335496274 N / 49.75424086090412 MPa |
| `lambda_c`, `Fn`, `Pne` | 2.6332645673840105, 43.634469235012915 MPa, 7854.204462302325 N |
| web effective width | 92.68649686086418 mm |
| each flange effective width | 32.57693441121566 mm |
| `Ae` | 157.8403656832955 mm2 |
| E3.1 `Pnl` | 6887.280580450945 N |
| governing state | E3.1 local/global |
| `phi_c`, `phi_c Pn` | 0.85, 5854.1884933833035 N |

The coupled flexural-torsional mode governs this benchmark. A separate case
with increased `KyLy` makes pure y-flexure govern. Increasing each relevant
effective length was checked not to increase its associated elastic result.
For a physical open C with nonzero `x0`, the coupled root is below the pure
x-flexural root; therefore a separate physical x-flexure-governing C case does
not exist within this narrow singly symmetric representation. `Pex` remains an
explicit tested candidate and enters the coupled solution.

## Independent C_LIPPED benchmark

The non-governing-E4 case adds two explicit `10 mm` lips to the `100 x 40 x 1`
MIDLINE mechanics, uses separately declared flat/overall AISI dimensions, and
uses explicit `Lm=500 mm`. `Ag=200 mm2`; the global result is
`Pcre=12147.209475405009 N`, `Fcre=60.736047377025045 MPa`,
`Fn=53.26551354965097 MPa`, and `Pne=10653.102709930194 N`.

The web effective width is `87.06818038875241 mm`; each flange and lip remains
`40 mm` and `10 mm`, respectively. Thus `Ae=187.0681803887524 mm2` and
`Pnl=9964.282697205643 N`.

For Appendix 2, Table 2.3.3-1 gives:

| Quantity | Independent result |
|---|---:|
| `Af`, `Jf` | 50 mm2, 16.666666666666668 mm4 |
| `Ixf`, `Iyf`, `Ixyf` | 286.6666666666667, 8533.333333333334, 800 mm4 |
| `xof`, `xhf`, `yof=yhf` | 16, -24, -1 mm |
| `Lcrd= Ld` | 366.3457407637397 mm |
| flange/web elastic stiffness terms | 467.39551282138063, 371.7948717948718 N |
| geometric flange/web terms | 2.8494966065963805, 1.2256492439296012 mm2 |
| `Fcrd`, `Pcrd` | 205.92892019016637 MPa, 41185.78403803327 N |
| `lambda_d`, `Pnd` | 1.2943474618626338, 42278.89687223019 N |

E3.1 governs at `Pn=9964.282697205643 N` and
`phi_c Pn=8469.640292624796 N`; E4 is retained visibly as a non-governing
candidate.

## E4-governing benchmark

A separate `100 x 20 x 5 x 1 mm` lipped C, `L=100 mm`, and sourced
`Lm=5000 mm` exercises E4 governing. Its independent candidates are:

| Candidate | Nominal strength |
|---|---:|
| E2 | 50949.33831113632 N |
| E3.1 | 30704.399869758516 N |
| E4 | 23753.727336681128 N |

The E4 intermediates are `Lcrd=155.81728474124952 mm`,
`Fcrd=115.25107310107303 MPa`, `Pcrd=17287.660965160954 N`, and
`lambda_d=1.7301631528398242`. The final LRFD strength is
`20190.668236178957 N`.

## Controlled interpretation validation

Stable record `S10024-A1-1_3A-XREF-001` preserves the published Appendix 1
Section 1.3(a) reference to Section 1.1.1 and the project-authorized no-hole
interpretation to Section 1.1(a), Eqs. 1.1-1 through 1.1-4, with `k` from
Section 1.3/Table 1.3-1. The trace records both references, rationale,
Section 1.1.4 corroboration, no-hole restriction, project/date/status, and
official-correction supersession rule. The record is applied only in the
slender simple-lip branch that needs the referenced flange width. Holes remain
outside the representable and supported v0.1 input scope.

## Numerical tolerances and exact boundaries

| Name | Value | Purpose | Boundary validation |
|---|---:|---|---|
| `SECTION_SYMMETRY_I_XY_ABSOLUTE_TOLERANCE_MM4` | `1e-9 mm4` | clean numerical `Ixy` residue before the singly symmetric route | at/above boundary test |
| `SECTION_SYMMETRY_Y0_ABSOLUTE_TOLERANCE_MM` | `1e-9 mm` | clean numerical transverse shear-center residue | at/above boundary test |
| `EFFECTIVE_AREA_ABSOLUTE_TOLERANCE_MM2` | `1e-9 mm2` | permit summation roundoff in `Ae <= Ag` | below/above boundary test |
| `EFFECTIVE_AREA_RELATIVE_TOLERANCE` | `1e-12` | scale the same area-roundoff guard | scale and bound tests |
| `GLOBAL_DISCRIMINANT_RELATIVE_CLEANUP_TOLERANCE` | `1e-12` | clean a tiny negative roundoff at the coupled repeated root | repeated-root test |

The normative branch values `lambda=0.673`, `lambda_c=1.5`, `D/w=0.25`,
`D/w=0.8`, and `lambda_d=5` are exact specification limits, not software
tolerances. Geometry equality used to select the analytical E4 route is exact
and has tolerance zero. The code does not use implicit `math.isclose` defaults
for normative decisions.

## Equation audit

| Implementation function | Engineering quantity | Clause | Equation/table ID | Inputs | Output unit | Independent test | Trace step | PDF verified |
|---|---|---|---|---|---|---|---|---|
| `resolve_effective_lengths` | global effective lengths | App. 2 §2.3.1 definitions | inputs to 2.3.1-1 to -3 | `L,Kx,Ky,Kt` or `Lx,Ly,Lt` | mm | `test_effective_length_contract_keeps_global_lengths_independent` | Global effective lengths | YES |
| `calculate_global_buckling` | `ro,Pex,Pey,Pt,beta,Pcre,Fcre` | App. 2 §§2.3.1, 2.3.1.1, 2.3.1.1.1, 2.3.1.1.2 | 2.3.1-1 to -4, 2.3.1-7, 2.3.1.1-1, 2.3.1.1.1-1, 2.3.1.1.2-1 | M3 set, global lengths, prescribed `E,G` | N, MPa | `test_global_buckling_matches_independent_unlipped_benchmark` | Global elastic buckling loads | YES |
| `calculate_global_column_strength` | `lambda_c,Fn,Pne` | E2 | E2-1 to E2-4 | `Ag,Fy,Fcre` | MPa, N | `test_e2_inelastic_branch_matches_independent_value`; elastic/transition companions | E2 global column strength | YES |
| `calculate_uniform_effective_width` | `Fcrl,lambda,rho,b` | App. 1 §1.1(a) | 1.1-1 to 1.1-4 | `w,t,f,k,E,mu` | MPa, mm | `test_uniform_plate_slender_branch_matches_independent_arithmetic`; branch matrix | Effective width per element | YES |
| `calculate_unstiffened_effective_width` | supported-free effective width | App. 1 §1.2.1(a) | §1.1(a), `k=0.43` | `w,t,f` | mm | unlipped complete benchmark | Effective width FLANGE/LIP | YES |
| `calculate_simple_lip_effective_width` | flange portions and lip contribution | App. 1 §1.3(a) | 1.3-1 to 1.3-11; Table 1.3-1; controlled 1.1-1 to -4 | explicit `w,d,D,t,theta,f` | mm, mm4 | simple-lip branch/boundary tests and lipped benchmark | Controlled interpretation; Effective width per flange/lip | YES |
| `calculate_effective_area` | `Ae` | E3.1 explanatory text | following E3.1-1 | identified widths, `t,Ag` | mm2 | `test_effective_area_is_element_by_element_and_has_unique_ids` | E3.1 effective area | YES |
| `calculate_local_global_strength` | `Pnl` | E3.1 | E3.1-1 | `Ae,Fn,Pne` | N | complete benchmarks and upper-limit test | E3.1 local-global nominal strength | YES |
| `calculate_flange_lip_properties` | analytical flange/lip terms | App. 2 §2.3.3.1 | Table 2.3.3-1 | MIDLINE `b,d,t` | mm2, mm4, mm6, mm | `test_orthogonal_flange_lip_properties_match_table_benchmark` | Appendix 2 distortional flange properties | YES |
| `calculate_distortional_buckling` | `Lcrd,Ld`, stiffness terms, `Fcrd,Pcrd` | App. 2 §2.3.3.1 | 2.3.3.1-1 to -7 | table terms, `ho,t,Lm,E,G,mu,Ag` | mm, N, mm2, MPa | `test_appendix_2_distortional_equations_match_independent_benchmark` | Appendix 2 analytical distortional buckling | YES |
| `calculate_e4_strength` | `Py,lambda_d,Pnd` | E4 | E4-1 to E4-3 | `Ag,Fy,Pcrd` | N | `test_e4_strength_and_slenderness_limit`; governing pair | E4 distortional nominal strength | YES |
| `calculate_ewm_compression_resistance` | candidates, governing `Pn`, `phi_c Pn` | E1; E2; E3; E4 | minimum rule; stated `phi_c=0.85` | coherent prior results | N | complete unlipped/lipped benchmarks | Candidates; governing; LRFD strength | YES |

## Known limitations

- Only S100-24 LRFD, EWM, concentric compression is calculated.
- Only orthogonal sharp-corner MIDLINE mechanics are accepted; Appendix 1
  widths come only from `StandardSectionDimensions`, never from a conversion.
- Global buckling is the singly symmetric C route. Unequal paired geometry is
  software `UNSUPPORTED`.
- The E4 analytical route requires equal stiffened flanges/lips and explicit,
  sourced `Lm`; the Appendix 2 §2.2 numerical route is not implemented.
- Continuous rotational stiffness is conservatively zero only under Appendix 2
  §2.3.3.1. No `Lb`, member length, or brace-spacing substitution for `Lm`
  exists.
- No effective-area iteration is required by the verified uniform compression
  procedure because Appendix 1 evaluates widths at the already established
  `Fn`; therefore there is no convergence policy or last-iterate fallback.
- DSM, pyCUFSM, flexure, demand utilization, P-M interaction, and reports are
  not part of M8B. M9A now supplies only elastic-buckling evidence; M9B DSM
  resistance has not started.
- Current production records intentionally lack executable evidence and remain
  blocked; only controlled synthetic fixtures produce strengths.
