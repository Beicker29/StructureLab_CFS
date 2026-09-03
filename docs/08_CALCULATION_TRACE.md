# Calculation Trace

Milestone 6 implements the shared immutable calculation-record infrastructure
in `cfs_design.results`. It records values that an engineering engine has
already calculated; it does not execute an equation, perform a unit conversion,
select a governing result, or implement a design provision.

## Trace hierarchy

```text
CalculationTrace
|- trace_id / linked project-member-demand identifiers
|- calculation status
|- optional DesignMethod and LimitStateId
|- CalculationStep[]
|  |- input EngineeringValue[]
|  |- documentation-only expression
|  |- optional EquationReference
|  |- result EngineeringValue[]
|  `- EngineeringDiagnostic[]
|- final EngineeringValue[]
|- EngineeringDiagnostic[]
`- MetadataEntry[]
```

All records are frozen, slotted dataclasses and all collections are tuples.
Step identifiers must be unique within a trace. Engineering-value names must
be unique within each input/result collection. `make_trace_id()` and
`make_step_id()` provide deterministic readable identifiers; callers may also
supply another deterministic identifier appropriate to their workflow.

`CalculationStep.expression` is presentation metadata only. The result package
does not call `eval`, compile, parse, or otherwise execute expression strings.
Future design/mechanics code calculates once and passes the completed values to
the trace.

## Values and units

Every `EngineeringValue` has a name, finite floating-point value, and one
explicit controlled `EngineeringUnit`. Optional symbol and description fields
add presentation meaning without changing the stored value. No rounding occurs
in the result layer.

Internal unit markers include `N`, `N-mm`, `MPa`, `mm`, `mm2` through `mm6`,
the M3 inertia-determinant unit `mm8`, `deg`, `s`, `kg/m3`, and the explicit
dimensionless marker `1`. Unit conversion remains at the IO boundary; trace
storage performs no hidden conversion and does not accept aliases such as
`kN`, `KN`, or `kNewton`.

NaN and positive/negative infinity are rejected. A calculation unable to
produce a finite result must preserve an explicit failed, unsupported,
not-applicable, or invalid-input state instead of placing a non-finite scalar
in a completed trace.

## References

`EquationReference` distinguishes standard, mechanics, software, and other
sources. A standard reference requires a paired `standard_id` and positive
edition and can additionally carry clause and equation identifiers. Generic
infrastructure contains no hard-coded AISI reference and no normative equation.
M7 reuses this generic object from outside the results package. Its clause-level
S100-24 references include the registered primary source ID and SHA-256 in
`notes`; no duplicate normative-reference class was introduced.

M7 applicability checks are not calculation steps and do not fabricate empty
calculation traces. M8B reuses their eligibility conclusion and diagnostics
when constructing an EWM compression trace, while reports continue to consume
stored records only.

## M8B EWM compression trace

A completed M8B trace records normative identity and PDF hash, member and
independent global/`Lm` lengths, the coherent M3 property set, prescribed
elastic constants, material strengths, Appendix 2 global quantities, E2,
explicit AISI dimensions, identified plate calculations, `Ae`, E3.1,
analytical E4 where applicable, all candidates, E1 governing selection,
`phi_c`, and `phi_c Pn`. Each normative step carries exact clause/equation or
table identity.

When `S10024-A1-1_3A-XREF-001` is actually used, a separate non-standard
reference records the published and interpreted cross-references, rationale,
corroboration, no-hole restriction, decision metadata, and supersession rule.
Blocked and failed calculations contain diagnostics and no claimed strength.

## Diagnostics and metadata

`EngineeringDiagnostic` preserves `INFO`, `WARNING`, or `ERROR`, a stable code,
message, and immutable flat context entries. `MetadataEntry` stores simple
JSON-friendly provenance scalars such as project, software, catalog, or future
external-engine versions without embedding live runtime state.

The complete resolved-input snapshot remains the authority for full member,
material, section, catalog, YAML, and ETABS inputs. A trace records only the
identifiers, values, references, and provenance relevant to the calculation;
it does not duplicate `ResolvedMember`.

## Report boundary

Reports and calculation memories will consume `CalculationTrace` and result
objects. They may format or round stored values for presentation, but they must
not reconstruct equations, recompute resistance/utilization, or inspect design
engines to reproduce a result. M6 includes an architectural dependency test
that prevents `reports` from importing mechanics, design, stability, or
workflow layers.

See `docs/14_RESULT_INFRASTRUCTURE_M6.md` for the result aggregates and exact M6
limitations.
