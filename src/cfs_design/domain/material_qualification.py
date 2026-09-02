"""Standard-edition-specific material qualification evidence."""

from dataclasses import dataclass
from enum import Enum

from cfs_design.core.exceptions import ValidationError

from ._validation import (
    require_enum,
    require_non_empty,
    require_optional_non_negative,
    require_optional_positive,
    require_optional_string,
)
from .material import Material


class MaterialQualificationRoute(str, Enum):
    A3_1 = "A3_1"
    A3_2 = "A3_2"


class MaterialQualificationState(str, Enum):
    QUALIFIED = "QUALIFIED"
    NOT_QUALIFIED = "NOT_QUALIFIED"
    INDETERMINATE = "INDETERMINATE"


class MaterialProductForm(str, Enum):
    SHEET = "SHEET"
    STRIP = "STRIP"
    PLATE = "PLATE"
    BAR = "BAR"
    UNKNOWN = "UNKNOWN"


class SteelClassification(str, Enum):
    CARBON = "CARBON"
    LOW_ALLOY = "LOW_ALLOY"
    UNKNOWN = "UNKNOWN"


class A3ElongationGroup(str, Enum):
    A3_1_1_GE_10 = "A3_1_1_GE_10"
    A3_1_2_GE_3_LT_10 = "A3_1_2_GE_3_LT_10"
    A3_1_3_LT_3 = "A3_1_3_LT_3"
    A3_2_1_ALTERNATIVE_DUCTILITY = "A3_2_1_ALTERNATIVE_DUCTILITY"
    UNKNOWN = "UNKNOWN"


class QualificationRequirementState(str, Enum):
    SATISFIED = "SATISFIED"
    NOT_SATISFIED = "NOT_SATISFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


_ASTM_ELONGATION_TESTS = frozenset({"ASTM_A370", "ASTM_A1058"})


