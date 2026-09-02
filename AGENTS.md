# AGENTS.md

## 1. Purpose

This file defines the mandatory operating rules for any coding agent working in this repository.

The repository is engineering software for cold-formed steel (CFS) member design. It is intended to be auditable, reproducible, modular, and suitable for professional engineering workflows.

Agents must preserve the approved architecture and engineering intent. They must not make independent changes to engineering scope, design assumptions, normative interpretation, data contracts, or architecture unless the task explicitly authorizes those changes.

The project follows four core principles:

1. **DRY — Don't Repeat Yourself**
2. **Single Source of Truth**
3. **Separation of Responsibilities**
4. **Engineering Traceability**

---

## 2. Approved Project Objective

The repository shall provide two independent AISI design routes using one common definition of material, section, member, restraints, and demands:

### Route A — AISI Effective Width Method (EWM)

AISI-based member design using the Effective Width Method.

### Route B — pyCUFSM + AISI Direct Strength Method (DSM)

pyCUFSM is used only as an elastic buckling / finite-strip analysis engine. Its elastic critical results are passed to the AISI DSM implementation.

pyCUFSM does **not** directly provide the final member design resistance.

### Comparison Mode

The repository shall support:

- EWM only
- DSM only
- EWM + DSM comparison

EWM and DSM must remain independent design engines. Neither method may use the resistance result of the other method.

Both methods must consume the same resolved `Member`, `Section`, `Material`, and `DesignContext`.

---

## 3. Frozen Scope — v0.1

The following scope is approved for v0.1.

### Supported section families

- Lipped C sections
- Unlipped C sections

Only sections contained in the approved section catalog are permitted in v0.1.

User-defined arbitrary sections are out of scope for v0.1.

### Material model

- Isotropic cold-formed steel
- Materials must come from the approved materials catalog

### Design standard

- ANSI/SDI AISI S100-24
- LRFD

The architecture shall remain extensible to future editions and ASD, but v0.1 implementation shall not silently add unsupported standards or design formats.

### Structural actions

v0.1 shall support:

- Axial compression
- Strong-axis flexure

### Buckling / limit-state families

Where applicable to the approved AISI method:

- Global buckling
- Local buckling
- Distortional buckling

### Design methods

- EWM
- DSM using pyCUFSM elastic buckling results
- EWM vs DSM comparison

### Demand source

- ETABS Excel export
- Multiple members
- Multiple load combinations per member
- Multiple stations / demand points per member and combination

### Required outputs

- Results by member
- Results by demand combination / demand point
- Governing demand point
- Governing limit state
- EWM result
- DSM result
- EWM vs DSM comparison
- Calculation trace
- Project summary
- Resolved input snapshot

### Explicitly out of scope for v0.1

Do not implement unless a future task explicitly expands the approved scope:

- Shear design
- P-M interaction
- Openings / holes
- Built-up members
- Connections
- Web crippling
- Seismic system design
- Arbitrary user-defined sections
- Automatic generation of structural load combinations
- SAP2000 import
- GUI / web application
- Excel as a calculation engine

---

## 4. Mandatory Architecture Principles

### 4.1 DRY

A material property, section property, normative equation, conversion rule, engineering result, or validation rule must have one authoritative implementation.

Do not duplicate:

- AISI equations
- resistance factors
- unit conversions
- section geometry definitions
- material definitions
- member definitions
- ETABS normalization logic
- report calculations

If two modules need the same engineering operation, move the operation to the appropriate shared layer instead of copying it.

---

### 4.2 Single Source of Truth

Materials and sections are defined in master catalogs.

Members reference catalog objects through IDs.

A `MemberCase` shall reference:

- `section_id`
- `material_id`

It shall not duplicate catalog values such as:

- `Fy`
- `Fu`
- `E`
- `Ix`
- `Iy`
- `A`
- `J`
- `Cw`

EWM and DSM must consume the same resolved objects.

---

### 4.3 Separation of Responsibilities

The repository shall maintain clear boundaries between:

- input/output
- catalogs
- domain models
- mechanics
- stability analysis
- normative design
- workflows
- validation
- reports

Engineering calculation modules must not know how Excel files are stored.

Reports must not know how AISI equations are implemented.

pyCUFSM-specific code must not spread throughout the repository.

---

### 4.4 Reports Never Recalculate

Reports are presentation layers.

A report may:

- read result objects
- read calculation traces
- format values
- create tables
- create figures
- create a calculation memory

A report must never independently recompute engineering resistance, buckling values, utilization, effective widths, or AISI equations.

The flow is:

`calculation -> result / CalculationTrace -> report`

Never:

