"""Elastic buckling (M2), AISI S100-24 Appendix 2.3.

No independent oracle yet (DC-10): these tests check transcription identities, limiting cases and
selection, not normative accuracy against the AISI Manual or CUFSM.
"""
import math

import pytest

from cfs_design.codes.aisi_s100_24 import appendix_2 as a2
from cfs_design.execution import execute_payload


@pytest.fixture
def c_member(member_payload):
    return {**member_payload, "flexure": {"Cb": 1.0}, "buckling": {"Lm": 1000}}


def _buckling(payload):
    return execute_payload(payload)["buckling"]


def test_z_column_of_table_2_3_3_1_at_90_degrees_equals_c_column():
    c = a2.flange_properties_c(60.0, 18.0, 2.0)
    z = a2.flange_properties_z(60.0, 18.0, 2.0, math.pi / 2)
    for name in c.__dataclass_fields__:
        assert getattr(z, name) == pytest.approx(getattr(c, name), rel=1e-12, abs=1e-9), name


def test_table_2_3_3_1_c_column_by_hand():
    f = a2.flange_properties_c(60.0, 18.0, 2.0)
    assert f.Af == 156.0 and f.Jf == pytest.approx((60 + 18) * 8 / 3)
    assert f.xof == pytest.approx(3600 / 156) and f.xhf == pytest.approx(-(3600 + 2160) / 156)
    assert f.yhf == f.yof == pytest.approx(-324 / 156)


def test_compression_and_flexure_geometric_stiffness_are_distinct_equations():
    """Eq. 2.3.3.1-5 carries (xof − xhf)²(Ixyf/Iyf)²; Eq. 2.3.3.2-6 does not (not merged)."""
    f = a2.flange_properties_c(60.0, 18.0, 2.0)
    extra = (math.pi / 500) ** 2 * f.Af * (f.xof - f.xhf) ** 2 * (f.Ixyf / f.Iyf) ** 2
    assert a2.k_phi_fg_compression(f, 500) - a2.k_phi_fg_flexure(f, 500) == pytest.approx(extra, rel=1e-12)


@pytest.mark.parametrize("lcrd_fn, fcrd_fn", [
    (lambda f, t, ho: a2.lcrd_compression(f, t, ho),
     lambda f, t, ho, ld: a2.fcrd_compression(a2.k_phi_fe(f, ld), a2.k_phi_we_compression(t, ho), 0.0,
                                              a2.k_phi_fg_compression(f, ld), a2.k_phi_wg_compression(t, ho, ld))),
])
def test_lcrd_is_close_to_the_minimum_of_fcrd(lcrd_fn, fcrd_fn):
    f, t, ho = a2.flange_properties_c(62.0, 15.0, 1.5), 1.5, 203.0
    lcrd = lcrd_fn(f, t, ho)
    fcrd = fcrd_fn(f, t, ho, lcrd)
    assert fcrd <= fcrd_fn(f, t, ho, 0.8 * lcrd) and fcrd <= fcrd_fn(f, t, ho, 1.25 * lcrd)


def test_compression_global_selects_the_smallest_mode(c_member):
    b = _buckling(c_member)["compression"]["global"]
    assert b["value"] == min(b["modes_kN"].values()) and b["mode"] == "flexural_torsional"
    # Eq. 2.3.1.1.2-1 never exceeds Pex, so about x the C always buckles flexural-torsionally;
    # long Ly with short Lx and Lz: flexural buckling about y by Eq. 2.3.1.1.1-1
    long_y = _buckling({**c_member, "lengths": {"Lx": 300, "Ly": 9000, "Lz": 300}})
    section = execute_payload(c_member)["section"]["properties"]
    euler = math.pi**2 * a2.E * section["Iy"] / 9000**2 / 1e3
    assert long_y["compression"]["global"]["mode"] == "flexural_y"
    assert long_y["compression"]["global"]["value"] == pytest.approx(euler, rel=1e-12)
    modes = b["modes_kN"]
    assert modes["flexural_torsional"] <= modes["flexural_x"]


