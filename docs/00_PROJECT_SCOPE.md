# Project Scope

## Current milestone

Milestone 7 provides source-fingerprinted S100-24 applicability, independent
v0.1 software-support checks, and an eligibility gate over the immutable M5/M6
inputs and results infrastructure. It performs no governing-demand selection,
AISI resistance equation, elastic buckling, EWM/DSM strength calculation, or
pyCUFSM operation. The software is not available for professional engineering
use.

## Approved v0.1 scope

- Catalogued lipped and unlipped C sections only.
- Approved catalogued isotropic cold-formed steel materials.
- ANSI/SDI AISI S100-24, LRFD.
- Axial compression and strong-axis flexure.
- Global, local, and distortional buckling where applicable.
- Independent Effective Width Method and Direct Strength Method routes.
- pyCUFSM used only to obtain elastic buckling results for the DSM route.
- EWM-only, DSM-only, and EWM/DSM comparison modes.
- Native ETABS Excel input with many members, load combinations, stations, and
  simultaneous demand points.
- Member and demand-point results, governing limit state, calculation trace,
  project summary, and resolved input snapshot.

## Explicit v0.1 exclusions

Shear design, P-M interaction, openings, built-up members, connections, web
crippling, seismic system design, arbitrary user-defined sections, automatic
load-combination generation, SAP2000 import, GUI/web applications, and Excel as
a calculation engine are excluded.

Scope changes require explicit owner approval. Numerical capability must not be
inferred from the presence of future package directories.
