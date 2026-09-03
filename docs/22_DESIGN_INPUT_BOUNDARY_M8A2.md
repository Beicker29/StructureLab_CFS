# M8A.2 Design-Execution Input Boundary

## Purpose

M8A.2 creates the shared immutable boundary for future EWM and DSM engines. It
does not calculate resistance or utilization.

```text
ResolvedProject
    -> resolved member definition
    -> require_design_mechanics(section_id)
    -> exact standard dimensions
    -> exact material qualification
    -> normative applicability + software support
    -> MemberDesignInput
```

## MemberDesignInput

The aggregate holds references to:

- `ResolvedMember`;
- one `ResolvedSectionMechanics` containing `gross` and `advanced` M3 results;
- optional exact-key `StandardSectionDimensions`;
- optional exact-key `StandardMaterialQualification`;
- `DesignContext` and `AISIProjectScopeEvidence`;
- requested `DesignMethod`, `DesignAction`, and `DesignExecutionPurpose`;
- the combined `DesignEligibility` result.

It copies no material value, section property, dimension, or evidence record.
Its `executable` flag is the eligibility result, not a calculated capacity.

## Mechanical-property authority and QA

`resolve_member_design_input()` obtains mechanics only through
`ResolvedProject.require_design_mechanics(section_id)`. Therefore future
design code receives the coherent pair:

```text
ResolvedSectionMechanics.gross
+ ResolvedSectionMechanics.advanced
```

`ResolvedSection.properties` remains the catalog QA/reference claim. It is not
substituted for any M3 value. A test deliberately makes catalog area differ
from computed area and verifies that `MemberDesignInput` retains the M3 object.

If `design_use_permitted` is false, `require_design_mechanics()` blocks input
construction. Material qualification and AISI dimensions cannot bypass that
gate.

## Capacity versus demand checking

`DesignExecutionPurpose` has exactly two values:

- `CAPACITY`: evaluates whether resistance inputs are executable and does not
  require ETABS/source/section-axis demands;
- `DEMAND_CHECK`: additionally requires the paired M4 source `DemandSet` and
  M5 `SectionDemandSet`, with point identity and provenance preserved.

The normative result is independent of execution purpose. ETABS presence is a
software workflow condition only.

```text
MemberDesignInput(CAPACITY)
    -> M8B EWM compression capacity engine
    -> one reusable EWMCompressionResistance

MemberResistanceResult + SectionDemandPoint
    -> future demand checker
    -> utilization/result
```

M8B implements the first downstream arrow for EWM axial compression. The
separation permits one capacity result to be reused across multiple
combinations and stations; the demand-check arrow remains unimplemented.

## E4 and current production readiness

The M8A.1 analytical E4 gates are unchanged: equal paired MIDLINE and AISI
dimensions plus explicit sourced `Lm` can be supported; unequal stiffened
flanges remain software `UNSUPPORTED` and point to the unimplemented Appendix
2 Section 2.2 numerical route.

The production project correctly remains non-executable because its scope
evidence is unknown, its material qualification is absent, its AISI dimension
sheet has no production rows, and its production `Lm` cells are blank. M8B
tests use explicitly labeled synthetic evidence for resistance calculations;
production data remains unchanged and blocked.

## Prohibited content

`MemberDesignInput` has no fields for `Fe`, `Fn`, `Pn`, `Mn`, resistance
factors, effective width/area, DSM strength, or utilization. M8A.2 adds no
pyCUFSM dependency or adapter.
