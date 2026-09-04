# M10 — EWM versus DSM Axial Compression Comparison

## Scope

M10 integrates the engineering-approved M8B EWM and M9B DSM axial-compression
engines. It adds demand utilization, execution routing, and informational
comparison only. It does not modify either resistance, reopen M9A, call
pyCUFSM directly, or implement flexure, interaction, shear, or reporting-side
calculations.

## Shared physical input and routing

`prepare_axial_compression_request` selects one existing simultaneous
`SectionDemandPoint` from a `ResolvedProject`. It creates method-specific
eligibility wrappers while retaining by identity one `ResolvedMember`, one M3
mechanics bundle, one `DesignContext`, one material qualification, one section
dimension record, and one project-scope record.

`design_axial_compression` is the single execution entry point:

```text
RunMode.EWM      -> M8B only -> MethodCompressionSummary
RunMode.DSM      -> M9B only -> MethodCompressionSummary
RunMode.COMPARE  -> M8B + M9B -> CompressionComparisonResult
```

An unrequested engine is not executed. The comparison layer receives completed
StructureLab resistance results and never calls an equation, reconstructs
nominal resistance, or reapplies the resistance factor.

## Demand convention

The M4/M5 canonical convention remains authoritative: `p_n > 0` is axial
compression in N. M10 uses that positive magnitude directly as `Pu`. Zero or
negative `p_n` is not transformed with `abs`, reversed, or treated as
compression; the point receives an explicit `METHOD_NOT_APPLICABLE` state and
no resistance engine or utilization is evaluated.

Combination ID, case type, resolved point ID, source point ID, station,
element, step type, and location remain available through the stored immutable
demand context. No combinations or component-wise envelopes are generated.

## Utilization and acceptance

For each design-ready method:

```text
UR_EWM = Pu / phiPn_EWM
UR_DSM = Pu / phiPn_DSM
PASS when UR <= 1.0
FAIL when UR > 1.0
```

`phiPn_EWM` and `phiPn_DSM` are copied directly from M8B and M9B respectively.
The comparison uses the exact `1.0` boundary without an engineering tolerance.
Positive finite demand and resistance are required.

## Comparison metrics

For a complete comparison:

```text
absolute_capacity_difference = phiPn_DSM - phiPn_EWM
relative_capacity_difference_percent =
    (phiPn_DSM - phiPn_EWM) / phiPn_EWM * 100
capacity_ratio_DSM_to_EWM = phiPn_DSM / phiPn_EWM
utilization_difference = UR_DSM - UR_EWM
```

A positive capacity difference therefore means DSM capacity is higher. The
lower capacity is identified as the informational comparison-governing result;
its utilization is the comparison-governing utilization. Exact equal capacity
uses `EQUAL_CAPACITY` deterministically.

This is not a code requirement to take the minimum and does not claim either
method is more correct. `code_required_design_method` remains `None` in
COMPARE mode. No divergence warning threshold is invented; the numerical
difference is reported without judging acceptability.

## Readiness, partial comparison, and applicability

Method states remain distinct:

- `METHOD_AVAILABLE`
- `METHOD_NOT_DESIGN_READY`
- `METHOD_NOT_APPLICABLE`
- `METHOD_UNSUPPORTED`
- `METHOD_INVALID_INPUT`

Normative applicability, software support, calculation status, and normalized
design readiness are retained separately. If DSM requires engineering review
without a valid `EngineeringSelection`, EWM remains available but all
comparison metrics and the comparison-governing method remain absent. The
result is `PARTIAL_COMPARISON`; EWM is not declared governing merely because
DSM is unavailable. M9A unsupported states propagate the same way. A valid
engineering selection is consumed only by M9B and its warnings/provenance flow
into M10 unchanged.

The approved M9B behavior for unlipped C sections is preserved: its
distortional branch remains not applicable inside DSM; M10 does not reinterpret
it.

## Results, trace, and reporting data

`MethodCompressionSummary` stores method, direct nominal/factored resistance,
common demand, utilization, PASS/FAIL, governing limit state, readiness,
applicability, software support, diagnostics, warnings, and the existing source
trace object.

`CompressionComparisonResult` stores both summaries, metrics, informational
governing semantics, overall/comparison status, provenance, and an M10
`CalculationTrace`. The trace references M8B/M9B trace IDs instead of
duplicating their calculation steps. `report_rows` exposes the two already
calculated summaries for a table such as:

```text
Method | phiPn | Pu | Utilization | Status | Governing Limit State
```

This is reporting-ready data only; reports do not execute engines or calculate
resistance, utilization, or comparison metrics.

## Validation and limitations

Targeted tests cover route isolation, shared physical-object identity, project
request preparation, positive-compression semantics, exact utilization
boundary, invalid demand/resistance, both capacity-difference signs, equality,
PASS/FAIL combinations, partial comparison, M9A unsupported/review/selection
states, lipped/unlipped sections, short/local/distortional/global-sensitive
fixtures, trace provenance, and architecture guards.

Remaining limitations are those frozen in M8B/M9A/M9B plus axial compression
only. M10 evaluates one simultaneous resolved demand point per invocation; a
future authorized member/project aggregation may select governing points from
these point-level results. No flexure, P-M interaction, or later milestone has
started.

