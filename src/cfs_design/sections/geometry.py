"""Cross-section geometry of C_LIPPED and Z_LIPPED from out-to-out dimensions (DC-3, D3).

Axes (D2): x perpendicular to the web, y along the web, x positive from the web toward the
flange tips. Units: mm.

The section is described by its sharp-cornered midline polyline. Corners are rounded with
inside radius R (outside R + t, midline R + t/2), the rounded-corner model of DC-4 / D1:
- `parts`: exact solid pieces, flats as rectangles and corners as annular sectors. With R = 0
  the corners are mitred (a t x t square at a 90° bend) and the flats become trapezoids.
- `midline`: lines and arcs of the midline, for the thin-walled sectorial properties.
- `flats`: flat width of each segment, exclusive of corners (S100-24 A1.3 "Flat Width", p. 5).

C_LIPPED: lips at 90° toward the other flange; D is the out-to-out vertical lip dimension.
Z_LIPPED: lips inclined outward (away from the web) at `lip_angle` to the flange plane; B is
measured to the sharp outer corner of the flange/lip bend and D along the outer face of the
lip from that corner. This reading reproduces data/Sections.xlsx (A, Ix, Iy, Ixy within 5e-6).
"""
import math
from dataclasses import dataclass

from ..errors import ValidationError

Point = tuple[float, float]


@dataclass(frozen=True)
class Polygon:
    vertices: tuple[Point, ...]


@dataclass(frozen=True)
class Sector:
    """Annular sector: centre (cx, cy), radii a < b, angles phi1 < phi2 (rad)."""

    cx: float
    cy: float
    a: float
    b: float
    phi1: float
    phi2: float


@dataclass(frozen=True)
class Line:
    p: Point
    q: Point


@dataclass(frozen=True)
class Arc:
    """Midline arc: centre, radius, start angle and signed sweep (rad)."""

    cx: float
    cy: float
    r: float
    phi0: float
    sweep: float


@dataclass(frozen=True)
class Geometry:
    vertices: tuple[Point, ...]  # sharp-cornered midline polyline
    parts: tuple[Polygon | Sector, ...]
    midline: tuple[Line | Arc, ...]
    flats: tuple[float, ...]


def c_lipped(H: float, B: float, D: float, t: float) -> list[Point]:
    """Midline vertices from the top lip tip to the bottom lip tip; web outer face at x = 0."""
    return [(B - t / 2, H / 2 - D), (B - t / 2, H / 2 - t / 2), (t / 2, H / 2 - t / 2), (t / 2, -H / 2 + t / 2),
            (B - t / 2, -H / 2 + t / 2), (B - t / 2, -H / 2 + D)]


def z_lipped(H: float, B: float, D: float, t: float, lip_angle: float) -> list[Point]:
    """Midline vertices from the top lip tip to the bottom lip tip; web midline at x = 0, top flange toward +x."""
    theta = math.radians(lip_angle)
    u = (math.cos(theta), -math.sin(theta))         # along the lip, from the bend to the tip
    n = (-math.sin(theta), -math.cos(theta))        # lip normal toward the inside of the bend
    outer = (B - t / 2, H / 2)                      # sharp outer corner of the flange/lip bend
    s = t * (1 - math.cos(theta)) / (2 * math.sin(theta))
    bend = (outer[0] + n[0] * t / 2 + s * u[0], outer[1] + n[1] * t / 2 + s * u[1])
    tip = (outer[0] + D * u[0] + n[0] * t / 2, outer[1] + D * u[1] + n[1] * t / 2)
    top = [tip, bend, (0.0, H / 2 - t / 2)]
    return top + [(-x, -y) for x, y in reversed(top)]


def _unit(p: Point, q: Point) -> tuple[Point, float]:
    dx, dy = q[0] - p[0], q[1] - p[1]
    length = math.hypot(dx, dy)
    return (dx / length, dy / length), length