`calculation -> report -> second calculation`

---

## 5. Approved Data Contracts

The approved project input files are:

1. `materials_catalog.xlsx`
2. `sections_catalog.xlsx`
3. `members.xlsx`
4. `ETABS_results.xlsx`
5. `project.yaml`

These files are data contracts.

Agents must not rename sheets, rename required fields, change field meaning, change units, or restructure these files without explicit approval.

Schema versioning must be respected.

Backward-incompatible schema changes require a deliberate schema-version change and migration plan.

---

## 6. Materials Catalog Rules

`materials_catalog.xlsx` is the master source of material data.

Primary concepts include:

- material identity
- specification
- grade
- `Fy`
- `Fu`
- `E`
- Poisson ratio
- density
- source/reference
- active status

`G` shall be treated as a derived property unless a future approved requirement states otherwise.

Members may only reference active materials.

Example rows prefixed with `EX_` are illustrative and shall remain inactive unless explicitly converted into verified catalog entries.

---

## 7. Sections Catalog Rules

`sections_catalog.xlsx` separates:

### `Sections`

Section identity:

- `section_id`
- designation
- family
- manufacturer
- `geometry_id`
- source
- active status

### `Geometry`

Physical definition required to reconstruct the section.

The geometry shall be sufficiently explicit to produce a deterministic geometry representation for both:

- EWM
- pyCUFSM geometry generation

### `Properties`

Catalog section properties such as:

- area
- centroid
- moments of inertia
- section moduli
- radii of gyration
- torsion constant
- warping constant
- shear-center information where required

Catalog properties and calculated properties are different concepts.

Do not overwrite catalog values with calculated values.

Instead, preserve both and create a verification result.

---

## 8. Automatic Catalog Verification

The repository shall automatically verify selected catalog properties against values calculated from section geometry.

Conceptually:

`CatalogSection -> GeometryEngine -> ComputedSectionProperties -> CatalogVerificationResult`

The comparison must:

- preserve original catalog values
- preserve computed values
- report absolute and relative differences
- use configurable tolerances
- return explicit PASS / WARNING / FAIL status
- preserve a trace of what was checked

Do not silently replace catalog properties.

The default verification tolerance belongs in project/configuration data and must not be hard-coded inside calculation functions.

---

## 9. Members and Cases

One `MemberCase` represents one physical design member.

It is **not** a load combination.

A member may have many demand combinations and many demand points.

Conceptually:

`Project -> MemberCase -> DemandSet -> DemandCombination -> DemandPoint`

Each member references exactly one section and one material for the current analysis context.

The member model may contain:

- physical length
- effective-length definition
- effective-length factors or explicit effective lengths
- unbraced length
- orientation
- restraints
- bracing information
- metadata

A member type shall be explicit, not inferred from force magnitudes.

Approved conceptual values include:

- `COLUMN`
- `BEAM`
- `BEAM_COLUMN`
- `OTHER`

Support in v0.1 still follows the frozen scope.

---

## 10. ETABS Import Rules

ETABS data arrives through a native Excel export.

The importer shall be isolated from the design engines.

Required flow:

`ETABS Excel -> ETABSImporter -> normalized DemandSet -> MemberCase`

EWM and DSM must never read ETABS Excel directly.

### Mapping

Member mapping belongs in the `ETABS_Mapping` sheet of `members.xlsx`.

Preferred mapping priority:

1. ETABS `Unique Name`
2. ETABS `Story + Beam/Frame label`

The mapping strategy must be configurable and validated.

Unmapped active project members or unexpected ETABS members shall not be silently ignored when the configured QA policy requires failure.

### Native ETABS rows

The importer shall preserve:

- member identity
- output case
- case type
- step type
- station
- force components
- element information
- location information
- source units

### DemandPoint rule

Each ETABS result row representing a physically valid simultaneous force state shall become or contribute to a `DemandPoint`.

The repository must **not** build a component-wise envelope by independently taking maximum `P`, maximum `M`, maximum `V`, etc.

Independent extrema may occur at different stations or steps and must not be combined into a fictitious force state.

The design workflow shall evaluate valid demand points and identify the governing one based on design utilization.

---

## 11. Units

The canonical internal engineering unit system is SI.

Excel/ETABS source units may differ.

All input units must be:

1. read explicitly,
2. validated,
3. converted at the IO/import boundary,
4. normalized before entering engineering calculation modules.

Engineering functions shall not contain hidden unit conversions.

Unknown or ambiguous source units must produce an explicit validation error rather than an assumed conversion.

---

## 12. Domain Model

The architecture shall converge toward explicit domain objects such as:

