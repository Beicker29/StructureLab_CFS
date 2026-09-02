# M7 AISI S100-24 Normative Evidence Map

## Primary authority

M7 was developed by inspecting the local primary document itself. The source
registry in `cfs_design.normative.sources` is the single typed identity record;
the PDF remains the authority and the registry is provenance metadata only.

| Field | Verified value |
|---|---|
| Source ID | `ANSI_SDI_AISI_S100_2024` |
| Designation | ANSI/SDI AISI S100-2024 |
| Title | North American Specification for the Design of Cold-Formed Steel Structural Members |
| Edition | 2024 |
| Organization | Steel Deck Institute |
| Repository path | `references/standards/AISI_S100-24/ANSI-SDI-AISI-S100-2024-SDI-AISI-S100-2024-C.pdf` |
| SHA-256 | `6ec32742f056d08a0823557d9ce58b69d84312e64a6e656b8ba4b3b10cf4b4ca` |

The document title pages identify the designation, title, edition, publisher,
and first printing. Clause identifiers below were verified against the
specification portion of that same file. Wording in this map is deliberately
short and original; it does not reproduce AISI provisions.

## Source hierarchy and discovered documents

The implemented `SOURCE_AUTHORITY_ORDER` is primary normative authority,
validation reference, previous standard, commentary/design manual, then future
scope. Only the primary role may support an active S100-24 applicability
reference.

| Role | Discovered document | SHA-256 | M7 use |
|---|---|---|---|
| Primary normative | ANSI/SDI AISI S100-2024 | `6ec32742f056d08a0823557d9ce58b69d84312e64a6e656b8ba4b3b10cf4b4ca` | Controls active rules |
| Previous standard | AISI S100-16 (2020) w/S3-22 | `706a4bfaf030768d6382324a8d1916acdb749a0e739ef20fa0d7638ba8a9f03a` | History only; cannot override or be labeled S100-24 |
| Future scope | AISI S240-20 | `c8bd8d62bf35878388b38a31f603478590ee744bd2b15eb77a74dbaae9d1e93e` | Registered and isolated |
| Future scope | AISI S400-20 | `97b7891ae9bc0af54e78074f7a7ddc9d6cdb9b3fdff71140c2b80630e1859b2b` | Registered and isolated |

No D102-23 validation document or D100-17 design manual was present in the
recursively inspected standards directory. Their hierarchy roles exist, but
no source record was fabricated. `future_scope` documents are not imported by
the current member-applicability implementation.

## Active evidence map

The result status describes the ordinary S100-24 member route evaluated by M7.
In particular, a failed B4.1 check means the ordinary Chapter E/F factor route
is `NOT_APPLICABLE`; it does not claim that AISI prohibits every alternative.
M7 records B4.2 as unevaluated when that distinction is needed.

