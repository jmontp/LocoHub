"""Synthetic source-inventory fixtures; no scientific arrays."""
import pytest
from contributor_tools import build_fu18_source_coverage as tool

def plan():
    pairs=[]
    for i in range(1,52):
        conditions=list(tool.CONDITIONS)
        if i>=43:conditions=[c for c in conditions if not c.startswith('O') and c not in ('T07','T08')]
        if i in (32,39):conditions.remove('T07')
        if i in (28,29,32,36,37,39):conditions.remove('T08')
        for c in conditions:
            stem=f'WBDS{i:02d}walk{c}';pairs.append({'subject':f'FU18_{i:02d}','condition':c,'stem':stem,'environment':'overground' if c.startswith('O') else 'treadmill','age_group':'Young' if i<=24 else 'Older','members':{k:{'name':stem+k+'.txt'} for k in ('ang','knt')}})
    return {'pairs':pairs}

def test_complete_scope_and_missing_conditions():
    rows=tool.inventory(plan());assert len(rows)==51 and sum(len(r['conditions']) for r in rows)==508
    assert rows[42]['conditions']==['T01','T02','T03','T04','T05','T06']
    page=tool.render(rows);assert page.count('title="Published angle and kinetic tables"')==508
    assert page.count('class="absent"')==53
    assert 'not completed conversions' in page and '<main ' in page and '<title>' in page

@pytest.mark.parametrize('mutation',['duplicate','missing','side_identity','member'])
def test_invalid_scope_rejected(mutation):
    data=plan()
    if mutation=='duplicate':data['pairs'].append(data['pairs'][0])
    elif mutation=='missing':data['pairs'].pop()
    elif mutation=='side_identity':data['pairs'][0]['stem']='WBDS02walkOC'
    else:data['pairs'][0]['members']['ang']['name']='incorrect.txt'
    with pytest.raises(ValueError):tool.inventory(data)
