# M7 Applicability, Software Support, and Eligibility

## Independent questions

M7 preserves two conclusions:

```text
ResolvedMember + DesignContext + project scope evidence + DesignMethod + DesignAction
    |                                      |
    v                                      v
NormativeApplicabilityResult       SoftwareSupportResult
    |                                      |
    +---------------+----------------------+
                    v
             DesignEligibility
```

`NormativeApplicabilityResult` answers only whether the verified S100-24 route
can be established. `SoftwareSupportResult` answers only whether the resolved
problem lies inside the approved StructureLab_CFS v0.1 envelope. A software
restriction is never reported as an AISI prohibition.

## Immutable models

`ApplicabilityCheck` records a deterministic ID, topic, normative status,
serialization-friendly observed facts, a short original requirement
paraphrase, one M6 `EquationReference`, and an optional structured diagnostic.
`NormativeApplicabilityResult` aggregates checks and derives its unique
references and diagnostics.

Normative aggregation is conservative:

1. any verified failed condition gives `NOT_APPLICABLE` for the evaluated
   route;
2. otherwise any unresolved condition gives `INDETERMINATE`;
3. otherwise the result is `APPLICABLE`.

`SoftwareSupportCheck` is structurally similar but uses the separate
`SoftwareSupportStatus`: `SUPPORTED`, `UNSUPPORTED`, or `INVALID_INPUT`.
Invalid resolved inputs take precedence over ordinary unsupported capability.

`DesignEligibility.executable` is true only for normative `APPLICABLE` plus
software `SUPPORTED`. Both sub-results and both sets of diagnostics remain in
the combined object. At M7 this is an eligibility gate for later engines, not
a resistance-calculation runner; no EWM or DSM engine is implemented here.

## v0.1 software-support matrix

| Dimension | Supported | Explicitly unsupported |
|---|---|---|
| Section | Catalog `C_LIPPED`, `C_UNLIPPED` | Other families, arbitrary user sections, built-up members, holes/openings |
| Material | Active catalog isotropic material model | Noncatalog or unsupported material models |
| Standard | ANSI/SDI AISI S100-2024 | Other standards or editions |
| Format | LRFD | ASD and unimplemented formats |
| Method | `DesignMethod.EWM`, `DesignMethod.DSM` | Any unapproved method |
| Action | Explicit axial compression for `COLUMN`; explicit strong-axis flexure for `BEAM` | Shear, P-M interaction, connections, web crippling |
| Geometry | Orthogonal, sharp-corner `MIDLINE` C geometry | `FLAT_WIDTHS`, `OUT_TO_OUT`, nonzero radii, nonorthogonal geometry |
| Demand path | CAPACITY without demands; DEMAND_CHECK with paired M4 source and M5 section-axis demands | Direct Excel/design-engine access, SAP2000, generated combinations |
| Systems | Member-level current scope | Seismic-system design |

EWM and DSM are represented as the approved v0.1 method envelope. Their
resistance engines and, for DSM, the future elastic-buckling adapter are still
absent. M7 does not import or run pyCUFSM.

## Strong-axis convention

M7 does not inspect ETABS M2/M3 to guess the strong axis. M5 has already
transformed demands to section x/y. Software support requires resolved x/y
properties to establish aligned principal axes (`Ixy = 0` within the narrow
numeric identity tolerance) and a unique larger `Ix` or `Iy`. The larger
resolved inertia identifies section axis X or Y. A rotated or equal-inertia
case is `UNSUPPORTED` until a separately approved transformation is available.

## Geometry and B4.1 are different checks

The M3 software builder supports only `MIDLINE` sharp orthogonal geometry. The
S100-24 B4.1 table, however, defines limits using flat widths and selected
out-to-out dimensions. Section schema `0.2.0` now carries those values in a
separate `AISI_Dimensions` record. These are different semantics:

- M3 `MIDLINE` support can be `SUPPORTED`;
- the B4.1 dimensional applicability check is evaluable only when a matching
  explicit S100-24 record is resolved; otherwise it remains `INDETERMINATE`.

No M7 function converts among `MIDLINE`, `FLAT_WIDTHS`, and `OUT_TO_OUT`.
For lipped EWM flanges in the conditional `60 < b/t <= 90` band, M7 also
preserves `INDETERMINATE` because M8A does not calculate the `I_s/I_a`
condition. M7 still calculates no resistance.

## Invalid input

M5 normally supplies structurally valid inputs. M7 still reports
`INVALID_INPUT` for an inactive resolved record, a requested method absent
from `DesignContext`, or a member that lacks the paired M4 source and M5
section-axis demand sets. Wrong Python object types raise `ValidationError`
before a normative conclusion is attempted.

## Source and calculation boundaries

`cfs_design.normative.source_validation` may discover files and verify their
SHA-256 hashes during development/audit. Applicability execution imports no PDF
library and reads no standard file. Source validation also rejects a missing or
ambiguous primary PDF and any unregistered standard PDF requiring an authority
role.

M7 calculates no resistance, effective width, buckling strength, utilization,
or governing demand. Reports remain consumers of future stored results and
traces only.

## M8A.1 scope and E4 gates

Project schema `0.2.0` lets M7 evaluate the project-wide A1.1 declarations and
the A1.2.3 country/format condition. `UNKNOWN` remains `INDETERMINATE`; an
explicit failed scope fact becomes `NOT_APPLICABLE` only where the verified
clause supports that conclusion. M8A.2 makes the separate member-material A3
check evaluable from an exact standard/edition record: qualified routes can be
applicable, an explicit sourced failure can be not applicable, and
missing/unknown evidence stays indeterminate.

`DesignExecutionPurpose.CAPACITY` removes only the ETABS software prerequisite.
`DEMAND_CHECK` preserves the approved M4/M5 pair requirement. Normative
applicability does not depend on this software execution purpose.

For `C_LIPPED` EWM axial compression, software support now also requires the
exact equal-flange analytical configuration and explicit `Lm`. Unequal
flanges are `UNSUPPORTED` because the Appendix 2 Section 2.2 numerical route
is not implemented. This never changes normative applicability.

M8B also narrows its global elastic solution to singly symmetric C sections.
For EWM axial compression the software gate therefore requires exact equality
of the paired MIDLINE flange values and, for lipped sections, paired lip
values. This capability conclusion is independent of the normative result and
does not approximate an unequal section.
