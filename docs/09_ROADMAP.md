# Roadmap

Each milestone requires separate authorization and proportionate validation.

1. **M0 - Repository Foundation:** packaging, structure, documentation,
   contracts, smoke tests, and CI.
2. **M1 - Domain Model:** shared immutable/value-style engineering objects.
3. **M2 - Catalog Loaders and Validation:** versioned catalog IO and rules.
4. **M3A - Basic Section Geometry and Catalog Verification:** implemented for
   explicit orthogonal sharp-corner `MIDLINE` C sections and basic gross
   properties.
5. **M3B - Shear Center and Warping Constant:** implemented for the same
   orthogonal sharp-corner `MIDLINE` C-section geometry as M3A.
6. **M4 - ETABS Importer:** implemented native row parsing, authoritative
   force-table units, exact mapping inputs, provenance, and normalized demand
   states without enveloping.
7. **M5 - Project Loader, Resolver, and Section-Axis Demands:** implemented
   typed project/member loading, active catalog resolution, project QA,
   provenance, and one-to-one ETABS 2/3 to section x/y demand transformation.
8. **M6 - CalculationTrace and Result Infrastructure:** implemented shared
   finite engineering values, controlled units, references, diagnostics,
   immutable trace hierarchy, and generic result aggregates.
9. **M7 - Applicability Engine:** implemented source-fingerprinted S100-24
   applicability, independent v0.1 software support, and eligibility gate.
10. **M8A - EWM Input Readiness:** implemented the section-catalog 0.2 AISI
    dimensional contract, M2/M5 resolution, B4.1 consumption, coherent M3
    design-property policy/QA gate, normative elastic constants, and mandatory
    lipped-C E4 decision. No resistance exists.
11. **M8B - EWM Compression:** remains blocked until trusted section dimensions
    and M7 A1.1/A1.2.3 evidence exist; a complete lipped-C result must include
    verified E4.
12. **M9 - DSM Compression + pyCUFSM:** adapter, benchmarks, and authorized DSM
    provisions.
13. **M10 - EWM/DSM Comparison:** independent result comparison.
14. **M11 - Flexure:** strong-axis EWM and DSM design within approved scope.
15. **M12 - Future Interactions:** reserved for separately approved scope;
    P-M interaction remains outside v0.1.
16. **M13 - Reporting / Calculation Memory:** presentation from result and trace
    objects with no recalculation.

The calculation implementation still stops before M8B. M8A provides exact
standard-specific fields without changing M3 geometry; production rows remain
absent until traceable values are approved. Result strength fields remain
unpopulated. Curved-bend and geometry-convention conversions remain deferred.
