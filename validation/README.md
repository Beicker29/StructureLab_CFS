# Validation Assets

This hierarchy separates AISI examples, external-solver benchmarks,
independent hand calculations, literature comparisons, and end-to-end
regression baselines. M3A/M3B analytical mechanics checks live with the
automated tests.

`m9a/` contains compact numerical evidence generated from official CUFSM
v5.66 source. It distinguishes `CLASSICAL_CFSM_REFERENCE`, `FCFSM_REFERENCE`,
and `ENGINEERING_REFERENCE_CASES`. These files contain results and provenance,
not copied CUFSM implementation.
