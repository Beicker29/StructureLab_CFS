"""Gross section properties of a Geometry (AISI S100-24 B5, p. 28: conventional methods, full section).

Method D1 (docs/chapter-sections.md):
- A, centroid, Ix, Iy, Ixy and the plastic moduli Zx, Zy (F2.2, p. 50) on the exact solid:
  rectangles and annular sectors, closed form.
- J = A t^2 / 3.
- Cw, xo and j (Appendix 2, Eq. 2.3.1-6, p. 2-3) with the sectorial coordinate of the midline
  (thin-walled theory, dA = t ds), integrated by Gauss-Legendre along each line and arc.
- ro: Appendix 2, Eq. 2.3.1-7 (p. 2-4).
Axes as in geometry.py (D2); x, y, xo are measured from the centroid of the exact solid.
"""
import math
from functools import cache

from .geometry import Arc, Geometry, Line, Polygon, Sector

Moments = tuple[float, float, float, float, float, float]  # A, ∫x, ∫y, ∫y², ∫x², ∫xy


@cache
def _gauss(n: int = 20) -> tuple[tuple[float, float], ...]:
    """Gauss-Legendre nodes and weights on [-1, 1]."""
    out = []
    for i in range(1, n + 1):
        x = math.cos(math.pi * (i - 0.25) / (n + 0.5))
        for _ in range(100):
            p0, p1 = 1.0, x
            for k in range(2, n + 1):
                p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
            dp = n * (x * p1 - p0) / (x * x - 1)
            dx = p1 / dp
            x -= dx
            if abs(dx) < 1e-16:
                break
        out.append((x, 2 / ((1 - x * x) * dp * dp)))
    return tuple(out)


def _polygon_moments(vertices: tuple[tuple[float, float], ...]) -> Moments:
    a = sx = sy = ixx = iyy = ixy = 0.0
    for (x0, y0), (x1, y1) in zip(vertices, vertices[1:] + vertices[:1], strict=True):
        c = x0 * y1 - x1 * y0
        a += c / 2
        sx += (x0 + x1) * c / 6
        sy += (y0 + y1) * c / 6
        iyy += (x0 * x0 + x0 * x1 + x1 * x1) * c / 12
        ixx += (y0 * y0 + y0 * y1 + y1 * y1) * c / 12
        ixy += (x0 * y1 + 2 * x0 * y0 + 2 * x1 * y1 + x1 * y0) * c / 24
    sign = 1.0 if a >= 0 else -1.0
    return sign * a, sign * sx, sign * sy, sign * ixx, sign * iyy, sign * ixy


def _sector_moments(s: Sector) -> Moments:
    d = s.phi2 - s.phi1
    k2, k3, k4 = (s.b**2 - s.a**2) / 2, (s.b**3 - s.a**3) / 3, (s.b**4 - s.a**4) / 4
    a = k2 * d
    sin_d = math.sin(s.phi2) - math.sin(s.phi1)
    cos_d = math.cos(s.phi1) - math.cos(s.phi2)
    sin2_d = math.sin(2 * s.phi2) - math.sin(2 * s.phi1)
    sx = s.cx * a + k3 * sin_d
    sy = s.cy * a + k3 * cos_d
    iyy = s.cx**2 * a + 2 * s.cx * k3 * sin_d + k4 * (d / 2 + sin2_d / 4)
    ixx = s.cy**2 * a + 2 * s.cy * k3 * cos_d + k4 * (d / 2 - sin2_d / 4)
    ixy = s.cx * s.cy * a + s.cx * k3 * cos_d + s.cy * k3 * sin_d + k4 * (math.sin(s.phi2) ** 2 - math.sin(s.phi1) ** 2) / 2
    return a, sx, sy, ixx, iyy, ixy


def _moments(part: Polygon | Sector) -> Moments:
    return _polygon_moments(part.vertices) if isinstance(part, Polygon) else _sector_moments(part)


