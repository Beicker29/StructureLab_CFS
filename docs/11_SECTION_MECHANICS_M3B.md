# M3B Shear Center and Warping Constant

Milestone 3B extends the non-normative section mechanics without creating a
second geometry model:

```text
SectionGeometry
    -> CenterlineSection                 (M3A, reused unchanged)
       + ComputedSectionProperties       (M3A A/Ix/Iy/Ixy)
    -> AdvancedSectionProperties         (M3B x0/y0/Cw)
```

M3B does not regenerate area, centroid, or gross inertias. It requires the
matching M3A result and rejects mismatched section or geometry identifiers.

## Scope and traversal

The mechanical geometry scope remains exactly the M3A scope: explicit
`C_LIPPED` and `C_UNLIPPED` dimensions, sharp-corner `MIDLINE`, `Ri_mm = 0`,
orthogonal straight segments, and uniform thickness. `OUT_TO_OUT`,
`FLAT_WIDTHS`, bends, arcs, nonzero radii, and nonorthogonal angles remain
unsupported.

`CenterlineSection.primitives` is an ordered contour, not an unordered segment
collection. The M3A builder produces this traversal:

```text
top free edge
    -> top lip, when present
    -> top flange toward web
    -> web from top to bottom
    -> bottom flange away from web
    -> bottom lip, when present
    -> bottom free edge
```

M3B consumes that tuple exactly as stored. It neither sorts nor reverses the
contour to obtain a preferred sign. Adjacent primitives must share their exact
endpoint; shuffled or disconnected contours are rejected.

## Coordinates and shear-center offsets

The canonical x axis is positive from the web toward the flange/lip tips and y
is positive upward. M3A's gross centroid is the origin for M3B coordinates.

`x0_mm` and `y0_mm` are signed offsets from that centroid to the gross-section
shear center:

```text
x_shear_center = x_bar + x0
y_shear_center = y_bar + y0
```

A negative `x0` therefore locates the shear center toward or beyond the back
of the web for the current channel orientation. These values have no AISI
interpretation in M3B.

## Sectorial sign and exact integration

For one oriented segment from centroidal node `i` to `j`, the sectorial
increment is:

```text
delta_omega = x_i y_j - x_j y_i
d_omega = x dy - y dx
```

The first node has raw value zero only as an accumulation datum. Raw values are
continuous from one segment to the next. Along a straight segment, x, y, and
omega are linear in its local parameter, so M3B integrates their products as
exact polynomials. For endpoint values `a0/a1` and `b0/b1`:

```text
integral(a b ds) = L (2 a0 b0 + a0 b1 + a1 b0 + 2 a1 b1) / 6
integral(omega ds) = L (omega0 + omega1) / 2
integral(omega^2 ds) = L (omega0^2 + omega0 omega1 + omega1^2) / 3
```

Uniform thickness is applied once through `dA = t ds`. No mesh, quadrature,
sample count, or pyCUFSM routine is used.

## Shear-center equations

From the raw centroid-pole field, M3B calculates:

```text
Iomega_x = integral(omega x dA)
Iomega_y = integral(omega y dA)
Delta = Ix Iy - Ixy^2

x0 = (Iy Iomega_y - Ixy Iomega_x) / Delta
y0 = -(Ix Iomega_x - Ixy Iomega_y) / Delta
```

The M3A convention `Ixy = integral(x y dA)` has no leading minus sign. A
near-degenerate `Delta` is rejected rather than divided. The only explicit
degenerate benchmark convention is a single straight strip: its pole is set at
its centroid and `x0 = y0 = Cw = 0`. Multi-segment degenerate contours remain
invalid.

## Shear-pole sectorial field and normalization

After obtaining the offsets, M3B recomputes sectorial increments about the
shear-center pole:

```text
xs = x - x0
ys = y - y0
d_omega_s = xs dys - ys dxs
```

The resulting field is then shifted by its area-weighted mean:

```text
omega_mean = integral(omega_s dA) / A
omega_n = omega_s - omega_mean
integral(omega_n dA) = 0
```

The final normalized field is not pinned to an arbitrary node. M3B exposes
immutable node values for auditability and future adapter use: centroid-pole
raw, shear-pole raw, and normalized sectorial coordinates.

The warping constant is integrated exactly:

```text
Cw = integral(omega_n^2 dA) = integral(omega_n^2 t ds)
```

Sectorial coordinates have units `mm^2`, `Iomega_x/Iomega_y` have units
`mm^5`, and `Cw` has units `mm^6`.

## Independent analytical benchmarks

The expected values below were derived independently with rational arithmetic
from the stated contour nodes and exact segment formulas. Tests contain the
final constants and do not call production mechanics to generate them.

### Straight strip

A single segment through its centroid has zero sectorial increments. Under the
explicit strip convention:

```text
x0 = 0
y0 = 0
Cw = 0
```

### Symmetric unlipped channel

For `H=100 mm`, `B1=B2=40 mm`, and `t=1 mm`, the ordered absolute nodes are
`(40,50)`, `(0,50)`, `(0,-50)`, `(40,-50)`. Independent line integration gives:

```text
x_bar = 80/9 mm
Ix = 850000/3 mm^4
Iy = 256000/9 mm^4
Ixy = 0

raw omega nodes = [0, 2000, 26000/9, 44000/9] mm^2
Iomega_x = 0
Iomega_y = -176000000/27 mm^5

x0 = -3520/153 mm
y0 = 0
x_shear_center from web = x_bar + x0 = -240/17 mm

normalized omega nodes =
    [-22000/17, 12000/17, -12000/17, 22000/17] mm^2
Cw = 2560000000/51 mm^6
```

The absolute shear-center result is also obtained by the independently
simplified thin-wall channel expression
`x_shear_center = -3 B^2 / (H + 6 B)` for this documented datum.

### Symmetric lipped channel

For the M3A `C200x70x20x2` sharp-corner benchmark, the ordered nodes are
`(70,80)`, `(70,100)`, `(0,100)`, `(0,-100)`, `(70,-100)`, `(70,-80)` and
`t=2 mm`. Independent exact integration gives:

```text
x_bar = 385/19 mm
Iomega_x = 0
Iomega_y = -14260960000/57 mm^5
x0 = -891310/17043 mm
y0 = 0
omega_mean = 5236000/897 mm^2
Cw = 11894750000000/2691 mm^6
```

Translation, x mirroring, and uniform scaling are also tested. Centroid-relative
offsets and `Cw` are translation invariant; x mirroring changes the sign of
`x0`, preserves `y0`, and preserves `Cw`; uniform scaling by lambda produces
`x0/y0 ~ lambda` and `Cw ~ lambda^6`.

## Catalog verification and limitations

The existing verification policy now accepts `x0`, `y0`, and `Cw`. It compares
an `AdvancedSectionProperties` result only when requested. A missing catalog
value remains `NOT_CHECKED`; it is never converted to zero and neither catalog
nor computed values are overwritten.

The two approved illustrative catalog rows omit all three advanced properties,
so their advanced checks correctly remain `NOT_CHECKED` even though M3B can
calculate the mechanics values.

M3B does not implement curved bends, arbitrary open sections, closed sections,
shear design, AISI provisions, EWM, DSM, elastic buckling, ETABS, project
loading, or pyCUFSM. A future validation milestone may compare results against
`pycufsm.pre.cutwp.prop2` as an independent implementation; no CUTWP source or
runtime dependency is present here.
