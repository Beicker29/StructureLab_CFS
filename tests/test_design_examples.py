"""docs/validation-yu-2019.md is generated from tests/contrast/yu_2019.py and must match the current code.

The contrast is not an oracle: differences are adjudicated by the user in the report. This test only
guarantees that the report shows what the code computes today (regenerate it after a calculation change).
"""
from tests.contrast import yu_2019


def _without_verdicts(text: str) -> list[str]:
    """Report lines with the user's Dictamen column blanked, so verdicts do not break the comparison."""
    out = []
    for line in text.splitlines():
        cells = line.split("|")
        if len(cells) == 10 and cells[1].strip() not in {"Magnitud", "---"}:
            cells[8] = " "
        out.append("|".join(cells))
    return out


def test_validation_report_is_current():
    assert _without_verdicts(yu_2019.OUTPUT.read_text(encoding="utf-8")) == _without_verdicts(yu_2019.render()), \
        "regenerate with: python tests/contrast/yu_2019.py"