@dataclass(frozen=True, slots=True)
class StandardMaterialQualification:
    """Auditable A3 evidence without duplicating the physical Material record."""

    material_id: str
    standard_id: str
    standard_edition: int
    qualification_route: MaterialQualificationRoute
    qualification_state: MaterialQualificationState
    product_form: MaterialProductForm
    steel_classification: SteelClassification
    elongation_group: A3ElongationGroup
    minimum_elongation_percent: float | None
    elongation_gauge_length_mm: float | None
    elongation_test_standard: str | None
    mandatory_mechanical_properties_state: QualificationRequirementState
    test_reports_required_state: QualificationRequirementState
    chemical_mechanical_conformance_state: QualificationRequirementState
    properties_determined_per_reference_state: QualificationRequirementState
    coating_requirements_state: QualificationRequirementState
    welding_requirements_state: QualificationRequirementState
    production_identification_state: QualificationRequirementState
    master_coil_10_percent_overstrength_state: QualificationRequirementState
    local_elongation_percent: float | None
    uniform_elongation_percent: float | None
    ductility_test_standard: str | None
    source_id: str
    basis: str
    notes: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("material_id", "standard_id", "source_id", "basis"):
            require_non_empty(getattr(self, field_name), field_name)
        if (
            isinstance(self.standard_edition, bool)
            or not isinstance(self.standard_edition, int)
            or self.standard_edition <= 0
        ):
            raise ValidationError("standard_edition must be a positive integer")
        for field_name, enum_type in (
            ("qualification_route", MaterialQualificationRoute),
            ("qualification_state", MaterialQualificationState),
            ("product_form", MaterialProductForm),
            ("steel_classification", SteelClassification),
            ("elongation_group", A3ElongationGroup),
            (
                "mandatory_mechanical_properties_state",
                QualificationRequirementState,
            ),
            ("test_reports_required_state", QualificationRequirementState),
            (
                "chemical_mechanical_conformance_state",
                QualificationRequirementState,
            ),
            (
                "properties_determined_per_reference_state",
                QualificationRequirementState,
            ),
            ("coating_requirements_state", QualificationRequirementState),
            ("welding_requirements_state", QualificationRequirementState),
            ("production_identification_state", QualificationRequirementState),
            (
                "master_coil_10_percent_overstrength_state",
                QualificationRequirementState,
            ),
        ):
            require_enum(getattr(self, field_name), enum_type, field_name)
        require_optional_non_negative(
            self.minimum_elongation_percent, "minimum_elongation_percent"
        )
        require_optional_positive(
            self.elongation_gauge_length_mm, "elongation_gauge_length_mm"
        )
        require_optional_non_negative(
            self.local_elongation_percent, "local_elongation_percent"
        )
        require_optional_non_negative(
            self.uniform_elongation_percent, "uniform_elongation_percent"
        )
        require_optional_string(
            self.elongation_test_standard, "elongation_test_standard"
        )
        require_optional_string(
            self.ductility_test_standard, "ductility_test_standard"
        )
        require_optional_string(self.notes, "notes")
        if self.qualification_state is MaterialQualificationState.QUALIFIED:
            self._validate_qualified_evidence()

    @property
    def key(self) -> tuple[str, str, int]:
        return self.material_id, self.standard_id, self.standard_edition

    def validate_against_material(self, material: Material) -> None:
        """Validate cross-record identity and the A3.1.1 Fu/Fy threshold."""

        if not isinstance(material, Material):
            raise ValidationError("material must be a Material")
        if material.material_id != self.material_id:
            raise ValidationError("qualification material_id does not match Material")
        if (
            self.qualification_state is MaterialQualificationState.QUALIFIED
            and self.elongation_group is A3ElongationGroup.A3_1_1_GE_10
            and material.fu_mpa / material.fy_mpa < 1.08
        ):
            raise ValidationError(
                "A3.1.1 qualified evidence requires Material Fu/Fy >= 1.08"
            )

    def _validate_qualified_evidence(self) -> None:
        if self.product_form is MaterialProductForm.UNKNOWN:
            raise ValidationError("qualified evidence requires a known product_form")
        if self.steel_classification is SteelClassification.UNKNOWN:
            raise ValidationError(
                "qualified evidence requires a known steel_classification"
            )
        if self.elongation_group is A3ElongationGroup.UNKNOWN:
            raise ValidationError("qualified evidence requires an elongation_group")

        if self.qualification_route is MaterialQualificationRoute.A3_1:
            self._require_state(
                "mandatory_mechanical_properties_state",
                QualificationRequirementState.SATISFIED,
            )
            self._require_state(
                "test_reports_required_state",
                QualificationRequirementState.SATISFIED,
            )
            for field_name in (
                "chemical_mechanical_conformance_state",
                "properties_determined_per_reference_state",
                "coating_requirements_state",
                "welding_requirements_state",
                "production_identification_state",
                "master_coil_10_percent_overstrength_state",
            ):
                self._require_state(
                    field_name,
                    QualificationRequirementState.NOT_APPLICABLE,
                )
            if self.elongation_group is A3ElongationGroup.A3_2_1_ALTERNATIVE_DUCTILITY:
                raise ValidationError("A3.2.1 ductility cannot qualify an A3.1 route")
        else:
            for field_name in (
                "mandatory_mechanical_properties_state",
                "test_reports_required_state",
            ):
                self._require_state(
                    field_name,
                    QualificationRequirementState.NOT_APPLICABLE,
                )
            self._validate_a3_2_evidence()

        self._validate_elongation_evidence()

    def _validate_a3_2_evidence(self) -> None:
        for field_name in (
            "chemical_mechanical_conformance_state",
            "properties_determined_per_reference_state",
        ):
            self._require_state(field_name, QualificationRequirementState.SATISFIED)
        for field_name in (
            "coating_requirements_state",
            "welding_requirements_state",
        ):
            value = getattr(self, field_name)
            if value not in {
                QualificationRequirementState.SATISFIED,
                QualificationRequirementState.NOT_APPLICABLE,
            }:
                raise ValidationError(
                    f"qualified A3.2 evidence requires {field_name} to be "
                    "SATISFIED or NOT_APPLICABLE"
                )
        production = self.production_identification_state
        if production is QualificationRequirementState.SATISFIED:
            return
        if (
            production is QualificationRequirementState.NOT_SATISFIED
            and self.master_coil_10_percent_overstrength_state
            is QualificationRequirementState.SATISFIED
        ):
            return
        raise ValidationError(
            "qualified A3.2 evidence requires documented production identification "
            "or satisfied master-coil 10-percent overstrength evidence"
        )

    def _validate_elongation_evidence(self) -> None:
        group = self.elongation_group
        if group is A3ElongationGroup.A3_2_1_ALTERNATIVE_DUCTILITY:
            if self.qualification_route is not MaterialQualificationRoute.A3_2:
                raise ValidationError("A3.2.1 ductility requires qualification_route A3_2")
            if self.local_elongation_percent is None or self.local_elongation_percent < 20:
                raise ValidationError("A3.2.1 requires local elongation >= 20 percent")
            if self.uniform_elongation_percent is None or self.uniform_elongation_percent < 3:
                raise ValidationError("A3.2.1 requires uniform elongation >= 3 percent")
            if not self.ductility_test_standard or not self.ductility_test_standard.strip():
                raise ValidationError("A3.2.1 requires a ductility test standard")
            if any(
                value is not None
                for value in (
                    self.minimum_elongation_percent,
                    self.elongation_gauge_length_mm,
                    self.elongation_test_standard,
                )
            ):
                raise ValidationError(
                    "A3.2.1 evidence must not mix A3.1 elongation fields"
                )
            return

        if any(
            value is not None
            for value in (
                self.local_elongation_percent,
                self.uniform_elongation_percent,
                self.ductility_test_standard,
            )
        ):
            raise ValidationError(
                "A3.1 elongation groups must not mix A3.2.1 ductility fields"
            )

        elongation = self.minimum_elongation_percent
        gauge = self.elongation_gauge_length_mm
        test_standard = self.elongation_test_standard
        if elongation is None or gauge is None or not test_standard:
            raise ValidationError(
                "qualified A3.1 elongation groups require elongation, gauge length, "
                "and test standard"
            )
        if test_standard not in _ASTM_ELONGATION_TESTS:
            raise ValidationError(
                "elongation_test_standard must be ASTM_A370 or ASTM_A1058"
            )
        if group is A3ElongationGroup.A3_1_1_GE_10:
            valid = (gauge == 50.0 and elongation >= 10.0) or (
                gauge == 200.0 and elongation >= 7.0
            )
            if not valid:
                raise ValidationError(
                    "A3.1.1 requires >=10 percent at 50 mm or >=7 percent at 200 mm"
                )
        elif group is A3ElongationGroup.A3_1_2_GE_3_LT_10:
            if gauge != 50.0 or not 3.0 <= elongation < 10.0:
                raise ValidationError(
                    "A3.1.2 requires 3 to less than 10 percent at 50 mm"
                )
        elif group is A3ElongationGroup.A3_1_3_LT_3:
            if gauge != 50.0 or not elongation < 3.0:
                raise ValidationError("A3.1.3 requires less than 3 percent at 50 mm")

    def _require_state(
        self,
        field_name: str,
        expected: QualificationRequirementState,
    ) -> None:
        if getattr(self, field_name) is not expected:
            raise ValidationError(
                f"qualified {self.qualification_route.value} evidence requires "
                f"{field_name}={expected.value}"
            )


__all__ = [
    "A3ElongationGroup",
    "MaterialProductForm",
    "MaterialQualificationRoute",
    "MaterialQualificationState",
    "QualificationRequirementState",
    "StandardMaterialQualification",
    "SteelClassification",
]
