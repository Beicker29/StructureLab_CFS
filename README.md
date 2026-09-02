# StructureLab_CFS

StructureLab_CFS is a Python project intended to provide auditable,
reproducible cold-formed steel member design workflows. The approved v0.1
target is ANSI/SDI AISI S100-24 LRFD for catalogued lipped and unlipped C
sections under axial compression and strong-axis flexure.

> **Development warning:** M8A-M8A.2 provide versioned S100-24 dimensional,
> scope, material-qualification, and design-input contracts, but production
> qualification/dimension evidence remains absent. The package does not
> calculate or select a governing demand, resistance, utilization, effective
> width, or elastic buckling. It is not suitable for engineering use.

## Planned design architecture

Two independent future routes will consume the same resolved material,
section, member, restraints, and demand objects:

- Effective Width Method (EWM), implemented from authorized AISI S100-24
  provisions.
- Direct Strength Method (DSM), consuming normalized elastic buckling results
  from a dedicated pyCUFSM adapter.

Comparison mode will present EWM and DSM results without allowing either
design engine to use the other engine's resistance. pyCUFSM will be an elastic
buckling analysis dependency only; it will not provide final member design
resistance.

## Approved v0.1 scope

- Catalogued lipped and unlipped C sections.
- Catalogued isotropic cold-formed steel materials.
- LRFD under ANSI/SDI AISI S100-24.
- Axial compression and strong-axis flexure.
- Global, local, and distortional buckling where applicable.
- Native ETABS Excel demands with multiple members, combinations, stations,
  and simultaneous demand points.
- EWM, DSM, and EWM/DSM comparison results with calculation traces.

Shear, P-M interaction, openings, built-up members, connections, web
crippling, seismic system design, arbitrary sections, load-combination
generation, SAP2000 import, and GUI/web development are outside v0.1.

## Installation

Python 3.10 or newer is required.

```bash
python -m venv .venv
python -m pip install -e .
```

For development and contract smoke tests, install the small optional test set:

```bash
python -m pip install -e ".[test]"
pytest
```

pyCUFSM is deliberately not an M8 dependency.

## Repository architecture

- `data/catalogs/`: authoritative material and section catalogs loaded through
  the M2 catalog boundary.
- `projects/`: project-specific member definitions, native ETABS exports, and
  configuration.
- `src/cfs_design/`: core infrastructure, the shared domain model, catalog
  loading/validation, M3A/M3B section mechanics, the M4 ETABS IO boundary, M5
  project resolution, shared M6 results/traces, M7 normative eligibility, and
  reserved stability, design, and report boundaries.
- `validation/`: future benchmarks and independently verified examples.
- `tests/`: automated package and data-contract tests.
- `docs/`: scope, architecture, schemas, validation, and roadmap decisions.

Dependencies point from IO and orchestration toward domain and engineering
layers. Design and mechanics code must never read Excel directly. Reports will
consume result and trace objects and will never recalculate engineering values.

## Implemented M3A mechanics

The public `cfs_design.mechanics.sections` API provides one immutable
`CenterlineSection`, analytical thin-wall gross properties, and preserved
catalog comparisons. The implemented geometry support is intentionally narrow:

- `C_LIPPED` and `C_UNLIPPED` with all component dimensions explicit;
- `MIDLINE` interpreted as straight centerline lengths between sharp vertices;
- `Ri_mm = 0` and orthogonal web/flange/lip geometry only.

`OUT_TO_OUT`, `FLAT_WIDTHS`, nonzero radii, and nonorthogonal angle conversions
raise `UnsupportedFeatureError` because their dimensional transformations are
not yet defined by the approved contract. See
[M3A Section Geometry and Gross Properties](docs/10_SECTION_MECHANICS_M3A.md)
for the exact datum, signs, formulas, extreme-fiber rule, and limitations.

## Implemented M3B mechanics

M3B reuses the same `CenterlineSection` and the M3A gross result to calculate
signed centroid-relative shear-center offsets, exact sectorial coordinates,
and zero-area-mean warping constant `Cw`. Catalog verification can optionally
compare `x0`, `y0`, and `Cw` while preserving missing values as `NOT_CHECKED`.
See [M3B Shear Center and Warping Constant](docs/11_SECTION_MECHANICS_M3B.md)
for the equations, traversal, sign convention, analytical benchmarks, and
limitations.

## Implemented M4 ETABS import

