"""Synthetic receipt gates only; never opens the scientific source."""
import pytest
from contributor_tools import restore_um21_stairs_wtr as t


def fixture(kind):
    plan={'kind':kind,'source':{'sha256':'source'},'probe_path':'probe','bindings':{'probe':'probehash',str(t.ROOT/'code'):'codehash'},'producer_code_paths':['code']}
    s={'scientific_approval':False,'source_sha256':'source','code_sha256':{'code':'codehash'}}
    a={'scientific_approval':False,'summary_sha256':'summary','probe_sha256':'probehash'}
    if kind=='stairs':
        records=[{'subject':'synthetic','condition':str(i),'windows':[{'synthetic':True}]*(2700 if i==0 else 0),'unannotated':[]} for i in range(403)]
        plan['scope']={'recordings':records};s.update(status='all_annotated_stair_cycles_exported_unreviewed',recordings=[dict(r,exported_rows=len(r['windows'])*150) for r in records])
        a.update(status='all_annotated_stair_cycles_source_checked_unreviewed',source_recordings=403,annotated_observations=2700,explicitly_empty_annotations=16,exported_observations_checked=2700,source_component_values_checked=1,max_component_error=0)
    else:
        subjects=[f'AB{i:02}' for i in range(1,10)];plan['scope']={'subjects':subjects};s.update(status='all_wtr_source_cycles_preserved_unreviewed',format='source_labeled_cycle_companion',source_subjects=subjects,records=[{'subject':x,'observations':1,'rows':150,'protocol_counts':{'unverified':1}} for x in subjects]);a.update(status='all_wtr_source_cycles_checked_unreviewed',records=[{'subject':x,'source_cycles':1,'finite_component_values_checked':1,'maximum_error':0} for x in subjects])
    return s,a,plan


@pytest.mark.parametrize('kind',['stairs','wtr'])
def test_full_pair(kind):
    s,a,p=fixture(kind);assert t.gate(s,a,p,'summary')[0]==(2700 if kind=='stairs' else 9)


@pytest.mark.parametrize('kind',['stairs','wtr'])
def test_probe_and_producer_required(kind):
    s,a,p=fixture(kind);s['code_sha256']={}
    with pytest.raises(ValueError):t.gate(s,a,p,'summary')
    s,a,p=fixture(kind);a['probe_sha256']='other'
    with pytest.raises(ValueError):t.gate(s,a,p,'summary')


def test_stair_partial_and_changed_exclusions_refuse():
    s,a,p=fixture('stairs');a['exported_observations_checked']=2699
    with pytest.raises(ValueError):t.gate(s,a,p,'summary')
    s,a,p=fixture('stairs');s['recordings'][0]['unannotated']=[{'invented':True}]
    with pytest.raises(ValueError):t.gate(s,a,p,'summary')


def test_wtr_count_cannot_replace_subject_membership():
    s,a,p=fixture('wtr');s['records'][-1]=s['records'][0]
    with pytest.raises(ValueError):t.gate(s,a,p,'summary')
    s,a,p=fixture('wtr');a['records'][-1]['subject']='AB10'
    with pytest.raises(ValueError):t.gate(s,a,p,'summary')