- `Project`
- `ProjectMetadata`
- `DesignContext`
- `Material`
- `CatalogSection`
- `SectionGeometry`
- `SectionProperties`
- `ResolvedSection`
- `MemberCase`
- `MemberGeometry`
- `Restraints`
- `DemandSet`
- `DemandCombination`
- `DemandPoint`
- `ResolvedMember`
- `ApplicabilityResult`
- `CatalogVerificationResult`
- `EWMResult`
- `DSMResult`
- `ComparisonResult`
- `MemberDesignResult`
- `CalculationTrace`

Names may evolve during implementation only if semantics remain clear and the architectural intent is preserved.

Do not create parallel duplicated data models for EWM and DSM.

---

## 13. Mechanics vs Design

The mechanics layer contains engineering mechanics that are not themselves a full normative workflow.

Examples:

- gross section property calculations
- geometry processing
- elastic buckling utilities
- effective-width mechanics where appropriately factored
- transformations
- stress distributions

The design layer applies normative AISI design provisions.

Do not place project orchestration, Excel reading, report generation, or CLI logic inside mechanics or design equations.

---

## 14. pyCUFSM Boundary

pyCUFSM shall be treated as an external stability-analysis dependency.

All direct pyCUFSM API access must occur through a dedicated adapter layer.

Conceptual flow:

`ResolvedSection / Member -> pyCUFSM Adapter -> pyCUFSM -> ElasticBucklingResult -> DSM`

The adapter is responsible for:

- translating internal geometry to pyCUFSM input
- translating materials/stress state where needed
- selecting/configuring analysis inputs
- converting pyCUFSM outputs into repository domain objects
- preserving pyCUFSM version metadata
- handling pyCUFSM-specific validation/errors

DSM design modules shall consume normalized elastic buckling results, not raw pyCUFSM dictionaries/arrays.

Do not vendor, fork, or copy pyCUFSM source into this repository unless explicitly approved.

---

## 15. Normative Engineering Rules

The normative implementation target for v0.1 is ANSI/SDI AISI S100-24.

Agents must never invent:

- equations
- coefficients
- resistance factors
- applicability limits
- effective-width expressions
- DSM expressions
- buckling interpretations
- material properties
- section properties

If the required normative source is unavailable or ambiguous:

**STOP the engineering implementation and report the missing or ambiguous reference.**

Do not infer a normative equation from memory when exact implementation is required.

Every normative calculation must be traceable to:

- standard
- edition
- chapter/section/clause where available
- equation identifier where available
- implemented variable definitions

The repository must distinguish:

- **Normative applicability**: whether AISI permits the method for the situation
- **Software support**: whether this repository has implemented and validated that situation

A method can be normatively applicable but software-unsupported.

---

## 16. Applicability Status

Engineering workflows shall use explicit states rather than forcing a numerical result.

Approved conceptual statuses include:

- `SUPPORTED`
- `WARNING`
- `NOT_APPLICABLE`
- `UNSUPPORTED`
- `INVALID_INPUT`

Do not return a resistance value for an unsupported case merely because the underlying function can numerically execute.

---

## 17. CalculationTrace

All important engineering calculations shall be traceable.

A `CalculationTrace` or equivalent structure shall be able to preserve:

- project/member identifier
- method
- limit state
- standard
- edition
- clause/equation reference
- input variables
- intermediate values
- result
- units
- warnings
- software version metadata where relevant

Calculation traces are the source for future calculation-memory generation.

A report must consume traces; it must not recreate them.

---

## 18. Reproducibility

Each completed project run shall preserve enough information to reproduce the result later.

At minimum, preserve:

- resolved member inputs
- material values actually used
- section values actually used
- catalog version/schema version
- project configuration
- standard edition
- design method
- ETABS source metadata
- pyCUFSM version when used
- software/repository version when practical
- warnings and applicability results

Changing a catalog later must not make an old calculation result impossible to audit.

---

## 19. Validation Strategy

Engineering validation is first-class functionality.

The target validation hierarchy is:

### Level 1 — Unit tests

Test individual:

- equations
- geometry calculations
- property calculations
- unit conversions
- validation rules

### Level 2 — Mechanics / pyCUFSM benchmarks

Validate:

- geometry translation
- signature-curve behavior
- critical elastic loads/moments
- mode-related outputs
- adapter normalization

against trusted benchmarks.

### Level 3 — AISI design examples

Validate complete EWM/DSM workflows against independently verified examples appropriate to the implemented standard/provision.

Historical examples based on older AISI editions may be used only when their normative differences are explicitly understood.

### Level 4 — End-to-end regression

Validate:

