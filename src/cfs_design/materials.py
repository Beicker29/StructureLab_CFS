"""Steel catalog data/Materiales.xlsx: name, Fy, Fu, elongation (AISI S100-24, A3.1).

Fy comes from Table A3.1.1-1. S100-24 does not tabulate Fu nor the minimum elongation; they are
transcribed from each ASTM standard with its edition in `Fu_elongation_source` (DC-8, D15).
While they are missing the material cannot be validated against A3.1.1 and design is INCOMPLETE.
No strength increase from cold work of forming (A3.3.2) is applied (DC-6 / D16).
"""
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Any

import openpyxl

from .errors import CatalogSchemaError, IncompleteDataError, MaterialNotFoundError, RuleNotImplementedError

SHEET = "Aceros"
HEADER = ("name", "standard", "grade", "Fy_MPa", "Fu_MPa", "elongation_group", "source", "elongation_pct",
          "elongation_gage_mm", "Fu_elongation_source")
# A3.1.1 (pp. 14-15): (a) Fu/Fy >= 1.08; (b) elongation >= 10 % in 50 mm or >= 7 % in 200 mm
MIN_FU_FY = 1.08
MIN_ELONGATION_PCT = {50: 10.0, 200: 7.0}


@dataclass(frozen=True)
class Material:
    name: str
    standard: str
    grade: str
    Fy: float
    Fu: float | None
    elongation_group: str
    source: str
    elongation_pct: float | None = None
    elongation_gage_mm: int | None = None
    fu_elongation_source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "standard": self.standard, "grade": self.grade, "Fy_MPa": self.Fy,
                "Fu_MPa": self.Fu, "elongation_group": self.elongation_group, "source": self.source,
                "elongation_pct": self.elongation_pct, "elongation_gage_mm": self.elongation_gage_mm,
                "Fu_elongation_source": self.fu_elongation_source}


def _optional_positive(value: object, name: str, column: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise CatalogSchemaError(f"material '{name}' has an invalid {column}", details={"value": value})
    return float(value)


@cache
def catalog() -> dict[str, Material]:
    path = resources.files("cfs_design") / "data" / "Materiales.xlsx"
    with resources.as_file(path) as file:
        workbook = openpyxl.load_workbook(file, read_only=True, data_only=True)
        try:
            if SHEET not in workbook.sheetnames:
                raise CatalogSchemaError(f"sheet '{SHEET}' not found in Materiales.xlsx")
            rows = workbook[SHEET].iter_rows(values_only=True)
            header = tuple(str(h).strip() if h is not None else "" for h in next(rows))
            if header[: len(HEADER)] != HEADER:
                raise CatalogSchemaError("unexpected header in Materiales.xlsx", details={"expected": HEADER, "found": header})
            out: dict[str, Material] = {}
            for values in rows:
                if values[0] is None:
                    continue
                row = dict(zip(HEADER, values, strict=False))
                key = str(row["name"]).strip()
                if key.upper() in {k.upper() for k in out}:
                    raise CatalogSchemaError(f"duplicate material '{key}'")
                fy = row["Fy_MPa"]
                if not isinstance(fy, (int, float)) or fy <= 0:
                    raise CatalogSchemaError(f"material '{key}' has no valid Fy")
                gage = _optional_positive(row["elongation_gage_mm"], key, "elongation_gage_mm")
                if gage is not None and int(gage) not in MIN_ELONGATION_PCT:
                    raise CatalogSchemaError(f"material '{key}' elongation gage must be 50 or 200 mm", details={"value": gage})
                source = row["Fu_elongation_source"]
                out[key] = Material(
                    key, str(row["standard"]), str(row["grade"]), float(fy), _optional_positive(row["Fu_MPa"], key, "Fu_MPa"),
                    str(row["elongation_group"]), str(row["source"]),
                    _optional_positive(row["elongation_pct"], key, "elongation_pct"),
                    None if gage is None else int(gage), None if source is None else str(source))
            return out
        finally:
            workbook.close()


def get_material(name: str) -> Material:
    wanted = name.strip().upper()
    for key, material in catalog().items():
        if key.upper() == wanted:
            return material
    raise MaterialNotFoundError(f"material '{name}' is not in Materiales.xlsx", details={"available": sorted(catalog())})


def validate_a3_1_1(material: Material) -> None:
    """A3.1.1 (pp. 14-15): use without restriction requires Fu/Fy >= 1.08 and the minimum elongation (D15).

    Missing Fu or elongation -> IncompleteDataError. A steel that does not meet them belongs to A3.1.2 or
    A3.1.3, whose restrictions are not automated -> RuleNotImplementedError.
    """
    missing = [k for k, v in (("Fu_MPa", material.Fu), ("elongation_pct", material.elongation_pct),
                              ("elongation_gage_mm", material.elongation_gage_mm),
                              ("Fu_elongation_source", material.fu_elongation_source)) if v is None]
    if missing:
        raise IncompleteDataError(f"material '{material.name}' cannot be validated against A3.1.1",
                                  details={"material": material.name, "missing": missing, "decision": "D15"})
    assert material.Fu is not None and material.elongation_pct is not None and material.elongation_gage_mm is not None
    ratio = material.Fu / material.Fy
    required = MIN_ELONGATION_PCT[material.elongation_gage_mm]
    if material.elongation_group != "A3.1.1" or ratio < MIN_FU_FY or material.elongation_pct < required:
        raise RuleNotImplementedError(f"material '{material.name}' is outside A3.1.1; A3.1.2/A3.1.3 restrictions are not automated",
                                      details={"Fu_Fy": ratio, "min_Fu_Fy": MIN_FU_FY, "elongation_pct": material.elongation_pct,
                                               "min_elongation_pct": required, "gage_mm": material.elongation_gage_mm})
