"""Steel catalog data/Materiales.xlsx: name, Fy, Fu, elongation group (AISI S100-24, A3.1).

Fy comes from Table A3.1.1-1. S100-24 does not tabulate Fu; it is left empty until it is
transcribed from each ASTM standard (DC-8). A provision that needs Fu must raise
IncompleteDataError when `Fu` is None.
"""
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Any

import openpyxl

from .errors import CatalogSchemaError, MaterialNotFoundError

SHEET = "Aceros"
HEADER = ("name", "standard", "grade", "Fy_MPa", "Fu_MPa", "elongation_group", "source")


@dataclass(frozen=True)
class Material:
    name: str
    standard: str
    grade: str
    Fy: float
    Fu: float | None
    elongation_group: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "standard": self.standard, "grade": self.grade, "Fy_MPa": self.Fy,
                "Fu_MPa": self.Fu, "elongation_group": self.elongation_group, "source": self.source}


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
                name, standard, grade, fy, fu, group, source = values[: len(HEADER)]
                key = str(name).strip()
                if key.upper() in {k.upper() for k in out}:
                    raise CatalogSchemaError(f"duplicate material '{key}'")
                if not isinstance(fy, (int, float)) or fy <= 0:
                    raise CatalogSchemaError(f"material '{key}' has no valid Fy")
                if fu is not None and (not isinstance(fu, (int, float)) or fu <= 0):
                    raise CatalogSchemaError(f"material '{key}' has an invalid Fu")
                out[key] = Material(key, str(standard), str(grade), float(fy), None if fu is None else float(fu),
                                    str(group), str(source))
            return out
        finally:
            workbook.close()


def get_material(name: str) -> Material:
    wanted = name.strip().upper()
    for key, material in catalog().items():
        if key.upper() == wanted:
            return material
    raise MaterialNotFoundError(f"material '{name}' is not in Materiales.xlsx", details={"available": sorted(catalog())})
