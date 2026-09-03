# Design Methods

## Effective Width Method

M8B implements authorized ANSI/SDI AISI S100-24 LRFD concentric-compression
capacity for eligible supported C sections. It consumes `MemberDesignInput`,
produces its own immutable result and trace, and does not use a DSM resistance.
Flexure and demand utilization remain future work.

## Direct Strength Method

The future DSM route will implement authorized AISI S100-24 LRFD provisions.
A dedicated adapter will use pyCUFSM only as an elastic finite-strip buckling
engine and normalize its output before DSM receives it. pyCUFSM will not return
the final design resistance.

## Comparison mode

Comparison will place independently calculated EWM and DSM results side by
side, with their applicability, governing limit states, warnings, and traces.
The comparison layer will not become a third calculation engine.

M7 identifies the verified S100-24 clause routes for EWM and DSM applicability
and records them with M6 references. It implements no AISI strength equation,
coefficient, resistance-factor calculation, pyCUFSM call, or member resistance.
M8B is the separately authorized EWM axial implementation. All other future
calculation implementations still require separate authorization,
equation-level traceability, and validation.
