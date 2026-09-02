# ETABS Import Contract

Milestone 4 implements this IO-boundary flow:

```text
Native ETABS Excel
  -> validated ETABSRawForceRow records
  -> explicit unit/sign normalization
  -> NormalizedETABSDemand provenance wrappers
  -> ETABS_Mapping
  -> DemandSet grouped by project case_id
```

It does not load `Members`, resolve a `MemberCase`, rotate axes, choose a
governing demand, or perform design. Those operations remain outside M4.
Mechanics, EWM, DSM, pyCUFSM adapters, and reports never read ETABS Excel.

## Native workbook layout

The approved export is read without modification. Its required sheets are
`Program Control` and `Element Forces - Beams`. Both native tables use row 1
for the title and row 2 for field names. The force table uses row 3 for units
and row 4 onward for data. These rows, sheet names, and every expected column
label are held in immutable `ETABSImportConfig` and `ETABSColumnMap` objects.
Columns are resolved by label, never by hidden numeric position. Complete blank
data rows are ignored; malformed partial rows fail with workbook, sheet, row,
and field context.

`ProgramName`, `Version`, and `CurrUnits` are retained as source metadata. The
license field is neither read into nor exposed by the result model.

## Unit authority and normalization

The force-table unit row is authoritative for the force values. `CurrUnits`
from `Program Control` remains audit metadata and does not override the table.
This is why the approved workbook's `kip, in, F` metadata does not reinterpret
table cells explicitly labelled `m`, `kgf`, and `kgf-m`.

M4 supports and tests only these exact conversions:

| ETABS table quantity | Source unit | Canonical unit | Factor |
|---|---:|---:|---:|
| `Station`, `Elem Station` | m | mm | 1000 |
| `P`, `V2`, `V3` | kgf | N | 9.80665 |
| `T`, `M2`, `M3` | kgf-m | N-mm | 9806.65 |

Conversions occur once at the IO boundary and are not rounded. Blank force
components are not assumed to be zero. Unknown or ambiguous units and
non-finite values fail explicitly.

## Force and local-axis conventions

Canonical axial demand `p_n` is positive in compression. Native ETABS frame
force `P` is positive in tension, therefore:

```text
p_n = -P_ETABS * 9.80665
```

`V2`, `V3`, `T`, `M2`, and `M3` retain their native CSI local-axis signs after
positive unit scaling. M4 does not take absolute values and does not rotate
member local axes into section axes. Orientation and strong-axis resolution
are deferred to M5.

## Native rows, stations, and demand points

Every valid force-table row remains an indivisible source record and produces
one `DemandPoint`. `Step Type`, station, element, element station, and
`Location` are retained. Separate `Before` and `After` rows at the same station
remain separate points. No station is selected and no component-wise envelope
is formed.

Point IDs are deterministic from the source workbook SHA-256 prefix and native
row number. `NormalizedETABSDemand` retains the corresponding immutable raw
row; the import metadata retains the absolute source path, SHA-256, worksheet,
layout, source units, and ETABS program metadata. Together these identify the
exact source row without adding ETABS-specific fields to generic domain
objects.

## Output Cases and response-spectrum semantics

Within a mapped project case, native `Output Case` values become separate
`DemandCombination` objects and `Case Type` is preserved. The approved `DERX`
and `DERY` cases are not merged.

The approved rows are `LinRespSpec` with `Step Type = Max`. Each row is kept as
the native ETABS response state supplied by the export. M4 does not claim that
response-spectrum ordinates are time-history simultaneous states, fabricate a
negative counterpart, combine independent rows, or create an envelope.

## Mapping contract

Only `members.xlsx:ETABS_Mapping` is read. Disabled rows are preserved for
inspection but ignored during matching. Enabled rows use this exact priority:

1. stripped, exact ETABS `Unique Name`;
2. stripped, exact `Story + Beam` fallback.

No fuzzy or case-insensitive matching is performed. Duplicate project IDs,
duplicate ETABS identities, incomplete fallback pairs, and conflicting unique
versus fallback matches fail explicitly. M4 enforces one enabled mapping row
per physical project case and does not invent multi-object aggregation.

Mapped rows are grouped as:

```text
case_id -> Output Case -> all source rows in workbook order
```

Unexpected ETABS rows are returned in `unmapped_rows` with warnings; they are
never discarded. An enabled mapping with no matching rows also produces a
warning. The later project QA policy decides whether either condition is
fatal.

## M4 limitations

M4 does not load `project.yaml` or the full `Members` sheet, resolve materials
or sections, rotate axes, reduce stations, determine a governing condition,
calculate utilization, apply AISI provisions, run EWM/DSM, or integrate
pyCUFSM. Formula evaluation is not supported; a formula required by the import
must already have a usable cached value or import fails.
