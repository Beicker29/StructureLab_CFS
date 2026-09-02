# M3A Section Geometry and Gross Properties

Milestone 3A introduces a non-normative mechanics path for basic gross
properties only:

```text
SectionGeometry
    -> CenterlineSection
    -> ComputedSectionProperties
    -> CatalogVerificationResult
```

`CenterlineSection` is the single canonical mechanical geometry. The gross
property engine consumes it and does not rebuild a section. Future EWM and
pyCUFSM work must reuse this boundary rather than add method-specific geometry
builders.

## Exact geometry-convention support

M3A gives `MIDLINE` the following deliberately narrow meaning:

- `H_mm` is the full straight web-centerline length between ideal sharp corner
  vertices. The initial origin is its midpoint, so the web runs from
  `(0, -H/2)` to `(0, +H/2)`.
- `B1_mm` is the straight top-flange centerline length from the web vertex
  toward positive x. `B2_mm` is the corresponding bottom-flange length.
- For `C_LIPPED`, `D1_mm` is the top lip centerline length directed downward,
  and `D2_mm` is the bottom lip length directed upward.
- Adjacent segments share an endpoint. That zero-measure vertex is not an arc
  and does not duplicate material length or area.
- `B2_mm`, and both lip dimensions for lipped sections, must be explicit. M3A
  does not infer missing dimensions from symmetry.

This support is restricted to `Ri_mm = 0`, 90-degree web-flange angles, and
90-degree flange-lip angles for lipped sections. It exactly represents the two
inactive illustrative sharp-corner rows in the approved catalog.

`FLAT_WIDTHS` and `OUT_TO_OUT` remain valid schema enum values but are
`UNSUPPORTED` by the M3A builder. The repository does not yet define whether
their dimensions include thickness, where their bend tangent points lie, or
how each dimension is reduced to a centerline segment. They are never treated
as aliases for `MIDLINE`.

The catalog defines `Ri_mm` as an inside bend radius, and a future curved
centerline could use `Rc = Ri + t/2`. M3A does not apply that expression because
the required H/B/D tangent and cutback meanings are not documented. A nonzero
radius therefore raises `UnsupportedFeatureError`; there is no `CircularArc`
or bend approximation in M3A.

## Coordinates and signs

- x is horizontal and positive from the web toward flange and lip tips.
- y is vertical and positive upward.
- Positive angular rotation is counter-clockwise from +x.
- The product of inertia is
  `Ixy = integral((x - x_bar)(y - y_bar) dA)`, with no leading minus sign.
- `theta_p` is the rotation from +x to the axis associated with `I1`, reported
  in `[-90, 90)` degrees. `I1` is the major and `I2` the minor principal
  inertia. With the stated `Ixy` sign, the implementation uses
  `theta_p = 0.5 atan2(-2 Ixy, Ix - Iy)`.

Centroidal properties are calculated from coordinates and remain invariant
under a translation of the initial datum.

## Thin-wall formulation

All inputs and outputs use millimetres and their powers. For each analytical
straight centerline segment, M3A integrates with:

```text
dA = t ds
A = t sum(L)
Ix = integral((y - y_bar)^2 dA)
Iy = integral((x - x_bar)^2 dA)
Ixy = integral((x - x_bar)(y - y_bar) dA)
```

The line integrals are exact polynomials; there is no mesh or discretization
parameter. Consistent with the approved illustrative catalog rows, local plate
second moments proportional to `t^3` are omitted from `Ix`, `Iy`, and `Ixy`.
Thickness remains authoritative on `CenterlineSection` and is not duplicated
on every primitive.

The elastic section moduli use centerline endpoint extents:

```text
Sx_pos = Ix / (y_max - y_bar)
Sx_neg = Ix / (y_bar - y_min)
Sy_pos = Iy / (x_max - x_bar)
Sy_neg = Iy / (x_bar - x_min)
```

Thus the M3A finite-thickness rule is explicitly `CENTERLINE_EXTENTS`: no
`t/2` is added beyond a free edge. This is a documented thin-wall convention,
not an outer-fiber reconstruction.

Radii of gyration are derived from computed values. For the uniform open wall,
the Saint-Venant torsion constant is:

```text
J = sum(L t^3 / 3)
```

The M3A gross-property layer itself does not calculate shear-center coordinates
or warping constant `Cw`; M3B now derives those in a separate advanced result
from this same centerline and the completed M3A properties. Effective widths,
buckling, resistance, and utilization remain unimplemented.

## Catalog verification

`SectionProperties` remains the immutable catalog claim and
`ComputedSectionProperties` remains the immutable mechanics result. Verification
receives both through a resolved section and never recalculates either one.

For catalog reference value `c`, the PASS limit is:

```text
pass_limit = max(absolute_tolerance, relative_tolerance * abs(c))
```

The explicit `warning_multiplier` defines a wider WARNING band. A difference
within the pass limit is `PASS`, one between the pass and warning limits is
`WARNING`, and one beyond the warning limit is `FAIL`. A missing optional
catalog value is `NOT_CHECKED`. Overall precedence is FAIL, WARNING, PASS,
then NOT_CHECKED.

Relative difference uses `max(abs(c), absolute_tolerance)` as its denominator.
If both are zero, exact equality reports zero and a nonzero difference reports
no relative value rather than infinity. Principal-axis angles are compared
modulo 180 degrees.

Tolerance values are supplied through `VerificationPolicy`; property
calculation contains no project tolerance. M3A does not yet load that policy
from `project.yaml`.
