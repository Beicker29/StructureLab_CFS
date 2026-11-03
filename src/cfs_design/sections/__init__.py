"""Section resolution (DC-7): catalog properties or properties computed from the geometry.

A catalog section takes its gross properties and design thickness from data/Sections.xlsx;
everything the catalog does not hold (flat widths, Sy at both fibres of the C, principal
axes of the Z, Zx, Zy) comes from the geometry. A section given by `shape` and dimensions is
computed entirely from the geometry with the same engine. The result names its `source`.
Scope (DC-9): C_LIPPED and Z_LIPPED; other shapes are INCOMPLETE.
The asymmetry property j (Eq. 2.3.1-6) is reported as `j_asym` so that it does not collide
with J for case-insensitive JSON readers.
"""
import math
from dataclasses import dataclass
from typing import Any

from ..errors import IncompleteDataError, RuleNotImplementedError, SectionNotFoundError, ValidationError
from ..models import SectionInput
from . import catalog
from .elements import element_widths
from .geometry import build, c_lipped, z_lipped
from .thin_walled import gross_properties

SHAPES = ("C_LIPPED", "Z_LIPPED")


@dataclass(frozen=True)
class SectionProperties:
    name: str | None
    shape: str
    source: str  # "catalog" or "geometry"
    dimensions: dict[str, float]
    properties: dict[str, float]
    elements: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "shape": self.shape, "source": self.source, "dimensions": self.dimensions,
                "properties": self.properties, "elements": self.elements}


def _geometric(shape: str, H: float, B: float, D: float, t: float, R: float, lip_angle: float) -> tuple[dict[str, float], dict[str, float]]:
    vertices = c_lipped(H, B, D, t) if shape == "C_LIPPED" else z_lipped(H, B, D, t, lip_angle)
    geometry = build(vertices, t, R)
    g = gross_properties(geometry, t)
    if shape == "C_LIPPED":
        xcent = g["xc"]                              # centroid to the outer face of the web
        sy = g["Iy"] / (B - xcent)
    else:
        xcent = max(g["x_max"] - g["xc"], g["xc"] - g["x_min"])  # centroid to the farthest fibre in x
        sy = g["Iy"] / xcent
    props = {"A": g["A"], "xcent": xcent, "xo": g["xo"], "J": g["J"], "Cw": g["Cw"], "j_asym": g["j"], "Ix": g["Ix"],
             "Iy": g["Iy"], "Ixy": g["Ixy"], "Sx": g["Ix"] / (H / 2), "Sy": sy, "rx": g["rx"], "ry": g["ry"], "ro": g["ro"],
             "Zx": g["Zx"], "Zy": g["Zy"]}
    return props, element_widths(geometry, B, D, t, R)


def _derived(shape: str, B: float, p: dict[str, float]) -> dict[str, float]:
    """Sy at both fibres of the C (F2.1 Sf, Sfc, p. 49) and principal axes of the Z, from Ix, Iy, Ixy, xcent."""
    if shape == "C_LIPPED":
        return {"Sy_web": p["Iy"] / p["xcent"], "Sy_tip": p["Iy"] / (B - p["xcent"])}
    mean, half = (p["Ix"] + p["Iy"]) / 2, (p["Ix"] - p["Iy"]) / 2
    radius = math.hypot(half, p["Ixy"])
    return {"I1": mean + radius, "I2": mean - radius, "theta_p_deg": math.degrees(0.5 * math.atan2(-2 * p["Ixy"], p["Ix"] - p["Iy"]))}


def resolve_section(section: SectionInput) -> SectionProperties:
    """Raises SectionNotFoundError (invalid input) or a blocking error (INCOMPLETE): missing data, shape out of scope."""
    if section.name is not None:
        entry = catalog.find(section.name)
        if entry is None:
            raise SectionNotFoundError(f"section '{section.name}' is not in Sections.xlsx")
        if entry.t_design is None:
            raise IncompleteDataError(f"section '{entry.name}' has no t_design_mm in Sections.xlsx",
                                      details={"section": entry.name, "missing": "t_design_mm"})
        geo_props, elements = _geometric(entry.shape, entry.H, entry.B, entry.D, entry.t_design, entry.R, entry.lip_angle)
        props = {**entry.properties, "Zx": geo_props["Zx"], "Zy": geo_props["Zy"]}
        dims = {"H": entry.H, "B": entry.B, "D": entry.D, "t": entry.t_design, "R": entry.R, "lip_angle": entry.lip_angle}
        return SectionProperties(entry.name, entry.shape, "catalog", dims, {**props, **_derived(entry.shape, entry.B, props)},
                                 elements)
    shape = str(section.shape)
    if shape not in SHAPES:
        raise RuleNotImplementedError(f"shape {shape} is outside the current scope (DC-9: C_LIPPED and Z_LIPPED)",
                                      details={"shape": shape, "decision": "DC-9"})
    lip_angle = section.lip_angle
    if shape == "C_LIPPED":
        if lip_angle not in (None, 90):
            raise ValidationError("C_LIPPED lips are at 90°", details={"lip_angle": lip_angle})
        lip_angle = 90.0
    required = {"H": section.H, "B": section.B, "D": section.D, "R": section.R, "lip_angle": lip_angle}
    missing = [k for k, v in required.items() if v is None]
    if missing:
        raise IncompleteDataError(f"{shape} needs {', '.join(missing)}", details={"missing": missing})
    dims = {k: float(v) for k, v in {**required, "t": section.t}.items() if v is not None}
    props, elements = _geometric(shape, dims["H"], dims["B"], dims["D"], dims["t"], dims["R"], dims["lip_angle"])
    return SectionProperties(None, shape, "geometry", dims, {**props, **_derived(shape, dims["B"], props)}, elements)


__all__ = ["SectionProperties", "resolve_section"]