def test_z_compression_checks_the_minor_principal_axis():
    payload = {"section": {"name": "PHR Z203x67x19-2.0"}, "material": "ASTM A653 SS Grade 50 Class 1",
               "lengths": {"Lx": 3000, "Ly": 3000, "Lz": 3000}, "buckling": {"Lm": 3000}, "cases": [{"name": "c", "Pu": 10}]}
    result = execute_payload(payload)
    g = result["buckling"]["compression"]["global"]
    i2 = result["section"]["properties"]["I2"]
    assert set(g["modes_kN"]) == {"flexural_x", "flexural_y", "torsional", "flexural_minor_principal"}
    assert g["modes_kN"]["flexural_minor_principal"] == pytest.approx(math.pi**2 * a2.E * i2 / 3000**2 / 1e3, rel=1e-12)
    assert g["mode"] == "flexural_minor_principal"


def test_local_buckling_coefficients(c_member):
    b = _buckling(c_member)
    comp = b["compression"]["local"]["elements"]
    assert (comp["web"]["k"], comp["flange"]["k"], comp["lip"]["k"]) == (4.0, 4.0, 0.43)
    web = b["flexure_x"]["local"]["elements"]["web"]
    assert web["k"] == pytest.approx(24.0) and web["k_source"] == "Eq. 1.1.2-2"     # pure bending, psi = 1
    assert b["flexure_x"]["local"]["elements"]["lip"]["k_source"] == "Eq. 1.2.2-2"


def test_distortional_moment_uses_sx_and_is_reported_with_its_assumptions(c_member):
    result = execute_payload(c_member)
    d = result["buckling"]["flexure_x"]["distortional"]
    assert d["value"] == pytest.approx(result["section"]["properties"]["Sx"] * d["stress_MPa"] / 1e6, rel=1e-12)
    assert d["xi_web"] == pytest.approx(2.0) and d["beta"] == 1.0
    assert result["buckling"]["k_phi"]["value_N_mm_per_mm_rad"] == 0.0
    assert "conservatively" in result["buckling"]["k_phi"]["source"]


def test_rotational_restraint_raises_distortional_buckling(c_member):
    free = _buckling(c_member)["compression"]["distortional"]["value"]
    braced = _buckling({**c_member, "buckling": {"Lm": 1000, "k_phi": 500.0}})
    assert braced["compression"]["distortional"]["value"] > free
    assert braced["k_phi"]["source"] == "input"


def test_continuous_restraint_without_lm_takes_lm_as_lcrd(c_member):
    d = _buckling({**c_member, "buckling": {"k_phi": 500.0}})["compression"]["distortional"]
    assert d["Lm_mm"] == d["Lcrd_mm"] == d["Ld_mm"]


@pytest.mark.parametrize("change, group, key, missing", [
    ({"buckling": {}}, "compression", "distortional", "Lm"),
    ({"flexure": None}, "flexure_x", "global", "Cb"),
    ({"lengths": {"Lx": 3000, "Ly": 1000}}, "compression", "global", "KtLt"),
])
def test_missing_data_blocks_only_that_quantity(c_member, change, group, key, missing):
    b = _buckling({**c_member, **change})
    assert b[group][key]["error"]["code"] == "INCOMPLETE_DATA"
    assert missing in b[group][key]["error"]["details"]["missing"]
    assert "value" in b["compression"]["local"]


def test_cases_outside_the_analytical_solutions_are_incomplete(c_member):
    c = _buckling(c_member)
    assert c["flexure_y_web_compression"]["distortional"]["error"]["details"]["decision"] == "D8"
    assert "value" in c["flexure_y_tips_compression"]["distortional"]
    z = _buckling({**c_member, "section": {"name": "PHR Z203x67x19-2.0"}})
    for key in ("global", "local", "distortional"):
        assert z["flexure_y_tips_compression"][key]["error"]["code"] == "RULE_NOT_IMPLEMENTED"
    assert "value" in z["flexure_x"]["distortional"]


def test_mcre_about_y_is_larger_with_compression_on_the_shear_centre_side(c_member):
    b = _buckling(c_member)
    assert b["flexure_y_web_compression"]["global"]["value"] > b["flexure_y_tips_compression"]["global"]["value"]


def test_finite_strip_is_not_available_yet(c_member):
    b = _buckling({**c_member, "buckling": {"source": "fsm"}})
    assert b["error"]["details"]["milestone"] == "M8"
