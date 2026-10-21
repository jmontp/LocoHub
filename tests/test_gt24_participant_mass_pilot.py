"""Pilot admission fails closed on synthetic missing/contradictory receipts."""
import json
import pytest
from contributor_tools import prepare_gt24_participant_mass_pilot as tool


def setup(tmp_path,monkeypatch):
    def write(name,obj):
        p=tmp_path/name;p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(obj));return str(p)
    metadata={'readme':{'path':'synthetic'}}
    matrix=write('matrix.json',{'source_metadata':metadata});inventory=write('inventory.json',{})
    identity={'phase':'Phase1And2','subject':'BT01','parsed_recording':'trial','native_recording':'native'}
    source=write('source.json',{'synthetic':True})
    membership=write('plan.json',{'bindings':{},'jobs':[{**identity,'tables':[{'kind':'angle_filt','parsed':{'path':source}}]}]})
    record={'phase':'Phase1And2','subject':'BT01','recording':'trial','native_name_candidates_only':['native'],'membership_index':0,'exo_state':'powered','participant_mass':{'value_kg':80},'model_mass':{'source_model_mass_kg':100},'verified_source_denominator':None}
    plan={'bindings':{},'mass_matrix':matrix,'inventory':inventory,'membership_plan':membership,'records':[record]}
    report={**identity,'status':'native_parsed_candidate_checked_unreviewed','membership_verified':True,'plan_sha256':tool.digest(membership),'job_index':0,'matched_intervals':[[0,9]],'tables':{'angle_filt':{'parsed':{'full_csv_sha256':tool.digest(source)}}}}
    monkeypatch.setattr(tool,'verify',lambda x:None);monkeypatch.setattr(tool,'collect_metadata',lambda *x:metadata)
    monkeypatch.setattr(tool,'participant_mass',lambda *x:record['participant_mass']);monkeypatch.setattr(tool,'resolve_mass',lambda *x,**kw:record['model_mass'])
    monkeypatch.setattr(tool,'checked_report_intervals',lambda x:x['matched_intervals'])
    return plan,report,lambda:write('records/000000.json',report)


def test_missing_receipt_never_admits(tmp_path,monkeypatch):
    plan,report,save=setup(tmp_path,monkeypatch)
    with pytest.raises(FileNotFoundError):tool.admission(plan)
    save();assert len(tool.admission(plan))==1


def test_false_or_wrong_identity_receipt_rejected(tmp_path,monkeypatch):
    plan,report,save=setup(tmp_path,monkeypatch);report['membership_verified']=False;save()
    with pytest.raises(ValueError):tool.admission(plan)
    report['membership_verified']=True;report['subject']='BT02';save()
    with pytest.raises(ValueError,match='identity'):tool.admission(plan)


def test_arbitrary_denominator_assertion_never_admits(tmp_path,monkeypatch):
    plan,report,save=setup(tmp_path,monkeypatch);save();plan['records'][0]['verified_source_denominator']={'value_kg':100.,'evidence_sha256':'a'*64}
    with pytest.raises(ValueError,match='unsupported'):tool.admission(plan)
