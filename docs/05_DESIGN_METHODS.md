# Design Methods

## Effective Width Method

M8B implements authorized ANSI/SDI AISI S100-24 LRFD concentric-compression
capacity for eligible supported C sections. It consumes `MemberDesignInput`,
produces its own immutable result and trace, and does not use a DSM resistance.
Flexure remains future work; M10 owns point-level axial demand utilization.

## Direct Strength Method

M9B implements S100-24 LRFD DSM concentric axial compression. It reuses the
shared M8B/E2 global calculation, consumes only normalized M9A LOCAL and
DISTORTIONAL results, respects engineering-review status, and emits its own
immutable resistance and trace. pyCUFSM does not return design resistance.
DSM flexure remains future work; M10 owns point-level axial demand utilization.

## Comparison mode

M10 places independently calculated EWM and DSM axial results side by side,
using the same positive-compression demand. It computes utilization and signed
informational differences, retains partial-comparison states, and references
the existing method traces. The comparison layer is not a third resistance
engine and does not establish a code-required minimum-method policy.

M7 identifies the verified S100-24 clause routes for EWM and DSM applicability
and records them with M6 references. It implements no AISI strength equation,
coefficient, resistance-factor calculation, pyCUFSM call, or member resistance.
M8B and M9B are the separately authorized axial implementations. All other
future calculation implementations still require separate authorization,
equation-level traceability, and validation.
