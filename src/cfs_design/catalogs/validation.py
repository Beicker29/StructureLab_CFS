"""Small catalog-level uniqueness and reference validation helpers."""

from collections.abc import Collection

from cfs_design.core.exceptions import CatalogError

from ._excel import RowContext


def register_unique(
    identifier: str,
    seen_rows: dict[str, int],
    context: RowContext,
    field: str,
) -> None:
    previous_row = seen_rows.get(identifier)
    if previous_row is not None:
        raise context.catalog_error(
            field,
            f"Duplicate ID {identifier!r}; first declared on row {previous_row}",
        )
    seen_rows[identifier] = context.row_number


def require_reference(
    identifier: str,
    valid_ids: Collection[str],
    context: RowContext,
    field: str,
    target: str,
) -> None:
    if identifier not in valid_ids:
        raise context.catalog_error(
            field,
            f"Unknown reference {identifier!r}; expected an ID from {target}",
        )


def reject_orphans(
    orphan_ids: Collection[str],
    source_path_name: str,
    worksheet: str,
    record_name: str,
) -> None:
    if orphan_ids:
        identifiers = ", ".join(sorted(orphan_ids))
        raise CatalogError(
            f"{source_path_name}\n"
            f"Worksheet: {worksheet}\n\n"
            f"Orphan {record_name} rows: {identifiers}"
        )


__all__ = ["register_unique", "reject_orphans", "require_reference"]

