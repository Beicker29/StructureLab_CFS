# Changelog

All notable changes to this project will be documented in this file.

The project is in pre-release development. Version labels describe software
development status and do not indicate engineering validation or approval for
design use.

## [0.1.0.dev0] - Unreleased

### Added

- Milestone 0 repository and `src/`-layout package foundation.
- Base exception hierarchy and canonical-SI unit policy marker.
- Documentation, test configuration, contract smoke tests, and CI foundation.
- Milestone 1 immutable shared domain objects for project context, materials,
  sections, members, restraints, normalized demands, and resolved inputs.
- Intrinsic domain validation and public `cfs_design.domain` API.
- Milestone 2 schema-v0.1 catalog loaders, contextual parsing, traceable catalog
  metadata, cross-reference validation, immutable containers, and registry.
- Public `cfs_design.catalogs` API returning `Material` and `ResolvedSection`.
- Milestone 3A canonical immutable centerline geometry for explicitly
  dimensioned, orthogonal, sharp-corner lipped and unlipped C sections.
- Analytical thin-wall gross properties `A`, centroid, `Ix`, `Iy`, `Ixy`,
  principal properties, elastic section moduli, radii of gyration, and `J`.
- Immutable computed-property and catalog-verification results with explicit
  configurable PASS/WARNING/FAIL/NOT_CHECKED policy.
- Independent straight-strip, symmetry, translation, mirror, scaling, and
  approved-catalog mechanics benchmarks.
- Milestone 3B exact sectorial-coordinate accumulation over the existing M3A
  centerline, signed centroid-relative shear-center offsets, mandatory
  zero-area-mean normalization, and analytical warping constant `Cw`.
- Immutable advanced/sectorial result objects and optional catalog verification
  for `x0`, `y0`, and `Cw` without replacing missing catalog values.
- Independent rational straight-strip, unlipped-channel, and lipped-channel
  benchmarks plus M3B translation, mirror, scaling, and degeneracy tests.
- Milestone 4 read-only native ETABS force-table parser with immutable raw rows,
  program/workbook metadata, exact row provenance, and explicit schema errors.
- Central IO-boundary conversions from `m`, `kgf`, and `kgf-m` to canonical
  `mm`, `N`, and `N-mm`, including compression-positive axial normalization
  while preserving all other CSI local signs.
- Isolated `ETABS_Mapping` loader with exact Unique Name / Story + Beam
  priority, ambiguity validation, disabled-row preservation, and explicit
  unmapped results.
- Output Case grouping into shared-domain `DemandSet` objects while preserving
  every station, step, element, and `Before`/`After` row without envelopes.
- Milestone 5 typed schema-v0.1 project YAML and Members workbook loaders with
  deterministic repository-root-relative path resolution and SHA-256
  provenance.
- Active-member catalog resolution through the M2 registry and configured M3
  catalog verification once per unique active section, with explicit
  diagnostics and error/warning policy.
- Immutable section-axis demand objects and one authoritative signed ETABS
  local 2/3 to section x/y transformation that preserves every simultaneous
  force state and its source identity.
- Common `ResolvedProject` and enhanced `ResolvedMember` aggregations retaining
  source demands, transformed demands, complete M4 results, QA diagnostics,
  input versions, and hashes without writing calculation outputs.
- Milestone 6 controlled engineering-unit identities and finite immutable
  `EngineeringValue` records with explicit dimensionless representation.
- Generic `EquationReference`, structured engineering diagnostics,
  deterministic trace/step identifiers, and immutable `CalculationStep` /
  `CalculationTrace` records whose expressions are documentation only.
- Separate calculation-execution, applicability, and design-check statuses to
  avoid collapsing failed calculations, unsupported cases, and design FAIL.
- Generic immutable `LimitStateResult`, `MethodDesignResult`,
  `MemberDesignResult`, and `ComparisonResult` containers with optional future
  engineering values, trace reuse, provenance metadata, and no ranking logic.
- Architectural report-boundary test preventing presentation code from
  importing mechanics, design, stability, or workflow engines.
- Milestone 7 immutable standard-document registry with verified local
  S100-24 designation, edition, authority role, repository path, and SHA-256;
  previous and future-scope sources remain isolated.
- Clause-level `ApplicabilityCheck` and `NormativeApplicabilityResult` models
  with conservative APPLICABLE/NOT_APPLICABLE/INDETERMINATE aggregation and
  reuse of the M6 `EquationReference` fingerprint.
- Independent `SoftwareSupportCheck` / `SoftwareSupportResult` models for the
  explicit v0.1 section, format, method, action, geometry, and M4/M5 demand
  envelope, including separate INVALID_INPUT handling.
- `DesignEligibility` gate retaining both reasons and permitting future
  execution only for normative APPLICABLE plus software SUPPORTED.
- Development source validation for missing, ambiguous, unexpected, or
  hash-mismatched standard PDFs without any runtime PDF parser dependency.
- Milestone 8 primary-source equation map and engineering stop record for EWM
  axial compression, identifying the exact S100-24 flat, out-to-out, overall,
  property-authority, elastic-constant, eligibility, and distortional-scope
  decisions required before resistance code may be written.
- Milestone 8A section-catalog schema `0.2.0` with a separate header-only
  production `AISI_Dimensions` contract, explicit provenance, legacy `0.1.0`
  loading, typed standard/edition lookup, and no MIDLINE inference.
- M7 B4.1 ratio evaluation from explicit flat/out-to-out dimensions while
  preserving indeterminate missing data and the conditional EWM `I_s/I_a`
  band.
- Coherent M3A/M3B `ResolvedSectionMechanics` design-property bundle with an
  explicit catalog-verification design-use gate; catalog properties remain QA
  data and are never spliced into that set.
- One immutable traceable source for S100-24 prescribed `E = 203000 MPa`,
  `G = 78000 MPa`, and `mu = 0.30`, separate from catalog materials.
- Formal M8B requirement that a complete lipped-C axial EWM result include E4,
  plus a versioned proposal (not an implementation) for missing A1.1/A1.2.3
  project facts.
- Milestone 8A.1 typed project scope evidence, schema-0.2 member `Lm` fields,
  and an exact equal-flange analytical E4 software gate without dimensional
  conversion or numerical Section 2.2 implementation.
- Milestone 8A.2 immutable `StandardMaterialQualification` evidence keyed by
  material/standard/edition, controlled A3 routes/states, mandatory provenance,
  legacy/current catalog loading, exact registry lookup, and the controlled
  production catalog migration to a header-only 25-field schema-0.2 worksheet.
- M7 material applicability from explicit qualification evidence while
  preserving missing evidence as `INDETERMINATE` and keeping normative failure
  separate from software support.
- Shared immutable `MemberDesignInput` referencing permitted coherent M3
  mechanics, standard dimensions, material qualification, context, scope, and
  eligibility without duplicating engineering values.
- `DesignExecutionPurpose` separation: CAPACITY has no ETABS prerequisite;
  DEMAND_CHECK retains the paired M4/M5 demand/provenance requirement.

### Not implemented

- Curved-bend and ambiguous dimension-convention conversion, governing demand
  selection, calculation-engine population of traces/results, AISI resistance
  equations, EWM/DSM design engines, pyCUFSM integration, serialization, and
  reporting calculations. Normative facts absent from the current domain stay
  explicitly INDETERMINATE. M8B remains stopped and no resistance validation
  benchmark is claimed until trusted dimensions and production qualification
  evidence are approved.
