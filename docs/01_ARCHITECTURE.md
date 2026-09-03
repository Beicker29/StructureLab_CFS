# Architecture

## Governing principles

**DRY.** Each engineering equation, conversion, validation rule, material,
section, and result has one authoritative implementation.

**Single source of truth.** Members reference catalog identifiers. EWM and DSM
will consume the same resolved section, material, member, restraint, demand,
and design-context objects.

**Separation of responsibilities.** IO owns file formats, domain objects own
engineering meaning, mechanics owns non-normative mechanics, stability owns
elastic buckling integration, design owns normative provisions, workflows
coordinate services, and reports present completed results.

**Engineering traceability.** Inputs, intermediate values, normative
references, results, units, warnings, and software metadata will be retained in
calculation traces.

## Dependency direction

The preferred direction is:

```text
IO -> Domain -> Mechanics / Stability / Design -> Results -> Reports
                  ^
                  |
              Workflows coordinate
```

Core engineering and domain packages do not depend on Excel, report generators,
CLI code, or project-folder layout. Excel readers will live only at IO/catalog
boundaries.

## M5 project-resolution boundary

M5 coordinates the existing public layers without duplicating them:

```text
typed YAML + member IO + M2 catalogs + M3 verification + M4 ETABS import
    -> active-member resolution
    -> coherent ResolvedSectionMechanics + QA design-use gate
    -> one ETABS-local-to-section-local transformation
    -> ResolvedProject + provenance + structured QA diagnostics
```

The project workflow owns cross-file references, activity policy, section-axis
orientation, and project-level QA. Catalog IO remains in M2, section mechanics
in M3, and native ETABS parsing/mapping/unit normalization in M4. The workflow
does not write outputs, envelope components, select a governing point, or call
design or stability code. Exact behavior is documented in
`docs/13_PROJECT_RESOLUTION_M5.md`.

## M3A section-mechanics boundary

M3A establishes one reusable mechanical geometry and separates catalog claims
from calculations:

```text
SectionGeometry
    -> CenterlineSection
       -> gross-property engine
          -> ComputedSectionProperties

ResolvedSection.properties + ComputedSectionProperties
    -> CatalogVerificationResult
```

The builder is the sole conversion from approved parametric section geometry
to mechanical primitives. The property engine does not regenerate dimensions,
and verification does not recalculate properties. `SectionProperties` remains
the supplied catalog object; computed values never overwrite it.

The mechanics package depends on domain and core only. It contains no Excel,
catalog-loader, ETABS, report, AISI, EWM, DSM, or pyCUFSM imports. Exact M3A
coordinate, `MIDLINE`, bend, and property conventions are documented in
`docs/10_SECTION_MECHANICS_M3A.md`.

## M3B advanced section-mechanics boundary

M3B consumes the existing canonical geometry and the completed M3A gross
result:

```text
CenterlineSection + ComputedSectionProperties
    -> exact sectorial mechanics
    -> AdvancedSectionProperties
       -> x0 / y0 / Cw / normalized sectorial nodes
```

No second section builder exists. M3B uses the ordered M3A contour, rejects
disconnected traversal, and does not recalculate `A`, centroid, `Ix`, `Iy`, or
`Ixy`. Catalog verification may read both result objects but does not invoke
either mechanics engine. Exact signs, equations, normalization, and benchmarks
are documented in `docs/11_SECTION_MECHANICS_M3B.md`.

## pyCUFSM boundary

All future direct pyCUFSM access belongs in one adapter:

```text
ResolvedSection / Member
    -> pyCUFSM adapter
    -> pyCUFSM
    -> normalized ElasticBucklingResult
    -> DSM
```

Raw pyCUFSM structures must not enter DSM. pyCUFSM will not calculate final
member design resistance and is not an M3B dependency.

## Reporting boundary

Reports consume result and `CalculationTrace` objects. They may format values
and figures but never recompute resistance, buckling values, effective widths,
utilization, or normative equations.

## M6 trace/result boundary

M6 inserts one shared immutable result layer between future calculations and
reports:

```text
mechanics / future design engine
    -> already-computed EngineeringValue values
    -> CalculationTrace + LimitStateResult
    -> MethodDesignResult / MemberDesignResult / ComparisonResult
    -> future reports
```

