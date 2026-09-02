# M5 Project Loading and Resolution

Milestone 5 assembles the approved YAML, member workbook, catalogs, and M4
ETABS import into one immutable `ResolvedProject`. It is an orchestration and
coordinate-transformation milestone; it does not calculate resistance,
utilization, governing demand, AISI applicability, EWM, DSM, or elastic
buckling.

## Authoritative flow

```text
project.yaml -> typed ProjectConfig
members.xlsx -> MemberCase values (active and inactive)
catalog workbooks -> M2 CatalogRegistry
ETABS workbook + mapping -> M4 ETABSImportResult
M3 mechanics -> one CatalogVerificationResult per active section
M4 local 2/3 demands -> section x/y demands
all inputs + diagnostics + hashes -> ResolvedProject
```

M5 reuses the M2 catalog API, M3 section mechanics and verification API, and
M4 mapping/import API. It does not duplicate their Excel schemas, conversions,
geometry construction, property equations, or ETABS normalization rules.

## Typed configuration and paths

`load_project_config()` accepts only YAML schema `0.1.0` and returns frozen,
typed values for project identity, design context, files, catalog
verification, ETABS behavior, quality assurance, and output configuration.
Raw nested configuration dictionaries do not cross this boundary.

For the approved v0.1 implementation, the global design selection must be
exactly ANSI/SDI AISI S100-24, LRFD, and SI. The configured run mode must agree
with the selected design methods. Unsupported global selections fail before
engineering data is resolved.

Relative input paths are resolved from the repository root, never from the
process working directory. The root may be supplied explicitly; otherwise it
is discovered deterministically from the configuration location. Paths that
escape that root are rejected. The configured relative path and resolved
absolute path are both preserved. Output paths are resolved but no directory
or result file is created by M5.

## Member loading and activity

The member loader reads the named `Members` and `Metadata` sheets, validates
schema version `0.1.0`, uses named columns, rejects formulas and partial rows,
and constructs the existing immutable `MemberCase`, `MemberGeometry`, and
`Restraints` domain values. Blank rows are ignored; every complete active or
inactive row is preserved. Domain validation remains the authority for length
definitions, member types, orientation, and restraint consistency.

Only active members are resolved for design input. Every active member must
reference an existing active material and existing active section when the
corresponding QA flags require failure. Inactive member definitions remain in
the project snapshot but are not resolved or assigned ETABS demands.

## Catalog verification

Catalog properties are verified once per unique section referenced by active
members, using the M3 engines and the YAML-selected properties and relative
tolerance. Supplied catalog properties and computed values remain separate.
M5 computes and preserves both the complete M3A gross result and M3B advanced
result as one immutable `ResolvedSectionMechanics` bundle.

The approved YAML schema supplies one relative tolerance but no absolute
tolerance. M5 therefore maps it to an M3 `VerificationPolicy` with
`absolute_tolerance = 0.0`; it does not invent an additional dimensional
tolerance. The existing M3 warning band remains authoritative.

Required selected properties that cannot be checked are fatal. Missing
extended properties are retained as explicit `NOT_CHECKED` diagnostics. A
verification failure or unsupported M3 geometry follows
`catalog_verification.action`: `error` stops resolution, while `warning`
preserves a structured warning. M5 never overwrites catalog properties.

The warning action permits project resolution, not automatic design use. A
required verification `FAIL` sets the bundle's `design_use_permitted` gate to
false; `NOT_CHECKED` for a required property remains fatal as before. When
verification is disabled, the computed mechanics bundle is still available
for audit but its design-use gate is false. Future design must request this
coherent M3 bundle and must never fill it with selected catalog values.

## Section-axis demand convention

M4 supplies canonical force states in ETABS local axes 1/2/3. M5 defines
`orientation_deg` as the signed rotation from ETABS local +2 to section local
+x, positive toward ETABS local +3. For
`theta = orientation_deg`, `c = cos(theta)`, and `s = sin(theta)`:

```text
Vx =  V2 c + V3 s
Vy = -V2 s + V3 c
Mx =  M2 c + M3 s
My = -M2 s + M3 c
```

`P` and `T` are unchanged. Forces are stored in N, moments and torque in N-mm,
and stations in mm. Cardinal-angle trigonometric roundoff is cleaned
deterministically, but no force component is enveloped or filtered.

Every source `DemandPoint` produces exactly one immutable
`SectionDemandPoint`. Output Case grouping, point order, station, step,
element, location, and source-point identity are preserved. The common
`ResolvedMember` retains both the source M4 demand set and the transformed
section-axis demand set.

## Mapping QA and diagnostics

`fail_on_unmapped_etabs_member` means that an active project member must have a
mapped demand set. It does not mean that every extra ETABS frame row must match
a project member. Extra or disabled/unmapped ETABS rows remain visible in the
M4 result and are summarized as structured diagnostics.

`ResolvedProject` contains the typed configuration, full `Project`, catalog
registry, active resolved members, section-verification results, complete M4
import result, coherent section-mechanics bundles, structured diagnostics, and
provenance. Provenance includes all
resolved input paths, SHA-256 hashes, schema/catalog versions, ETABS program
version, and package version.

## Explicit limitations

- M5 creates no output files or result folders.
- It does not select a governing demand point or calculate an envelope.
- It does not interpret section-axis forces as design actions.
- It does not determine AISI applicability or software support.
- It does not implement EWM, DSM, pyCUFSM, resistance, utilization, or reports.
- `OUT_TO_OUT`, `FLAT_WIDTHS`, curved bends, and nonorthogonal section geometry
  remain subject to the explicit M3 unsupported behavior.