def _clip_polygon(vertices: tuple[tuple[float, float], ...], axis: int, c: float) -> tuple[tuple[float, float], ...]:
    """Part of a convex polygon with coordinate[axis] <= c (Sutherland-Hodgman, one plane)."""
    out = []
    for p, q in zip(vertices, vertices[1:] + vertices[:1], strict=True):
        p_in, q_in = p[axis] <= c, q[axis] <= c
        if p_in:
            out.append(p)
        if p_in != q_in:
            f = (c - p[axis]) / (q[axis] - p[axis])
            out.append((p[0] + f * (q[0] - p[0]), p[1] + f * (q[1] - p[1])))
    return tuple(out)


def _clip_sector(s: Sector, axis: int, c: float) -> tuple[float, float]:
    """Area and first moment (along axis) of the part of an annular sector with coordinate[axis] <= c."""
    beta = 0.0 if axis == 0 else math.pi / 2       # coordinate = centre + r cos(phi - beta)
    centre = s.cx if axis == 0 else s.cy
    lo, hi = s.phi1 - beta, s.phi2 - beta
    breaks = {s.a, s.b, abs(c - centre)}
    for angle in (lo, hi):
        if abs(math.cos(angle)) > 1e-14:
            breaks.add((c - centre) / math.cos(angle))
    radii = sorted(r for r in breaks if s.a <= r <= s.b)

    def strip(r: float) -> tuple[float, float]:
        k = (c - centre) / r
        if k >= 1:
            pieces = [(lo, hi)]
        elif k <= -1:
            pieces = []
        else:
            g = math.acos(k)
            pieces = [(max(lo, g + 2 * math.pi * m), min(hi, 2 * math.pi - g + 2 * math.pi * m)) for m in (-2, -1, 0, 1)]
        area = moment = 0.0
        for a1, a2 in pieces:
            if a2 > a1:
                area += r * (a2 - a1)
                moment += r * (centre * (a2 - a1) + r * (math.sin(a2) - math.sin(a1)))
        return area, moment

    area = moment = 0.0
    for r0, r1 in zip(radii, radii[1:], strict=False):
        for g, w in _gauss():
            da, dm = strip(r0 + (g + 1) / 2 * (r1 - r0))
            area += w / 2 * (r1 - r0) * da
            moment += w / 2 * (r1 - r0) * dm
    return area, moment


def _clip(part: Polygon | Sector, axis: int, c: float) -> tuple[float, float]:
    if isinstance(part, Sector):
        return _clip_sector(part, axis, c)
    clipped = _clip_polygon(part.vertices, axis, c)
    if len(clipped) < 3:
        return 0.0, 0.0
    m = _polygon_moments(clipped)
    return m[0], m[1 + axis]


def _extent(part: Polygon | Sector, axis: int) -> tuple[float, float]:
    if isinstance(part, Polygon):
        values = [v[axis] for v in part.vertices]
    else:
        centre = part.cx if axis == 0 else part.cy
        trig = math.cos if axis == 0 else math.sin
        angles = [part.phi1, part.phi2] + [k * math.pi / 2 for k in range(-8, 9) if part.phi1 < k * math.pi / 2 < part.phi2]
        values = [centre + r * trig(phi) for r in (part.a, part.b) for phi in angles]
    return min(values), max(values)


def plastic_modulus(geometry: Geometry, axis: int) -> float:
    """∫|u - u_p| dA, u = coordinate[axis], u_p the equal-area (plastic) neutral axis."""
    parts = geometry.parts
    total = [_moments(p) for p in parts]
    area = sum(m[0] for m in total)
    first = sum(m[1 + axis] for m in total)
    lo = min(_extent(p, axis)[0] for p in parts)
    hi = max(_extent(p, axis)[1] for p in parts)
    for _ in range(200):
        mid = (lo + hi) / 2
        if sum(_clip(p, axis, mid)[0] for p in parts) < area / 2:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-13 * (abs(hi) + 1):
            break
    c = (lo + hi) / 2
    a_left = q_left = 0.0
    for p in parts:
        a, q = _clip(p, axis, c)
        a_left += a
        q_left += q
    return (first - q_left - c * (area - a_left)) - (q_left - c * a_left)


