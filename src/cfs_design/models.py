"""Input (MemberInput, CaseDemand) and result (DesignResult) models. Units: mm, MPa, kN, kN·m.

Input policy: unknown keys are rejected; a section is given by catalog name or by geometry,
never by loose properties; a material is a catalog name, never loose Fy/Fu numbers.
Shape-specific required dimensions are checked by sections/.
"""
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Method = Literal["DSM", "EWM", "both"]
BucklingSource = Literal["analytical", "fsm"]
ShapeKind = Literal["C_LIPPED", "C_UNLIPPED", "Z_LIPPED", "HAT", "ANGLE", "ANGLE_LIPPED", "SIGMA"]


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SectionInput(_Strict):
    """Catalog `name`, or `shape` with out-to-out dimensions (DC-3): H depth, B flange, D lip, t design thickness,
    R inside bend radius, lip_angle between lip and flange in degrees (D3: required for Z_LIPPED, 90 for C_LIPPED)."""

    name: str | None = None
    shape: ShapeKind | None = None
    H: float | None = Field(default=None, gt=0)
    B: float | None = Field(default=None, gt=0)
    D: float | None = Field(default=None, gt=0)
    t: float | None = Field(default=None, gt=0)
    R: float | None = Field(default=None, ge=0)
    lip_angle: float | None = Field(default=None, gt=0, le=90)

    @model_validator(mode="after")
    def _name_xor_shape(self) -> "SectionInput":
        if (self.name is None) == (self.shape is None):
            raise ValueError("section needs exactly one of `name` (catalog) or `shape` (geometry)")
        if self.name is not None and any(v is not None for v in (self.H, self.B, self.D, self.t, self.R, self.lip_angle)):
            raise ValueError("a catalog section takes no dimensions")
        if self.shape is not None and self.t is None:
            raise ValueError("a geometric section needs the thickness `t`")
        return self


class Lengths(_Strict):
    """Unbraced lengths (mm) about x, y and for twisting."""

    Lx: float | None = Field(default=None, gt=0)
    Ly: float | None = Field(default=None, gt=0)
    Lz: float | None = Field(default=None, gt=0)


class Factors(_Strict):
    Kx: float = Field(default=1.0, gt=0)
    Ky: float = Field(default=1.0, gt=0)
    Kt: float = Field(default=1.0, gt=0)


class BucklingInput(_Strict):
    """Origin of the elastic critical loads (DC-2). With `fsm`, optional half-wavelengths (mm) for local and distortional."""

    source: BucklingSource = "analytical"
    local_half_wavelength: float | None = Field(default=None, gt=0)
    distortional_half_wavelength: float | None = Field(default=None, gt=0)


class FlexureInput(_Strict):
    Cb: float | None = Field(default=None, gt=0)
    Lm: float | None = Field(default=None, gt=0)
    inelastic_reserve: bool = False


class WebCripplingInput(_Strict):
    N: float = Field(gt=0)
    load_case: Literal["EOF", "IOF", "ETF", "ITF"]
    fastened: bool


DEMAND_FIELDS = ("Pu", "Mux", "Muy", "Vux", "Vuy", "Pw", "Bu")


class CaseDemand(_Strict):
    """One LRFD combination. Pu > 0 compression, < 0 tension (kN); M in kN·m; V, Pw in kN; Bu in kN·m²."""

    name: str
    Pu: float = 0.0
    Mux: float = 0.0
    Muy: float = 0.0
    Vux: float = 0.0
    Vuy: float = 0.0
    Pw: float = 0.0
    Bu: float = 0.0

    @model_validator(mode="after")
    def _has_demand(self) -> "CaseDemand":
        if all(getattr(self, f) == 0 for f in DEMAND_FIELDS):
            raise ValueError(f"case '{self.name}' has no demand")
        return self


class MemberInput(_Strict):
    """One file per member: member data at top level and its load combinations in `cases`."""

    section: SectionInput
    material: str
    lengths: Lengths = Lengths()
    factors: Factors = Factors()
    method: Method = "DSM"
    buckling: BucklingInput = BucklingInput()
    flexure: FlexureInput | None = None
    web_crippling: WebCripplingInput | None = None
    cases: list[CaseDemand] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_case_names(self) -> "MemberInput":
        names = [c.name for c in self.cases]
        if len(names) != len(set(names)):
            raise ValueError("case names must be unique")
        return self


class Check(BaseModel):
    """One check per demand (or interaction). capacity is φRn when computed."""

    model_config = ConfigDict(frozen=True)

    check: str
    chapter: str
    demand: float
    status: Status
    capacity: float | None = None
    ratio: float | None = None
    method: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class CaseResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    status: Status
    ratio: float | None
    checks: list[Check]


class DesignResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Status
    ratio: float | None
    governing: str | None
    material: dict[str, Any]
    section: dict[str, Any] | None = None
    cases: list[CaseResult]
    errors: list[dict[str, Any]] = Field(default_factory=list)