The `cfs_design.io.etabs` API reads the approved native ETABS workbook,
preserves immutable raw rows and workbook provenance, validates the force-table
unit row, and normalizes demands to `mm`, `N`, and `N-mm`. Axial force is
compression-positive internally; all other force and moment signs remain in
the CSI local convention. Exact `Unique Name` then `Story + Beam` mapping groups
all stations by Output Case without component envelopes. Unmapped rows remain
visible. See [ETABS Import Contract](docs/04_ETABS_IMPORT_SCHEMA.md) and
[M4 Technical Note](docs/12_ETABS_IMPORT_M4.md).

## Implemented M5 project resolution

The `cfs_design.io.project` API loads schema-v0.1 YAML and member workbooks into
typed immutable values. The `cfs_design.workflows.project` API resolves active
catalog references, applies configured M3 verification once per unique active
section, preserves one coherent M3A/M3B property bundle with a design-use QA
gate, reuses the M4 importer, and produces a provenance-rich
`ResolvedProject`. Each simultaneous ETABS 2/3 demand state is rotated once to
section x/y using the member's signed `orientation_deg`; source and transformed
states are both retained and no envelope or governing selection is performed.
See [M5 Project Loading and Resolution](docs/13_PROJECT_RESOLUTION_M5.md).

## Implemented M6 trace and result infrastructure

The public `cfs_design.results` package stores finite `EngineeringValue`
scalars with controlled explicit units, documentary equation references,
structured diagnostics, calculation steps/traces, and generic limit-state,
method, member, and comparison results. Execution, applicability, and design
check statuses remain distinct. All records are frozen and serialization-ready;
expressions are never evaluated and governing fields are never selected by M6.
See [Calculation Trace](docs/08_CALCULATION_TRACE.md) and
[M6 Result Infrastructure](docs/14_RESULT_INFRASTRUCTURE_M6.md).

## Implemented M7 applicability infrastructure

The public `cfs_design.normative` package registers and validates the local
ANSI/SDI AISI S100-2024 source fingerprint, evaluates only verified
clause-level conditions available from resolved inputs, and independently
checks the approved v0.1 software envelope. `DesignEligibility` permits later
execution only when normative applicability is `APPLICABLE` and software
support is `SUPPORTED`.

Missing jurisdiction, forming/use facts, an explicit matching B4.1 dimensional
record, or a required Chapter F load-plane fact remains `INDETERMINATE`; M7
never invents a conversion or proxy. The PDFs are development authorities, not runtime rule
engines. See [M7 Normative Map](docs/15_AISI_NORMATIVE_MAP_M7.md) and
[M7 Applicability](docs/16_APPLICABILITY_M7.md).

## Implemented M8A-M8A.2 input readiness — stopped before resistance

Section-catalog schema `0.2.0` adds a separate `AISI_Dimensions` worksheet and
immutable edition-keyed records; schema `0.1.0` remains readable. No value is
derived from `MIDLINE`, and no illustrative dimension was fabricated. M7 can
evaluate B4.1 from an explicit record and otherwise stays indeterminate.

M5 exposes M3A/M3B as one coherent future design-property set behind the
catalog-verification QA gate. The normative layer centralizes S100-24's
prescribed `E`, `G`, and `mu` without overwriting material data. A complete
future lipped-C axial EWM result must include E4. Project-level A1.1/A1.2.3
evidence and explicit member `Lm` are typed without inferred production facts.

M8A.2 adds edition-keyed material qualification evidence and an immutable
`MemberDesignInput` that references one coherent M3 mechanics set behind its
QA gate. Pure CAPACITY support no longer requires ETABS demands; DEMAND_CHECK
still requires the preserved M4/M5 pair. The production material workbook is
now schema `0.2.0` with a header-only 25-column qualification sheet; no
production qualification evidence was fabricated.

No resistance, effective width, buckling force, utilization, DSM, or pyCUFSM
integration is implemented. See [M8A Dimensional Contract](docs/19_AISI_DIMENSIONAL_CONTRACT_M8A.md),
[M8A.2 Material Qualification](docs/21_AISI_MATERIAL_QUALIFICATION_M8A2.md),
[M8A.2 Design Input](docs/22_DESIGN_INPUT_BOUNDARY_M8A2.md), and the historical
[M8 Normative Map](docs/17_EWM_COMPRESSION_NORMATIVE_MAP_M8.md).

## Validation philosophy

Engineering validation is planned in four levels: focused equation/unit tests,
mechanics and pyCUFSM benchmarks, independently verified AISI examples, and
end-to-end regression. Numerical execution alone will not constitute
validation. Unsupported or inapplicable cases will return explicit statuses
rather than forced resistance values.

## Development guidance

All contributions must follow [AGENTS.md](AGENTS.md), preserve the approved
input contracts, cite authorized normative references when engineering work
begins, and include proportionate tests. Future milestones must not be started
implicitly.
