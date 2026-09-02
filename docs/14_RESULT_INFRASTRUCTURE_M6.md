# M6 Result Infrastructure

Milestone 6 provides generic calculation records and result containers shared
by future EWM and DSM engines. It intentionally contains no AISI equation,
coefficient, resistance factor, effective-width rule, DSM expression,
utilization formula, governing selection, or pyCUFSM integration.

## Public package

`cfs_design.results` exposes:

- `EngineeringUnit`, `EngineeringValue`, `MetadataEntry`, and `LimitStateId`;
- `EquationReference`, `CalculationStep`, and `CalculationTrace`;
- `EngineeringDiagnostic` and `DiagnosticSeverity`;
- separate `CalculationStatus`, `ApplicabilityStatus`, and
  `DesignCheckStatus` identities;
- `LimitStateResult`, `MethodDesignResult`, `MemberDesignResult`, and
  `ComparisonResult`;
- deterministic `make_trace_id()` and `make_step_id()` helpers.

These are immutable data records. None is a calculation service.

## Status separation

One ambiguous result-status enum would incorrectly mix different engineering
meanings. M6 therefore records three independent concepts:

```text
CalculationStatus
    NOT_RUN | COMPLETED | COMPLETED_WITH_WARNINGS | FAILED

ApplicabilityStatus
    NOT_EVALUATED | APPLICABLE | NOT_APPLICABLE | UNSUPPORTED | INVALID_INPUT

DesignCheckStatus
    NOT_EVALUATED | PASS | FAIL | WARNING
```

M6 only defines these identities. M7 will determine applicability; later design
workflows will calculate and assign design-check states.

## Result hierarchy

```text
MemberDesignResult
`- MethodDesignResult[]                 one method and demand point
   `- LimitStateResult[]
      `- CalculationTrace

ComparisonResult
|- optional EWM MethodDesignResult
`- optional DSM MethodDesignResult
```

`LimitStateResult` can retain nominal strength, design strength, demand,
utilization, trace, diagnostics, and metadata. All engineering fields remain
optional so unsupported/infrastructure-only states never fabricate zero
strengths. If present, strength and demand units must agree and utilization
must use unit `1`.

`MethodDesignResult` groups limit states for exactly one member, combination,
and simultaneous demand point. Its `traces` property exposes the limit-state
traces without storing a second duplicate collection.

`MemberDesignResult` can retain all method/demand-point results for a physical
member. Optional governing fields are storage locations for later workflows;
M6 provides no ranking function and never populates them automatically.

`ComparisonResult` can retain future precomputed EWM/DSM differences. It does
not calculate them and does not assume that the lower strength is legally
governing. Applicability-aware comparison remains future work.

## Units and numerical policy

The controlled unit identity lives in `cfs_design.core.units`, which remains
the single unit source. Values entering results must already be normalized to
the repository's canonical SI representation. M6 stores full Python
floating-point values and rejects booleans, NaN, and infinities. Reports own
display rounding and future display-unit conversions.

## References and provenance

Standard references support standard ID, edition, clause, and equation ID.
Non-normative mechanics and software references are equally representable.
M6 does not instantiate a real AISI equation reference.

Flat immutable `MetadataEntry` collections accept only JSON-friendly primitive
values. Future traces can therefore retain section/material identifiers,
standard edition, repository version, or pyCUFSM version/configuration without
coupling the generic result layer to an external engine.

## Immutability and serialization readiness

All result records use frozen/slotted dataclasses and tuples. They contain no
file handles, callables, NumPy objects, loggers, or mutable dictionaries.
`dataclasses.asdict()` produces a tree that standard JSON encoding can consume,
but final JSON/YAML/report serializers are intentionally deferred.

## Explicit M6 boundary

M6 does not:

- run a design or mechanics calculation;
- evaluate `CalculationStep.expression`;
- select governing limit states, demand points, combinations, or methods;
- calculate nominal/design strength, utilization, or comparison differences;
- determine AISI applicability or software support;
- implement EWM, DSM, pyCUFSM, reports, or output serialization.

Future calculation engines must compute once, create result/trace records, and
allow reports to consume those records without recalculation.
