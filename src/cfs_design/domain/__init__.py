"""Selection and calculation per chapter, applicability (Table B4.1-1) and coverage of obligations."""
from dataclasses import dataclass
from typing import Any

from ..materials import Material
from ..models import MemberInput
from ..sections import SectionProperties


@dataclass(frozen=True)
class DesignContext:
    """Member data resolved once by the engine and shared by every check."""

    member: MemberInput
    material: Material
    section: SectionProperties
    buckling: dict[str, Any]
