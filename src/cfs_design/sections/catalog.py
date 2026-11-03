"""Section catalog data/Sections.xlsx (DC-7): dimensions, design thickness and gross properties.

Every sheet except `Notas` holds one family (PHR-C, PHR-Z, PAG-C, PAG-Z) with the header
below. `t_design_mm` is the base-steel design thickness (S100-24 A1.3 "Thickness", p. 7); an
empty cell is kept as None and the section resolves to INCOMPLETE, never to t_mm. The catalog
properties are taken as computed with `t_design_mm` (DC-7, provisional assumption).
"""
from dataclasses import dataclass
from functools import cache
from importlib import resources

import openpyxl

from ..errors import CatalogSchemaError

NOTES_SHEET = "Notas"
HEADER = ("name", "shape", "finish", "H_mm", "B_mm", "D_mm", "t_mm", "t_design_mm", "calibre", "R_mm", "lip_angle_deg",
          "area_mm2", "peso_kgf_m", "xcent_mm", "xo_mm", "J_mm4", "Cw_mm6", "j_mm", "Ix_mm4", "Iy_mm4", "Sx_mm3", "Sy_mm3",
          "rx_mm", "ry_mm", "ro_mm", "Ixy_mm4")
SHAPES = ("C_LIPPED", "Z_LIPPED")
# catalog column -> property key of the result
PROPERTY_COLUMNS = {"area_mm2": "A", "xcent_mm": "xcent", "xo_mm": "xo", "J_mm4": "J", "Cw_mm6": "Cw", "j_mm": "j_asym",
                    "Ix_mm4": "Ix", "Iy_mm4": "Iy", "Ixy_mm4": "Ixy", "Sx_mm3": "Sx", "Sy_mm3": "Sy", "rx_mm": "rx",
                    "ry_mm": "ry", "ro_mm": "ro"}
SIGNED = {"xo_mm", "j_mm", "Ixy_mm4"}


@dataclass(frozen=True)
class CatalogSection:
    name: str
    sheet: str
    shape: str
    H: float
    B: float
    D: float
    t: float
    t_design: float | None
    R: float
    lip_angle: float
    properties: dict[str, float]


def _number(value: object, name: str, column: str, *, positive: bool = True, allow_zero: bool = False) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise CatalogSchemaError(f"section '{name}' has no valid {column}")
    if positive and (value < 0 or (value == 0 and not allow_zero)):
        raise CatalogSchemaError(f"section '{name}' has an invalid {column}", details={"value": value})
    return float(value)


@cache
def catalog() -> dict[str, CatalogSection]:
    path = resources.files("cfs_design") / "data" / "Sections.xlsx"
    with resources.as_file(path) as file:
        workbook = openpyxl.load_workbook(file, read_only=True, data_only=True)
        try:
            out: dict[str, CatalogSection] = {}
            for sheet in workbook.sheetnames:
                if sheet == NOTES_SHEET:
                    continue
                rows = workbook[sheet].iter_rows(values_only=True)
                header = tuple(str(h).strip() if h is not None else "" for h in next(rows))
                if header[: len(HEADER)] != HEADER:
                    raise CatalogSchemaError(f"unexpected header in Sections.xlsx sheet '{sheet}'",
                                             details={"expected": HEADER, "found": header})
                for values in rows:
                    if values[0] is None:
                        continue
                    row = dict(zip(HEADER, values, strict=False))  # header checked as a prefix
                    name = str(row["name"]).strip()
                    if name.upper() in {k.upper() for k in out}:
                        raise CatalogSchemaError(f"duplicate section '{name}'")
                    if row["shape"] not in SHAPES:
                        raise CatalogSchemaError(f"section '{name}' has an unsupported shape", details={"shape": row["shape"]})
                    t_design = None if row["t_design_mm"] is None else _number(row["t_design_mm"], name, "t_design_mm")
                    props = {key: _number(row[col], name, col, positive=col not in SIGNED, allow_zero=True)
                             for col, key in PROPERTY_COLUMNS.items()}
                    out[name] = CatalogSection(
                        name=name, sheet=sheet, shape=str(row["shape"]),
                        H=_number(row["H_mm"], name, "H_mm"), B=_number(row["B_mm"], name, "B_mm"),
                        D=_number(row["D_mm"], name, "D_mm"), t=_number(row["t_mm"], name, "t_mm"), t_design=t_design,
                        R=_number(row["R_mm"], name, "R_mm", allow_zero=True),
                        lip_angle=_number(row["lip_angle_deg"], name, "lip_angle_deg"), properties=props)
            return out
        finally:
            workbook.close()


def find(name: str) -> CatalogSection | None:
    wanted = name.strip().upper()
    for key, section in catalog().items():
        if key.upper() == wanted:
            return section
    return None
