# PRJ_001 Example Project Inputs

The supplied Excel files contain illustrative, inactive `EX_` records and a
native ETABS export. They are contract examples, not verified design data.

`project.yaml` completes the approved five-file M0 contract and uses
repository-root-relative paths. Its placeholder project metadata and inactive
catalog/member rows mean this remains a schema example, not a runnable design
case.

The project owner identifies the intended ETABS units as m, kN, kN·m, and s.
The native export contains conflicting unit labels; this discrepancy must be
rejected or explicitly resolved by the future importer rather than silently
converted.
