"""Shared physical-input and demand fixtures for M10."""

from dataclasses import replace

import pytest

from cfs_design.design import MemberDesignInput
from cfs_design.design.comparison import AxialDemandContext
from cfs_design.domain import (
    DemandCombination,
    DemandPoint,
    DemandSet,
    DesignMethod,
    RunMode,
    SectionDemandCombination,
    SectionDemandPoint,
    SectionDemandSet,
    SectionFamily,
)
from cfs_design.normative import (
    DesignAction,
    DesignExecutionPurpose,
    evaluate_design_eligibility,
)
from cfs_design.workflows import AxialCompressionDesignRequest
from tests.design.dsm.conftest import make_m9a_result
from tests.design.ewm.conftest import make_design_input


def make_m10_request(
    *,
    run_mode: RunMode = RunMode.COMPARE,
    p_n: float = 10_000.0,
    family: SectionFamily = SectionFamily.C_LIPPED,
    length_mm: float = 500.0,
    local_status=None,
    distortional_status=None,
    p_crl_n: float = 100_000.0,
    p_crd_n: float = 100_000.0,
    selection_family=None,
) -> AxialCompressionDesignRequest:
    base = make_design_input(family=family, length_mm=length_mm)
    source_point = DemandPoint(
        point_id="ETABS-LC1-001",
        p_n=p_n,
        v2_n=0.0,
        v3_n=0.0,
        t_nmm=0.0,
        m2_nmm=0.0,
        m3_nmm=0.0,
        station_mm=250.0,
        step_type="Max",
        element_id="E1",
        element_station_mm=250.0,
        location="Interior",
    )
    section_point = SectionDemandPoint(
        point_id="SECTION-ETABS-LC1-001",
        source_point_id=source_point.point_id,
        p_n=p_n,
        vx_n=0.0,
        vy_n=0.0,
        t_nmm=0.0,
        mx_nmm=0.0,
        my_nmm=0.0,
        station_mm=source_point.station_mm,
        step_type=source_point.step_type,
        element_id=source_point.element_id,
        element_station_mm=source_point.element_station_mm,
        location=source_point.location,
    )
    source_demands = DemandSet(
        combinations=(
            DemandCombination(
                combination_id="LC1",
                case_type="Combination",
                points=(source_point,),
            ),
        )
    )
    section_demands = SectionDemandSet(
        combinations=(
            SectionDemandCombination(
                combination_id="LC1",
                case_type="Combination",
                points=(section_point,),
            ),
        )
    )
    member = replace(
        base.resolved_member,
        demands=section_demands,
        source_demands=source_demands,
    )
    methods = {
        RunMode.EWM: (DesignMethod.EWM,),
        RunMode.DSM: (DesignMethod.DSM,),
        RunMode.COMPARE: (DesignMethod.EWM, DesignMethod.DSM),
    }[run_mode]
    context = replace(base.design_context, methods=methods, run_mode=run_mode)

    def method_input(method: DesignMethod) -> MemberDesignInput:
        eligibility = evaluate_design_eligibility(
            member=member,
            context=context,
            method=method,
            action=DesignAction.AXIAL_COMPRESSION,
            scope_evidence=base.scope_evidence,
            material_qualification=base.material_qualification,
            purpose=DesignExecutionPurpose.DEMAND_CHECK,
        )
        return MemberDesignInput(
            resolved_member=member,
            section_mechanics=base.section_mechanics,
            standard_dimensions=base.standard_dimensions,
            material_qualification=base.material_qualification,
            design_context=context,
            scope_evidence=base.scope_evidence,
            method=method,
            action=DesignAction.AXIAL_COMPRESSION,
            purpose=DesignExecutionPurpose.DEMAND_CHECK,
            eligibility=eligibility,
        )

    ewm_input = method_input(DesignMethod.EWM) if DesignMethod.EWM in methods else None
    dsm_input = method_input(DesignMethod.DSM) if DesignMethod.DSM in methods else None
    demand = AxialDemandContext(
        project_id="SYNTHETIC_M10",
        case_id=member.member.case_id,
        section_id=member.section.catalog_section.section_id,
        material_id=member.material.material_id,
        combination_id="LC1",
        case_type="Combination",
        point=section_point,
    )
    elastic = None
    if dsm_input is not None:
        kwargs = {
            "p_crl_n": p_crl_n,
            "p_crd_n": p_crd_n,
            "selection_family": selection_family,
        }
        if local_status is not None:
            kwargs["local_status"] = local_status
        if distortional_status is not None:
            kwargs["distortional_status"] = distortional_status
        elastic = make_m9a_result(dsm_input, **kwargs)
    return AxialCompressionDesignRequest(
        project_id=demand.project_id,
        run_mode=run_mode,
        demand=demand,
        ewm_input=ewm_input,
        dsm_input=dsm_input,
        elastic_buckling=elastic,
    )


@pytest.fixture
def m10_request_factory():
    return make_m10_request

