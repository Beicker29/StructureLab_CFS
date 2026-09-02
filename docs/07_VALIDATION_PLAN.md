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

M8 completed a primary-source mapping audit, not a numerical validation. It
verified the required E1, E2, E3.1, applicable E4, Appendix 1, Appendix 2, and
Table B4.1-1 chain and then activated the milestone stop condition. The current
M8A now provides the versioned typed contract for those dimensional bases but
does not populate the illustrative production sections. Its Level 1 coverage
checks new/legacy schemas, row completeness, keys/references, strict numeric
values, unsupported editions, provenance, no MIDLINE inference, M7 present/
absent behavior, coherent M3 property authority, QA gating, and immutable
normative constants. Consequently, no M8 resistance equation test,
hand-calculated capacity benchmark, or
`docs/18_EWM_COMPRESSION_VALIDATION_M8.md` is claimed. Those artifacts must not
be created until trusted production dimensions, remaining M7 project evidence,
and the M8B equation/benchmark scope in
`docs/19_AISI_DIMENSIONAL_CONTRACT_M8A.md` are satisfied.
