"""Public orchestration for the M4 ETABS import boundary."""

from pathlib import Path

from .mapping import map_etabs_demands
from .models import ETABSImportResult, ETABSMappingTable
from .normalization import normalize_etabs_demands
from .reader import read_etabs_results
from .schema import ETABSImportConfig


def import_etabs_results(
    path: str | Path,
    *,
    config: ETABSImportConfig | None = None,
    mapping: ETABSMappingTable | None = None,
) -> ETABSImportResult:
    """Read, normalize, and optionally map native ETABS force rows."""

    read_result = read_etabs_results(path, config=config)
    normalized_rows = normalize_etabs_demands(read_result)
    return map_etabs_demands(read_result, normalized_rows, mapping)


__all__ = ["import_etabs_results"]
