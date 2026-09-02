# M4 ETABS Importer Technical Note

## Public API

The `cfs_design.io.etabs` boundary exposes:

```python
read_etabs_results(path, config=...)
normalize_etabs_demands(read_result)
load_etabs_mapping(path)
map_etabs_demands(read_result, normalized_rows, mapping)
import_etabs_results(path, config=..., mapping=...)
```

`import_etabs_results` composes the other operations. The split APIs allow raw
source inspection and independent normalization/mapping tests without leaking
cell parsing helpers.

## Result layers

- `ETABSRawForceRow` contains unchanged values from one native result row.
- `ETABSReadResult` pairs all raw rows with workbook metadata and source units.
- `DemandPoint` contains canonical `mm`, `N`, and `N-mm` values.
- `NormalizedETABSDemand` links each generic point to its exact raw row.
- `ETABSMappingTable` preserves enabled and disabled mapping records.
- `MappedMemberDemands` contains one `DemandSet` for a mapped `case_id` plus
  the ordered provenance records used to build it.
- `ETABSImportResult` returns metadata, raw rows, normalized rows, mapped
  groups, unmapped rows, mapping data, and warnings as immutable values.

The raw and normalized layers are deliberately separate. Import never mutates
source values or overwrites them with converted values.

## Integrity behavior

The reader opens cached-value and formula views of each workbook in read-only
mode. It rejects missing sheets/columns, duplicate headers, required formulas
without cached results, missing identity values, nonnumeric force cells, NaN,
infinity, and unsupported unit labels. Errors include source context.

The approved workbook regression asserts 24 rows: 12 for `DERX` and 12 for
`DERY`. Both cases preserve the two 2.75 m rows labelled `Before` and `After`.
The approved Excel files are never edited by tests; invalid and enabled-mapping
cases use temporary copies.

## Deliberate boundaries

The importer owns native ETABS concepts and conversion at the IO boundary.
Generic demand objects do not acquire workbook paths or ETABS program fields.
Conversely, no M4 module imports section mechanics, design provisions, or
pyCUFSM. M5 must consume this result to resolve project members and orientation
without moving spreadsheet concerns into the domain or design layers.