def _strip(p: Point, q: Point, t: float) -> Polygon:
    (ux, uy), _ = _unit(p, q)
    nx, ny = -uy * t / 2, ux * t / 2
    return Polygon(((p[0] + nx, p[1] + ny), (q[0] + nx, q[1] + ny), (q[0] - nx, q[1] - ny), (p[0] - nx, p[1] - ny)))


def _offset_vertex(prev: Point, v: Point, nxt: Point, d: float) -> Point:
    """Mitre point of the two midline segments offset by d (left positive)."""
    (u1x, u1y), _ = _unit(prev, v)
    (u2x, u2y), _ = _unit(v, nxt)
    bx, by = -u1y - u2y, u1x + u2x                  # sum of left normals
    scale = d * 2 / (bx * (-u1y) + by * u1x + bx * (-u2y) + by * u2x)
    return v[0] + bx * scale, v[1] + by * scale


def build(vertices: list[Point], t: float, R: float) -> Geometry:
    """Solid parts, midline and flat widths of an open polyline section of thickness t and inside radius R."""
    n = len(vertices)
    rm = R + t / 2
    trims, corners = [0.0] * (2 * (n - 1)), []
    for i in range(1, n - 1):
        u1, _ = _unit(vertices[i - 1], vertices[i])
        u2, _ = _unit(vertices[i], vertices[i + 1])
        cross = u1[0] * u2[1] - u1[1] * u2[0]
        alpha = math.acos(max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1])))
        trims[2 * i - 1] = trims[2 * i] = rm * math.tan(alpha / 2)
        corners.append((u1, u2, cross, alpha))
    flats = []
    for i in range(n - 1):
        _, length = _unit(vertices[i], vertices[i + 1])
        flat = length - trims[2 * i] - trims[2 * i + 1]
        if flat <= 0:
            raise ValidationError("the dimensions leave no flat portion in a segment of the section",
                                  details={"segment": i, "flat_width": flat})
        flats.append(flat)
    parts: list[Polygon | Sector] = []
    midline: list[Line | Arc] = []
    if R == 0:
        left = [vertices[0]] + [_offset_vertex(vertices[i - 1], vertices[i], vertices[i + 1], t / 2) for i in range(1, n - 1)]
        right = [vertices[0]] + [_offset_vertex(vertices[i - 1], vertices[i], vertices[i + 1], -t / 2) for i in range(1, n - 1)]
        for i in range(n - 1):
            p, q = vertices[i], vertices[i + 1]
            strip = _strip(p, q, t).vertices
            lp = strip[0] if i == 0 else left[i]
            rp = strip[3] if i == 0 else right[i]
            lq = strip[1] if i == n - 2 else left[i + 1]
            rq = strip[2] if i == n - 2 else right[i + 1]
            parts.append(Polygon((lp, lq, rq, rp)))
            midline.append(Line(p, q))
        return Geometry(tuple(vertices), tuple(parts), tuple(midline), tuple(flats))
    start = vertices[0]
    for i in range(n - 1):
        v = vertices[i + 1]
        if i == n - 2:
            end = v
        else:
            u1, u2, cross, alpha = corners[i]
            T = trims[2 * i + 1]
            end = (v[0] - u1[0] * T, v[1] - u1[1] * T)
        parts.append(_strip(start, end, t))
        midline.append(Line(start, end))
        if i < n - 2:
            u1, u2, cross, alpha = corners[i]
            normal = (-u1[1], u1[0]) if cross > 0 else (u1[1], -u1[0])
            cx, cy = end[0] + normal[0] * rm, end[1] + normal[1] * rm
            phi0 = math.atan2(end[1] - cy, end[0] - cx)
            sweep = alpha if cross > 0 else -alpha
            parts.append(Sector(cx, cy, R, R + t, min(phi0, phi0 + sweep), max(phi0, phi0 + sweep)))
            midline.append(Arc(cx, cy, rm, phi0, sweep))
            T = trims[2 * i + 2]
            start = (v[0] + u2[0] * T, v[1] + u2[1] * T)
    return Geometry(tuple(vertices), tuple(parts), tuple(midline), tuple(flats))