The results package may depend on core unit/validation infrastructure and the
shared `DesignMethod` identity. It does not depend on IO, reports, EWM, DSM,
stability, project orchestration, or pyCUFSM. Expression strings are trace
metadata and are never executable. Reports are guarded against importing
mechanics, design, stability, or workflow layers; they must consume stored
result/trace objects only. See `docs/08_CALCULATION_TRACE.md` and
`docs/14_RESULT_INFRASTRUCTURE_M6.md`.

## M7 normative and eligibility boundary

M7 adds two independent rule paths downstream of the shared M5 input:

```text
ResolvedMember + DesignContext + project scope evidence + requested method/action
    -> S100-24 applicability rules -> NormativeApplicabilityResult
    -> v0.1 capability rules       -> SoftwareSupportResult
    -> DesignEligibility
```

The normative package depends on core, domain, and results. It does not make
IO, catalogs, mechanics, stability, reports, or project resolution depend on
normative logic. `source_validation` is an explicit development/audit utility
that discovers and hashes local files; design eligibility itself reads typed
rules and M6 references and never parses a PDF.

One source registry owns document identities and authority roles. One
applicability implementation owns verified S100-24 rules. One independent
software-support implementation owns the v0.1 capability matrix. The combined
gate never converts `UNSUPPORTED` into AISI `NOT_APPLICABLE`, and it blocks an
`INDETERMINATE` normative case. See `docs/15_AISI_NORMATIVE_MAP_M7.md` and
`docs/16_APPLICABILITY_M7.md`.

## M8A dimensional and design-basis boundary

M8A resolves the approved input architecture without implementing resistance:

```text
Geometry -> CenterlineSection -> M3A/M3B -> ResolvedSectionMechanics
Properties ---------------------------> catalog verification / QA gate
AISI_Dimensions ----------------------> M7 and future normative design

ResolvedMember + permitted coherent M3 bundle + M7 eligibility
    -> M8B EWM global buckling
    -> Appendix 1 effective widths / effective area
    -> E2 / E3.1 / applicable analytical E4 result
    -> M6 trace and generic results
```

Section-catalog schema `0.2.0` adds a separate edition-keyed
`AISI_Dimensions` source. It never changes `SectionGeometry` or M3. M5 exposes
one coherent M3A/M3B property bundle; catalog properties remain QA claims and
required verification failures block design use even when project resolution
continues under warning policy. The S100 normative layer separately owns its
prescribed elastic constants.

The production illustrative catalog deliberately has no dimensional records,
so its M7 B4.1 result remains `INDETERMINATE`.

M8A.1 adds typed, provenance-bearing project evidence for the project-wide
A1.1 facts and A1.2.3 governing country, while leaving material-specific A3
qualification on the material side of the boundary. It also adds explicit
member `Lm` without deriving it from other bracing fields. M7 separately gates
the future analytical E4 route to exact equal-flange data; unequal flanges are
software-unsupported without becoming normatively prohibited. See
`docs/20_SCOPE_AND_DISTORTIONAL_INPUTS_M8A1.md`.

## M8A.2 material and design-execution boundary

Material schema `0.2.0` adds an edition-keyed
`AISI_Material_Qualification` evidence source without duplicating the physical
`Material`. M7 consumes the exact record and keeps missing evidence
`INDETERMINATE`; material qualification remains a normative question, not a
software-support result.

Future EWM and DSM engines receive one immutable `MemberDesignInput` containing
references to the resolved member, permitted coherent M3 mechanics, exact
standard dimensions, exact material qualification, design context, scope
evidence, and eligibility. Construction calls
`ResolvedProject.require_design_mechanics()`; catalog properties cannot enter
the design-property set.

`DesignExecutionPurpose` separates `CAPACITY` from `DEMAND_CHECK`. Capacity
support does not require ETABS demands. Demand checking continues to require
the paired M4 source and M5 section-axis demand sets. M8B consumes the CAPACITY
boundary for axial EWM resistance; utilization remains separate. See
`docs/21_AISI_MATERIAL_QUALIFICATION_M8A2.md` and
`docs/22_DESIGN_INPUT_BOUNDARY_M8A2.md`.

## M8B axial EWM design layer

`cfs_design.design.ewm` consumes no Excel, YAML, ETABS, report, DSM, or
pyCUFSM API. Its public capacity function retains global flexural and coupled
flexural-torsional quantities, E2 and E3.1 results, analytical E4 for eligible
lipped C sections, every nominal candidate, governing E1 selection, LRFD
factor, design strength, diagnostics, and a complete M6 trace. Low-level
equations remain focused module functions and each has one production
implementation. Demand utilization remains separate and unimplemented.
