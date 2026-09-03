# Validation Plan

Engineering validation is first-class functionality and will proceed in four
levels.

## Level 1 — Unit tests

Test individual equations, geometry/property calculations, unit conversions,
and validation rules with traceable references.

## Level 2 — Mechanics and pyCUFSM benchmarks

Verify geometry translation, signature curves, critical elastic results, mode
outputs, and adapter normalization against trusted independent benchmarks.

## Level 3 — AISI design examples

Verify complete EWM and DSM workflows against independently checked examples
appropriate to the implemented standard. Older-edition examples may be used
only after documenting relevant normative differences.

## Level 4 — End-to-end regression

Exercise project configuration, catalogs, ETABS import, resolution, design,
comparison, and results together. Preserve approved numerical baselines and
explain engineering reasons before changing them.

Current M0-M5 tests cover package installation, immutable domain construction,
catalog contract/loading validation, exact straight-segment integration, the
two illustrative sharp-corner catalog sections, and mechanics invariants for
translation, mirroring, and dimensional scaling.

The M3A mechanics benchmarks are intentionally independent of AISI design:

- a straight strip checks area, centroid, inertia, section modulus, radii, and
  open-wall `J` behavior against analytical values;
- symmetric C geometry checks `y_bar = 0` and `Ixy = 0` without hard-coding
  symmetry in the engine;
- translation checks centroidal-inertia invariance;
- mirror checks `x_bar` and `Ixy` signs and swaps positive/negative y-axis
  section moduli;
- uniform scaling checks the expected powers for area, inertia, section
  modulus, `J`, and radii;
- both approved inactive catalog examples are reproduced and pass a strict
  explicit verification policy.

The M3A subset does not validate shear center, `Cw`, curved bends, AISI
provisions, member resistance, pyCUFSM, or complete design workflows.

M3B adds independently derived rational benchmarks for a straight strip, a
symmetric unlipped channel, and the illustrative lipped C200 geometry. The
tests verify raw sectorial accumulation, `Iomega_x/Iomega_y`, the signed shear
center, area-mean normalization, `Cw`, connected traversal, degeneracy,
immutability, translation, mirroring, and sixth-power scaling. These are
section-mechanics validations only; future comparison with
`pycufsm.pre.cutwp.prop2` remains separate and pyCUFSM is not installed.

M4 adds native-workbook integration and IO-boundary validation. Tests verify
the approved 24 force rows and source hashes, Program Control metadata without
license exposure, authoritative force-table units, exact `m`, `kgf`, and
`kgf-m` conversions, compression-positive axial sign, preservation of all
other CSI local signs, deterministic row provenance, Output Case grouping,
stations, `Before`/`After`, mapping priority, disabled/unknown mappings, and
duplicate or ambiguous mapping failures. Corrupt-workbook cases use temporary
copies. No response-spectrum negative state or component envelope is created.

M5 adds typed YAML and Members workbook validation, deterministic root-relative
paths, catalog-reference and activity QA, once-per-section M3 verification,
complete active-member resolution, input hashes, and end-to-end reuse of the
M2/M3/M4 public boundaries. Exact cardinal and arbitrary-angle cases validate
the signed ETABS 2/3 to section x/y rotation, invariants, source-state
traceability, and preservation of all stations and `Before`/`After` rows.
Tests also distinguish an active member with no mapped demands from unrelated
extra ETABS rows and exercise both warning and error verification policies.

M6 adds infrastructure-only tests for finite explicitly unitized values,
dimensionless identity, references, deterministic trace/step identifiers,
step/trace hierarchy, immutable diagnostics and metadata, separate result
statuses, optional result fields, method/member/comparison aggregation, JSON-
friendly dataclass trees, public API, and forbidden report dependencies. The
neutral arithmetic examples record precomputed values; the result layer does
not execute their documentation expressions.

M7 adds tests for the real local standard registry and SHA-256 fingerprints,
missing/ambiguous primary detection, secondary-source roles, future-scope
isolation, immutable applicability/support models, deterministic IDs, all four
required eligibility combinations, and the explicit v0.1 capability matrix.
An M5-shaped temporary copy of the five approved inputs resolves a real member
through M7 and confirms that unavailable normative facts produce
`INDETERMINATE` while supported software geometry remains a separate result.

Architectural tests prohibit runtime PDF and pyCUFSM imports, dependencies from
normative code into IO/catalog/mechanics, and design-strength equation
identifiers in M7. These tests establish infrastructure behavior only; they do
not validate resistance.

M7 is not an end-to-end design validation: governing-demand selection,
EWM/DSM resistance, authorized AISI equation benchmarks, and pyCUFSM benchmarks
remain future levels.

M8 first completed the primary-source mapping audit for E1, E2, E3.1,
applicable E4, Appendix 1, Appendix 2, and Table B4.1-1. M8A then provided the
versioned dimensional and mechanics-authority contracts without populating
illustrative production rows. M8B now adds direct branch and domain tests, two
complete synthetic C-section benchmarks, governing and non-governing E4 cases,
length/material/symmetry sanity checks, structured failure regressions, a
production-block regression, exact-reference trace audits, and dependency
guards. Results and the equation audit are recorded in
`docs/18_EWM_COMPRESSION_VALIDATION_M8.md`.

M8A.1 adds project-scope and explicit `Lm` contract tests. M8A.2 adds material
schema 0.1/0.2 compatibility, exact keys/references, controlled A3 routes and
states, required provenance, route-specific completeness, formula rejection,
M7 qualified/unqualified/missing behavior, immutable design-input assembly,
coherent M3 property authority, QA blocking, CAPACITY without member demands,
and DEMAND_CHECK with and without the preserved M4/M5 pair. M8B preserves those
boundaries and adds resistance benchmarks only through controlled synthetic
fixtures.