`Project -> catalogs -> ETABS -> resolver -> design -> comparison -> result`

Regression tests must detect unintended numerical changes.

---

## 20. Testing Rules for Agents

Every engineering change requires tests.

Agents shall run the smallest relevant test set during development and the full applicable suite before declaring completion.

A task is not complete when code merely executes.

A task is complete when:

- intended behavior is implemented
- validation rules are implemented
- tests pass
- no unrelated tests regress
- architecture rules remain satisfied
- documentation is updated when required

Never weaken or delete a failing engineering test solely to make CI pass.

If an approved numerical reference changes, explain the engineering reason before updating the expected result.

---

## 21. External Code and Licensing

Do not copy code from external repositories without verifying:

- license
- compatibility
- attribution requirements
- engineering validity

The repository `AISI_CFS_Design_Functions` or similar external projects may be used as references for ideas, comparison, or independent validation only when legally and technically appropriate.

Do not copy copyrighted AISI manual text, tables, commentary, or examples into the repository beyond what is legally appropriate for references and implementation metadata.

Implement normative equations independently from authorized source material.

---

## 22. Coding Quality

Prefer:

- small focused modules
- explicit types
- immutable/value-style domain objects where practical
- pure engineering functions where practical
- deterministic calculations
- explicit exceptions
- meaningful names
- testable components
- dependency injection / adapters for external systems

Avoid:

- monolithic calculation files
- hidden global state
- circular imports
- magic numbers
- hard-coded file paths
- hard-coded Excel column positions when a named/configured schema exists
- silent fallbacks
- catch-all exception suppression
- engineering calculations inside CLI/report/UI code

Comments should explain engineering intent or non-obvious decisions, not restate obvious code.

---

## 23. Dependency Direction

High-level workflows may depend on domain and engineering services.

Core engineering/domain layers must not depend on:

- Excel
- report generators
- CLI
- project folder layout

A preferred conceptual dependency direction is:

`IO -> Domain -> Mechanics/Stability/Design -> Results -> Reports`

with workflows coordinating these layers.

External dependencies such as pyCUFSM must enter through adapters.

---

## 24. Change Control

Agents must not independently change:

- approved v0.1 scope
- normative standard/edition
- Excel/YAML schemas
- meaning of existing IDs
- canonical unit policy
- ETABS demand-point policy
- architecture boundaries
- DRY rules
- pyCUFSM adapter boundary
- catalog verification philosophy

If a task appears to require such a change:

1. identify the conflict,
2. explain why the approved architecture is insufficient,
3. propose the smallest change,
4. wait for explicit approval before implementing the architectural change.

Refactoring that preserves behavior and architecture is allowed when required by the task and covered by tests.

---

## 25. Required Agent Workflow

For every implementation task:

### Step 1 — Read

Read:

- this `AGENTS.md`
- relevant documentation
- relevant schemas
- existing tests
- nearby implementation

Do not start from assumptions when repository context is available.

### Step 2 — Plan

State or internally establish:

- exact scope
- files likely affected
- architectural layer
- validation required
- tests required
- engineering references required

### Step 3 — Implement One Scope

Keep changes focused.

Do not combine unrelated architecture refactors and engineering features in one change.

### Step 4 — Test

Run:

- new tests
- relevant existing tests
- regression tests affected by the change

### Step 5 — Review

Check:

- DRY
- units
- signs/conventions
- normative traceability
- applicability
- error handling
- backward compatibility
- no report-side recalculation

### Step 6 — Report

At completion summarize:

- what changed
- what did not change
- tests executed
- engineering references used
- warnings/open issues
- any decisions requiring owner approval

---

# 26. Milestone 0 — Repository Foundation

Milestone 0 is infrastructure only.

## M0 may implement

- repository folder structure
- Python package skeleton
- `pyproject.toml`
- test framework configuration
- CI foundation
- lint/format/type-check foundation if approved in the task
- base exceptions
- basic constants infrastructure
- unit infrastructure
- schema placement
- documentation skeleton
- import smoke tests
- package installation smoke tests
- `AGENTS.md`

## M0 must NOT implement

- EWM equations
- DSM equations
- AISI resistance calculations
- effective-width calculations
- pyCUFSM integration
- member resistance
- design utilization
- engineering report calculations

M0 success means the repository is clean, installable, testable, documented, and ready for the domain-model milestone.

---

## 27. Engineering Safety Rule

This repository can influence structural engineering decisions.

Correctness and traceability take priority over speed.

When uncertain:

- do not guess,
- do not silently assume,
- do not fabricate a reference,
- do not force a numerical result.

Raise the uncertainty explicitly and preserve the integrity of the engineering workflow.
