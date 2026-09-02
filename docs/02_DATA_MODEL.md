# Domain Model

Milestone 1 implements the shared, immutable input domain used by both future
EWM and DSM engines. The model accepts already constructed Python values; it
does not read Excel/YAML, normalize ETABS data, resolve files, or calculate a
design result.

## Relationships

```text
Project
├── ProjectMetadata
├── DesignContext
└── tuple[MemberCase, ...]
    ├── section_id ───────────────┐
    ├── material_id ──────────────┼── future resolver
    ├── MemberGeometry            │
    └── Restraints                │
                                  ▼
                            ResolvedMember
                            ├── MemberCase
                            ├── ResolvedSection
                            │   ├── CatalogSection
                            │   ├── SectionGeometry
                            │   └── SectionProperties
                            ├── Material
                            └── DemandSet
                                └── tuple[DemandCombination, ...]
                                    └── tuple[DemandPoint, ...]
```

One `MemberCase` is one physical member, not a load combination. It contains
only catalog references, member length/orientation information, restraints,
and project metadata. It does not duplicate material values, section geometry,
or section properties.

`Project` also owns immutable `AISIProjectScopeEvidence`. This keeps project
design-basis declarations separate from `DesignContext` method selection and
from material-specific qualification data.

`ResolvedMember` is the common future design input. It verifies that a member's
section and material identifiers match its resolved objects. In M5 it retains
the normalized M4 source demands and the one-to-one section-axis demands. No
separate `EWMMember` or `DSMMember` exists.

## Implemented modules and value objects

- `enums.py`: `MemberType`, `SectionFamily`, `GeometryConvention`,
  `LengthDefinition`, `DesignFormat`, `DesignMethod`, and `RunMode`.
- `project.py`: `ProjectMetadata` and `Project`.
- `scope.py`: three-state, provenance-bearing project scope declarations and
  controlled S100-24 country/application identities.
- `design_context.py`: selected standard metadata, format, methods, run mode,
  and canonical unit-system identifier.
- `material.py`: catalog material values and derived isotropic `g_mpa`.
- `section.py`: `CatalogSection`, mechanical `SectionGeometry`, supplied
  `SectionProperties`, and explicit edition-keyed `StandardSectionDimensions`.
- `member.py`: `MemberGeometry`, `Restraints`, and `MemberCase`.
- `demand.py`: normalized `DemandPoint`, `DemandCombination`, and `DemandSet`.
- `section_demand.py`: section-axis `SectionDemandPoint`, combination, and set.
- `resolved.py`: `ResolvedSection` and `ResolvedMember` aggregations.

Principal types are available directly from `cfs_design.domain`.

## Calculation records and results

M6 adds a separate shared `cfs_design.results` layer. These are outputs from
future mechanics/design services rather than unresolved input-domain objects:

```text
EngineeringValue + EquationReference + EngineeringDiagnostic
    -> CalculationStep[]
    -> CalculationTrace
    -> LimitStateResult[]
    -> MethodDesignResult[]
    -> MemberDesignResult

EWM MethodDesignResult + DSM MethodDesignResult
    -> ComparisonResult
```

`LimitStateId` is an extensible uppercase value object, not a speculative list
of AISI provisions. Execution, applicability, and design pass/fail statuses are
separate types. Optional engineering fields remain `None` until a future
engine calculates them; M6 never substitutes zeros.

Result collections are frozen tuples. Metadata is a flat tuple of typed,
JSON-friendly entries. A trace carries only calculation-relevant identifiers,
values, references, and provenance rather than copying an entire
`ResolvedMember`. Governing fields are optional storage only and have no M6
selection logic.

## Applicability and eligibility records

M7 adds a separate `cfs_design.normative` layer rather than adding AISI state
to `ResolvedMember` or creating EWM/DSM-specific member models:

```text
ApplicabilityCheck[] -> NormativeApplicabilityResult
SoftwareSupportCheck[] -> SoftwareSupportResult
both -> DesignEligibility
```

The normative result uses the existing M6 `ApplicabilityStatus` with the added
`INDETERMINATE` state and derives its unique M6 `EquationReference` values.
Software support has its own `SoftwareSupportStatus`, so `UNSUPPORTED` and
`INVALID_INPUT` cannot be confused with an AISI conclusion. `DesignAction` is
explicit and is not inferred from force magnitudes. All M7 records are frozen,
slotted, tuple-based, and preserve simple scalar observations and structured
diagnostics.

## Catalog boundary

Milestone 2 connects the approved catalog contracts to the M1 domain without
introducing Excel knowledge downstream:

