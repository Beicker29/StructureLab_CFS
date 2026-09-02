"""Explicit unit and sign normalization from ETABS rows to domain demands."""

from cfs_design.core.exceptions import ValidationError
from cfs_design.core.units import (
    convert_force_to_n,
    convert_length_to_mm,
    convert_moment_to_nmm,
)
from cfs_design.domain import DemandPoint

from .models import ETABSReadResult, NormalizedETABSDemand


def _compression_positive(value: float) -> float:
    result = -value
    return 0.0 if result == 0.0 else result


def normalize_etabs_demands(
    read_result: ETABSReadResult,
) -> tuple[NormalizedETABSDemand, ...]:
    """Normalize every row independently; no component envelope is created."""

    if not isinstance(read_result, ETABSReadResult):
        raise ValidationError("read_result must be ETABSReadResult")
    units = read_result.metadata.source_units
    digest_prefix = read_result.metadata.file_sha256[:12].upper()
    normalized: list[NormalizedETABSDemand] = []
    for raw in read_result.raw_rows:
        converted_p = convert_force_to_n(raw.p_raw, units.p)
        point = DemandPoint(
            point_id=f"ETABS-{digest_prefix}-R{raw.source_row:06d}",
            p_n=_compression_positive(converted_p),
            v2_n=convert_force_to_n(raw.v2_raw, units.v2),
            v3_n=convert_force_to_n(raw.v3_raw, units.v3),
            t_nmm=convert_moment_to_nmm(raw.t_raw, units.t),
            m2_nmm=convert_moment_to_nmm(raw.m2_raw, units.m2),
            m3_nmm=convert_moment_to_nmm(raw.m3_raw, units.m3),
            station_mm=convert_length_to_mm(raw.station_raw, units.station),
            step_type=raw.step_type,
            element_id=raw.element,
            element_station_mm=convert_length_to_mm(
                raw.element_station_raw, units.element_station
            ),
            location=raw.location,
        )
        normalized.append(NormalizedETABSDemand(raw_row=raw, demand_point=point))
    return tuple(normalized)


__all__ = ["normalize_etabs_demands"]