def _midline_nodes(geometry: Geometry, t: float, pole: tuple[float, float]) -> list[tuple[float, float, float, float]]:
    """(x, y, t·ds weight, ω) at Gauss nodes; ω = ∫(x - px) dy - (y - py) dx from the first tip."""
    px, py = pole
    out, omega = [], 0.0
    for e in geometry.midline:
        if isinstance(e, Line):
            (x0, y0), (x1, y1) = e.p, e.q
            length = math.hypot(x1 - x0, y1 - y0)
            rate = (x0 - px) * (y1 - y0) - (y0 - py) * (x1 - x0)
            for g, w in _gauss():
                f = (g + 1) / 2
                out.append((x0 + f * (x1 - x0), y0 + f * (y1 - y0), w / 2 * length * t, omega + f * rate))
            omega += rate
        else:
            def d_omega(phi: float, a: Arc = e) -> float:
                return a.r * ((a.cx - px) * (math.sin(phi) - math.sin(a.phi0)) - (a.cy - py) * (math.cos(phi) - math.cos(a.phi0))
                              + a.r * (phi - a.phi0))
            for g, w in _gauss():
                phi = e.phi0 + (g + 1) / 2 * e.sweep
                out.append((e.cx + e.r * math.cos(phi), e.cy + e.r * math.sin(phi), w / 2 * e.r * abs(e.sweep) * t,
                            omega + d_omega(phi)))
            omega += d_omega(e.phi0 + e.sweep)
    return out


def _sectorial(geometry: Geometry, t: float) -> dict[str, float]:
    """Shear centre, Cw and j on the midline, referred to the midline centroid."""
    raw = _midline_nodes(geometry, t, (0.0, 0.0))
    am = sum(w for _, _, w, _ in raw)
    xm = sum(x * w for x, _, w, _ in raw) / am
    ym = sum(y * w for _, y, w, _ in raw) / am
    nodes = [(x - xm, y - ym, w, om) for x, y, w, om in _midline_nodes(geometry, t, (xm, ym))]
    ix = sum(y * y * w for _, y, w, _ in nodes)
    iy = sum(x * x * w for x, _, w, _ in nodes)
    ixy = sum(x * y * w for x, y, w, _ in nodes)
    iwx = sum(om * y * w for _, y, w, om in nodes)
    iwy = sum(om * x * w for x, _, w, om in nodes)
    det = ix * iy - ixy**2
    xs = (iy * iwx - ixy * iwy) / det
    ys = (ixy * iwx - ix * iwy) / det
    shifted = [(om - xs * y + ys * x, w) for x, y, w, om in nodes]
    mean = sum(om * w for om, w in shifted) / am
    cw = sum((om - mean) ** 2 * w for om, w in shifted)
    j = sum((x**3 + x * y * y) * w for x, y, w, _ in nodes) / (2 * iy) - xs   # Eq. 2.3.1-6
    return {"xs": xs + xm, "ys": ys + ym, "Cw": cw, "j": j}


def gross_properties(geometry: Geometry, t: float) -> dict[str, float]:
    """A, centroid (xc, yc), Ix, Iy, Ixy, J, Cw, xo, yo, j, rx, ry, ro, Zx, Zy and the section extents."""
    total = [sum(v) for v in zip(*(_moments(p) for p in geometry.parts), strict=True)]
    a, sx, sy, ixx, iyy, ixy = total
    xc, yc = sx / a, sy / a
    ix, iy, ixy_c = ixx - a * yc * yc, iyy - a * xc * xc, ixy - a * xc * yc
    sect = _sectorial(geometry, t)
    xo, yo = sect["xs"] - xc, sect["ys"] - yc
    rx, ry = math.sqrt(ix / a), math.sqrt(iy / a)
    x_ext = [_extent(p, 0) for p in geometry.parts]
    return {
        "A": a, "xc": xc, "yc": yc, "Ix": ix, "Iy": iy, "Ixy": ixy_c, "J": a * t * t / 3, "Cw": sect["Cw"],
        "xo": xo, "yo": yo, "j": sect["j"], "rx": rx, "ry": ry, "ro": math.sqrt(rx**2 + ry**2 + xo**2 + yo**2),  # Eq. 2.3.1-7
        "Zx": plastic_modulus(geometry, 1), "Zy": plastic_modulus(geometry, 0),
        "x_min": min(e[0] for e in x_ext), "x_max": max(e[1] for e in x_ext),
    }
