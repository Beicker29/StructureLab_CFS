# Applicability and Software Support

Milestone 7 implements two independent questions:

1. **Normative applicability:** does ANSI/SDI AISI S100-24 permit the method for
   the resolved situation?
2. **Software support:** has this repository implemented and validated that
   permitted situation?

A case may be normatively applicable but not yet supported by the software.
The software must never return a resistance solely because a numerical function
can execute.

Normative applicability uses `APPLICABLE`, `NOT_APPLICABLE`, and
`INDETERMINATE`. Failure of a verified criterion is different from missing
facts: unresolved facts must remain `INDETERMINATE`.

Software support separately uses `SUPPORTED`, `UNSUPPORTED`, and
`INVALID_INPUT`. Warnings are structured diagnostics and are not another
support status. Geometry conventions or actions missing from v0.1 produce
software `UNSUPPORTED`, never normative `NOT_APPLICABLE` by themselves.

`DesignEligibility.executable` is true only for normative `APPLICABLE` and
software `SUPPORTED`. M7 contains no resistance engine, so eligibility is the
precondition for later authorized calculation rather than a design result.

See `docs/15_AISI_NORMATIVE_MAP_M7.md` for verified clauses and source
fingerprints and `docs/16_APPLICABILITY_M7.md` for the support matrix and exact
aggregation behavior.
