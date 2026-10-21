"""Receipt-only synthetic scope gates; no scientific data or numerical imports."""
import copy
import pytest
from contributor_tools import restore_um21_planar_scopes as t


def fixture():
    p={'kind':'stairs','baseline':'/synthetic/baseline','expected_records':1,'expected_observations':2,'field_mapping':t.MAPPING}
    record={'phase_path':'AB00/synthetic/phase.parquet','observations':2,'outputs':{'AB00/synthetic/phase.parquet':'old','AB00/synthetic/source_columns.json':'sidecar'}}
    scope={'status':'complete_um21_planar_scope_checked_unreviewed','producer':'stairs','baseline_root':p['baseline'],'expected_records':1,'expected_observations':2,'records':[record]}
    result={'status':'um21_planar_estimates_preserved_canonical_orientations_withheld_unreviewed','scientific_approval':False,'producer':'stairs','scope':'complete_bound_baseline','field_mapping':t.MAPPING,'observations':2,'records':[{'phase_path':record['phase_path'],'observations':2,'rows':300,'persisted_exact_preservation':True,'unrelated_metadata_preserved':True,'source_null_masks_preserved':True,'outputs':{record['phase_path']:{'source_sha256':'old','sha256':'new'},'AB00/synthetic/source_columns.json':{'source_sha256':'sidecar','sha256':'sidecar'}}}]}
    return scope,result,p


def test_exact_preservation_receipt():
    scope,r,p=fixture();t.preservation_gate(scope,r,p)


@pytest.mark.parametrize('field',['persisted_exact_preservation','unrelated_metadata_preserved','source_null_masks_preserved'])
def test_missing_proof_refuses(field):
    scope,r,p=fixture();r['records'][0][field]=False
    with pytest.raises(ValueError):t.preservation_gate(scope,r,p)


def test_omitted_or_changed_source_sidecar_refuses():
    scope,r,p=fixture();r['records'][0]['outputs'].pop('AB00/synthetic/source_columns.json')
    with pytest.raises(ValueError):t.preservation_gate(scope,r,p)
    scope,r,p=fixture();r['records'][0]['outputs']['AB00/synthetic/source_columns.json']['sha256']='changed'
    with pytest.raises(ValueError):t.preservation_gate(scope,r,p)


def test_duplicate_shard_or_finite_canonical_policy_refuses():
    scope,r,p=fixture();r['records']*=2
    with pytest.raises(ValueError):t.preservation_gate(scope,r,p)
    scope,r,p=fixture();r['field_mapping']={}
    with pytest.raises(ValueError):t.preservation_gate(scope,r,p)


def test_full_actual_source_receipt_required():
    p={'kind':'stairs','baseline':'/synthetic/base','bindings':{'upstream':'hash'},'upstream_plan':'upstream','expected_records':403,'expected_observations':2700}
    u={'bindings':{'code':'hash'},'source':{'sha256':'source'}}
    r={'status':'all_stairs_source_scope_checked_unreviewed','scientific_approval':False,'plan_sha256':'hash','bindings':u['bindings'],'source_sha256':'source','recordings':403,'observations':2700,'artifacts':{'/synthetic/base/conversion_summary.json':'summary','/synthetic/base/source_comparison.json':'readback'}}
    t.upstream_gate(r,u,p)
    for change in ({'observations':2699},{'status':'running'},{'scientific_approval':True},{'artifacts':{}}):
        with pytest.raises(ValueError):t.upstream_gate({**r,**change},u,p)
