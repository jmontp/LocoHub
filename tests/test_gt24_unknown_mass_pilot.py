"""Metadata-only gates; no numerical source read or worker execution."""
import json
from pathlib import Path
import pytest
from contributor_tools import prepare_gt24_unknown_mass_pilot as tool


def test_model_error_remains_unknown_no_participant_borrow(monkeypatch):
    monkeypatch.setattr(tool,'participant_mass',lambda *a:{'value_kg':80.,'status':'source_participant_mass_bound'})
    def unresolved(*a,**kw):raise ValueError('Synthetic source model conflict')
    monkeypatch.setattr(tool,'resolve_mass',unresolved)
    p,m=tool.mass_policy({}, {'phase':'Phase3','subject':'BT01','exo_state':'powered','native_name_candidates_only':['trial']})
    assert p['value_kg']==80. and m['source_model_mass_kg'] is None
    assert 'conflict' in m['unresolved_reason']


def test_missing_complete_receipt_rejects_before_execution(tmp_path,monkeypatch):
    inventory=tmp_path/'inventory.json';inventory.write_text('{}')
    matrix=tmp_path/'matrix.json';matrix.write_text(json.dumps({'source_metadata':{'readme':{'path':'synthetic'}}}))
    membership=tmp_path/'plan.json';membership.write_text(json.dumps({'bindings':{},'jobs':[{}]}))
    monkeypatch.setattr(tool,'verify',lambda b:None)
    monkeypatch.setattr(tool,'collect_metadata',lambda *a:{'readme':{'path':'synthetic'}})
    plan={'bindings':{},'mass_matrix':str(matrix),'inventory':str(inventory),'membership_plan':str(membership),'records':[{'membership_index':0}]}
    with pytest.raises(ValueError,match='prerequisite missing'):tool.membership_admission(plan)


def test_wrong_terminal_membership_not_admitted(tmp_path,monkeypatch):
    inventory=tmp_path/'inventory.json';inventory.write_text('{}');matrix=tmp_path/'matrix.json';matrix.write_text(json.dumps({'source_metadata':{'readme':{'path':'synthetic'}}}))
    membership=tmp_path/'plan.json';membership.write_text(json.dumps({'bindings':{},'jobs':[{}]}));(tmp_path/'records').mkdir();(tmp_path/'records/000000.json').write_text(json.dumps({'status':'candidate_only','membership_verified':False}))
    monkeypatch.setattr(tool,'verify',lambda b:None);monkeypatch.setattr(tool,'collect_metadata',lambda *a:{'readme':{'path':'synthetic'}})
    plan={'bindings':{},'mass_matrix':str(matrix),'inventory':str(inventory),'membership_plan':str(membership),'records':[{'membership_index':0}]}
    with pytest.raises(ValueError,match='Successful exact'):tool.membership_admission(plan)