```text
materials_catalog.xlsx                 sections_catalog.xlsx
        |                                      |
        v                                      v
load_material_catalog()                load_section_catalog()
        |                                      |
        v                                      v
 MaterialCatalog                       SectionCatalog
        |                                      |
        +------------------+-------------------+
                           v
                    CatalogRegistry
                    |             |
                    v             v
                 Material   ResolvedSection
```

`CatalogMetadata`, `CatalogSource`, `MaterialCatalog`, `SectionCatalog`, and
`CatalogRegistry` are catalog-layer objects rather than duplicated engineering
domain models. The registry returns the same M1 `Material` and
`ResolvedSection` values that future project resolution and design workflows
will consume. Section schema `0.2.0` additionally exposes exact-key
`StandardSectionDimensions`; legacy `0.1.0` resolves with an empty tuple.

## Immutability and identity

Domain classes are frozen, slotted dataclasses. Domain collections use tuples,
and duplicate member, combination, or demand-point identifiers are rejected at
the collection boundary. Equality is value-based through dataclass semantics.

Required identifiers and labels must be non-blank. Numeric values must be
finite. Intrinsic physical quantities such as material strengths, elastic
modulus, physical lengths, section area/inertias/moduli, radii of gyration, and
torsion constant must be positive where required.

## Length definitions

`MemberGeometry` supports exactly one of two complete definitions:

```text
K_FACTORS:        L + Kx + Ky + Kt
EFFECTIVE_LENGTHS: L + Lx + Ly + Lt
```

Supplying fields from both modes or omitting a required value is invalid. The
object does not convert `K * L` into effective lengths and does not calculate
Euler or AISI buckling; normalization belongs to a later resolver/service.

`Restraints.distortional_unbraced_length_mm` is the explicit future AISI `Lm`
input. It is optional as a member-contract field, but when supplied it must be
positive and paired with `distortional_restraint_source`. It is independent of
`lb_mm`, lateral brace spacing, and the translation/torsion/warping flags.

## Section separation

`CatalogSection` is identity only. `SectionGeometry` preserves the dimensions
needed for future deterministic geometry work. `SectionProperties` preserves
catalog-supplied properties. `ResolvedSection` checks identifiers and family
consistency but never recalculates or overwrites catalog values.

`StandardSectionDimensions` is a separate immutable value keyed by
`(geometry_id, standard_id, standard_edition)` with a source ID. It holds
explicit AISI flat, out-to-out, and overall dimensions. It never derives them
from `SectionGeometry`, including for zero inside radius, and M3 never consumes
it. Missing standard dimensions are represented by absence, not zeros.

Optional catalog fields remain optional in the domain where the approved
contract permits them. In particular, inactive illustrative rows may omit
warping and shear-center values. M3A now keeps the supplied object separate
from immutable `ComputedSectionProperties` and `CatalogVerificationResult`
mechanics values; it does not add calculated fields to this domain model.

## Demand meaning and units

A `DemandPoint` is one physically simultaneous state in canonical internal SI
units:

- forces: N;
- moments and torque: N·mm;
- stations: mm.

Positive, negative, and zero components are retained without structural sign
interpretation:

```text
ETABS native values and signs
    -> future ETABSImporter validation/conversion
    -> normalized DemandPoint
```

The domain does not read source units, parse ETABS, hard-code ETABS sign rules,
create component-wise envelopes, or select a governing point. M5 creates one
section-axis state from each M4 source point and preserves both representations
in `ResolvedMember`.

## Project resolution

`ResolvedProject` is a workflow aggregation rather than a second engineering
domain model. It preserves the typed `ProjectConfig`, complete `Project`, M2
registry, active `ResolvedMember` values, per-section M3 verification results,
complete M4 import result, diagnostics, and reproducibility provenance. M8A
also adds one `ResolvedSectionMechanics` per mechanically resolved active
section. That bundle contains the complete M3A gross and M3B advanced objects,
its catalog comparison, and an explicit `design_use_permitted` QA gate.
It also preserves the exact `AISIProjectScopeEvidence` and member restraint
values loaded at the IO boundary.

Future design reads only that coherent M3 bundle. `ResolvedSection.properties`
remains available as the independent catalog QA/reference record; no mixed
catalog/computed design-property object exists.

Inactive `MemberCase` values remain in `Project.members`; only active rows enter
`ResolvedProject.resolved_members`. The section-axis demand types are shared
by all future methods and do not contain applicability, governing, resistance,
or utilization results.

## Validation boundary

M1 validates intrinsic construction only: required identity, numeric ranges,
complete/noncontradictory length modes, unique collection identifiers, and
referential consistency inside resolved objects.

It deliberately does not determine AISI applicability or v0.1 software
support inside the domain itself. M7 consumes valid resolved values to perform
those separate evaluations. Catalog activity/verification, ETABS mapping
quality, governing demand, resistance, utilization, buckling, effective width,
and design status remain outside intrinsic domain construction.
