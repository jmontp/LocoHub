"""Small receipt-only fixtures; no scientific data read or process launch."""
import copy
import pytest
from contributor_tools import restore_um21_tread_components as tool


def fixture():
    records=[];checked=[];output=[]
    for i in range(50):
        n=8626 if i==0 else 0;e=3674 if i==0 else 0
        r={'subject':'synthetic','condition':str(i),'observations':n,'excluded':e,'rows':150*n,'path':f'synthetic/{i}/phase.parquet','schema_passed':True,'sha256':'output'+str(i)}
        records.append(r);checked.append({'subject':r['subject'],'condition':r['condition'],'observations':n,'excluded_pairs':e,'source_pairs':n+e,'output_sha256':r['sha256'],'finite_values_checked':1,'maximum_error':0,'ledger_sha256':'ledger'+str(i)})
        output.append({'subject':r['subject'],'condition':r['condition'],'observations_checked':n,'existing_columns_exactly_preserved':True,'finite_source_values_checked':1,'source_columns':12,'maximum_error':0,'base_output_sha256':r['sha256'],'ledger_sha256':'ledger'+str(i)})
    base={'status':'complete_partial_scope','planned_recordings':50,'available_recordings':50,'source':{'sha256':'source'},'recordings':records}
    readback={'status':'all_tread_sagittal_exports_checked_unreviewed','scientific_approval':False,'summary_sha256':'summary','probe_sha256':'probe','source_sha256':'source','records':checked}
    plan={'base_summary':'summary.json','base_readback':'readback.json','source':{'sha256':'source'},'bindings':{'summary.json':'summary','readback.json':'readback',str(tool.PROBE):'probe',**{f'code{i}':f'hash{i}' for i in range(4)}}}
    report={'status':'all_tread_joint_components_readback_unreviewed','scientific_approval':False,'planned_recordings':50,'base_summary_sha256':'summary','base_readback_sha256':'readback','source_sha256':'source','code_sha256':{f'code{i}':f'hash{i}' for i in range(4)},'records':output}
    return base,readback,plan,report


def test_full_scope_receipt():
    b,r,p,o=fixture();assert len(tool.completion_gate(o,p,b,r))==50


@pytest.mark.parametrize('change',['duplicate','missing','counts','source','probe'])
def test_baseline_membership_and_provenance(change):
    b,r,p,o=fixture()
    if change=='duplicate':b['recordings'][-1]=b['recordings'][0]
    if change=='missing':r['records'].pop()
    if change=='counts':r['records'][0]['source_pairs']-=1
    if change=='source':r['source_sha256']='other'
    if change=='probe':r['probe_sha256']='other'
    with pytest.raises(ValueError):tool.completion_gate(o,p,b,r)


@pytest.mark.parametrize('field,value',[('existing_columns_exactly_preserved',False),('finite_source_values_checked',0),('source_columns',0),('maximum_error',float('nan')),('ledger_sha256','changed'),('observations_checked',1)])
def test_partial_or_unassessed_components_refuse(field,value):
    b,r,p,o=fixture();o['records'][0][field]=value
    with pytest.raises(ValueError):tool.completion_gate(o,p,b,r)
