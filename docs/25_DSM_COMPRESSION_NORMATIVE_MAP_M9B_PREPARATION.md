# DSM Compression Normative Map — M9B Preparation Only

## Status and source

This is a source-confirmation record for a possible future M9B. It implements
no DSM equation, resistance, factor, utilization, or EWM/DSM comparison.

The primary source is ANSI/SDI AISI S100-2024, repository SHA-256
`6ec32742f056d08a0823557d9ce58b69d84312e64a6e656b8ba4b3b10cf4b4ca`.
The clauses below were checked directly in the local verified PDF. The
descriptions are original paraphrases; the PDF remains authoritative.

## Axial-compression responsibility map

| Quantity | Source and equation | Confirmed role | Future software owner |
|---|---|---|---|
| `Pne` | E2-1 through E2-4 | Nominal axial strength for yielding/global buckling. `Pne = Ag Fn`; `Fn` depends on `Fy/Fcre`. | Existing StructureLab analytical E2/M8B path |
| `Fcre`, `Pcre` | Appendix 2 Sections 2.1 and 2.3.1; Eq. 2.1-1 gives `Pcr = Ag Fcr` | Elastic global flexural, torsional, or flexural-torsional buckling input to E2. | Existing StructureLab analytical Appendix 2/M8B path |
| `Pnℓ` | E3.2-1 | DSM local-buckling nominal axial strength, limited not to exceed `Pne`. | Future M9B only |
| `λℓ` | E3.2-2 | Local slenderness uses `sqrt(Pne/Pcrℓ)`. | Future M9B only |
| `Pcrℓ` | E3.2 definition; Appendix 2 Sections 2.1/2.2 and 2.3.2 | Critical elastic local column buckling force. Numerical solutions are permitted by Section 2.2. | Proposed pyCUFSM constrained LOCAL result after M9A validation |
| `Pnd` | E4-1 | Distortional nominal axial strength, limited not to exceed `Py`. | Future M9B only |
| `λd` | E4-2 | Distortional slenderness uses `sqrt(Py/Pcrd)`. | Future M9B only |
| `Py` | E4-3 | Gross-section yield force `Ag Fy`. | Future M9B composition from shared inputs |
| `Pcrd` | E4 definition; Appendix 2 Sections 2.1/2.2 and 2.3.3 | Critical elastic distortional column buckling force. Numerical solutions are permitted by Section 2.2. | Proposed pyCUFSM constrained DISTORTIONAL result after M9A validation |

## Confirmed architecture

The source does not require pyCUFSM to provide global buckling. The future
composition is therefore permitted to take `Pne`/`Pcre` from StructureLab's
validated analytical E2 path, `Pcrℓ` from a validated constrained LOCAL FSM
analysis, and `Pcrd` from a validated constrained DISTORTIONAL FSM analysis.

M9A has not yet validated the latter two production inputs, so this map does
not authorize M9B.
