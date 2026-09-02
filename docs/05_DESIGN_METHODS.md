# Design Methods

## Effective Width Method

The future EWM route will implement authorized ANSI/SDI AISI S100-24 LRFD
provisions and produce its own result and trace. It will consume the common
resolved member and will not use a DSM resistance.

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
Exact future calculation implementations require separate authorization,
equation-level traceability, and validation.