| Rule ID | Topic | Method | Action | Verified S100-24 reference | Repository implementation | Short purpose |
|---|---|---|---|---|---|---|
| `M7_SOURCE_SELECTION` | Source guard | Both | All | Primary document identity | `normative.applicability` | Prevents S100-24 rules from evaluating another edition |
| `A1_1_THICKNESS` | Specification scope | Both | Current actions | A1.1, specification p. 1 | `normative.applicability` | Checks the explicit 25.4 mm thickness ceiling |
| `A1_1_MEMBER_PROVENANCE` | Member/material scope | Both | Current actions | A1.1, specification p. 1 | `normative.applicability` | Requires forming, material class, structural use, and dynamic context to be established |
| `A1_2_3_DESIGN_FORMAT_JURISDICTION` | Design-format geography | Both | Current actions | A1.2.3, specification p. 1 | `normative.applicability` | Relates ASD/LRFD/LSD to the governing country |
| `B4_1_YIELD_STRESS` | Method material limit | EWM / DSM | Current actions | B4.1, Table B4.1-1, specification p. 26 | `normative.applicability` | Checks the method-specific Fy ceiling |
| `B4_1_INSIDE_RADIUS` | Method geometry limit | EWM / DSM | Current actions | B4.1, Table B4.1-1, specification p. 26 | `normative.applicability` | Checks the method-specific inside-radius ratio |
| `B4_1_ELEMENT_DIMENSIONS` | Element ratios | EWM / DSM | Current actions | B4.1, Table B4.1-1, specification p. 26 | `normative.applicability` | Evaluates explicit schema-0.2 AISI flat/out-to-out values; absence stays indeterminate |
| `B4_1_EDGE_STIFFENER_TYPE` | Edge-stiffener category | EWM / DSM | Current actions | B4.1, Table B4.1-1, specification p. 26 | `normative.applicability` | Classifies the explicit simple-lip or unstiffened C edge |
| `B4_2_ALTERNATIVE_ROUTE` | Outside B4.1 | Both | Current actions | B4.2, specification p. 27 | `normative.applicability` | Records that separate testing/rational-analysis factor routes are not evaluated |
| `E3_METHOD_ROUTE` | Compression local interaction | EWM | Axial compression | E3 and E3.1, specification p. 44 | `normative.applicability` | Identifies the EWM compression route |
| `E3_METHOD_ROUTE` | Compression local interaction | DSM | Axial compression | E3 and E3.2, specification pp. 44-45 | `normative.applicability` | Identifies the DSM compression route |
| `F_SCOPE_BENDING_AXIS` | Flexure scope | Both | Strong-axis flexure | Chapter F scope, specification p. 48 | `normative.applicability` | Requires a Chapter F bending-axis case to be established |
| `F_SCOPE_TWIST_CONDITION` | Flexure scope | Both | Strong-axis flexure | Chapter F scope, specification p. 48 | `normative.applicability` | Requires an accepted load-plane, twist-restraint, or combined-torsion condition |
| `F2_METHOD_ROUTE` | Yield/global flexure | EWM / DSM | Strong-axis flexure | F2.1 / F2.2, specification pp. 48 and 50 | `normative.applicability` | Selects the verified method-specific global route |
| `F3_METHOD_ROUTE` | Local interaction in flexure | EWM / DSM | Strong-axis flexure | F3.1 / F3.2, specification pp. 51-52 | `normative.applicability` | Selects the verified method-specific local route |
| `B3_3_ACTION_ROUTE_NOT_EVALUATED` | Future action guard | Both | Shear or combined action | B3.3, specification p. 24 | `normative.applicability` | Leaves unimplemented action routes indeterminate rather than prohibited |

The code cites clauses only. It implements no equation from the cited pages.

## Deliberately indeterminate facts

M7 returns `INDETERMINATE` when current domain data cannot establish:

- the cold-forming process, qualifying base-metal class, intended
  load-carrying use, or dynamic-effects allowance needed by A1.1;
- the governing country needed to finish the A1.2.3 design-format check;
- B4.1 flat and out-to-out element dimensions when the resolved section has no
  matching explicit S100-24 dimensional record;
- Chapter F load-plane coincidence with the shear center when twisting is not
  explicitly restrained;
- a normative action route outside axial compression and strong-axis flexure;
- B4.2 testing or rational-analysis alternatives.

The existing `MIDLINE` dimensions are not treated as B4.1 flat widths or
out-to-out widths. `FLAT_WIDTHS` and `OUT_TO_OUT` are likewise not converted.
This is intentional engineering uncertainty, not missing arithmetic.

M8A adds a separate exact-key dimensional source. When present, M7 checks the
web, flange, lip, and `d_o/b_o` ratios directly. For an EWM lipped flange with
`60 < b/t <= 90`, the check remains `INDETERMINATE` until `I_s/I_a` is
available to select the table limit. An exceeded explicit limit is
`NOT_APPLICABLE` to the ordinary B4.1 route and retains the B4.2 distinction.

## Boundary

PDF reading was a development audit activity only. Production applicability
uses typed rules and M6 `EquationReference` objects containing the primary
source fingerprint. The package neither parses a PDF at design runtime nor
calculates strength, resistance factors, buckling loads, effective widths, or
utilization.
