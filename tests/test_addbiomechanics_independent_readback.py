"""Independent persisted-source audit against synthetic native API mocks only."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest

ROOT=Path(__file__).parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
fakes=load('adb_source_fixtures',ROOT/'tests/test_addbiomechanics_source_preservation.py')
review=load('adb_independent_readback',ROOT/'contributor_tools/conversion_scripts/AddBiomechanics/audit_source_preservation.py')

@pytest.fixture
def exported(tmp_path,monkeypatch):
    source=tmp_path/'input';source.mkdir();p=source/'sample.b3d';p.write_bytes(b'synthetic-only-source')
    subject=fakes.Subject((3,2));monkeypatch.setattr(fakes.m,'make_guard',lambda output:lambda **kwargs:None)
    monkeypatch.setitem(sys.modules,'nimblephysics',SimpleNamespace(biomechanics=SimpleNamespace(SubjectOnDisk=lambda p:subject)))
    output=tmp_path/'output';fakes.m.process_dataset('Falisse2016',source,output)
    return source,output,subject


def manifest_update(output,change=None):
    path=output/'manifest.json';m=json.loads(path.read_text());entry=m['files'][0]
    if change:change(m,entry)
    path.write_text(json.dumps(m));return m,entry


def alter_table(output,change):
    import pyarrow as pa
    import pyarrow.parquet as pq
    path=output/'source_0000/source_frames.parquet';table=pq.ParquetFile(path).read(use_threads=False);rows=table.to_pylist();change(rows)
    pq.write_table(pa.Table.from_pylist(rows,schema=table.schema),path)
    manifest_update(output,lambda m,e:e.update(output_sha256=review.digest(path)))


def run(exported):
    source,output,subject=exported
    return review.audit(source,output,guard=lambda **kwargs:None)


def test_complete_independent_scope_values_models_metadata(exported):
    report=run(exported)
    assert report['files'][0]['source_frames']==5 and report['files'][0]['rows']==14
    assert report['canonical_dataset_complete'] is False and report['scientific_approval'] is False
    assert report['files'][0]['source_properties_checked']>40


def test_empty_source_scope_cannot_be_approved(exported):
    source,output,_=exported
    (source/'sample.b3d').unlink()
    manifest_update(output,lambda manifest,entry:manifest.update(files=[]))
    with pytest.raises(ValueError,match='No original B3D'):
        run(exported)


def test_task_metadata_cannot_claim_anatomical_or_experiment_approval(exported):
    _,output,_=exported
    def change(rows):
        for row in rows:
            info=json.loads(row['task_info'])
            info['assessment']='scientifically_approved'
            row['task_info']=json.dumps(info)
    alter_table(output,change)
    manifest_update(output,lambda manifest,entry:[trial.update(task_assessment='scientifically_approved') for trial in entry['trials']])
    with pytest.raises(ValueError,match='Historical task assessment'):
        run(exported)


@pytest.mark.parametrize('kind',['drop_pass','drop_frame','extra_frame','clock','mass','mass_available','trial','canonical_task'])
def test_identity_completeness_and_clock_corruptions(exported,kind):
    _,out,_=exported
    def mutate(rows):
        if kind=='drop_pass':rows.pop(1)
        elif kind=='drop_frame':del rows[:2]
        elif kind=='extra_frame':rows.append(rows[-1].copy())
        elif kind=='clock':rows[0]['time_s']=.5
        elif kind=='mass':rows[0]['source_mass_kg']=70.
        elif kind=='mass_available':rows[0]['mass_available']=True
        elif kind=='trial':rows[0]['source_trial_index']=1
        else:rows[0]['task']='level_walking'
    alter_table(out,mutate)
    with pytest.raises(ValueError):run(exported)


@pytest.mark.parametrize('kind',['dtype','shape','signed_zero','NaN_mask','property','extra_property'])
def test_independent_all_value_and_property_corruptions(exported,kind):
    _,out,_=exported
    def mutate(rows):
        i=0 if kind in ('signed_zero','NaN_mask') else 1;fields=json.loads(rows[i]['source_fields_json'])
        if kind=='dtype':fields['pos']['dtype']='<f4'
        elif kind=='shape':fields['pos']['shape']=[1,3]
        elif kind=='signed_zero':fields['markerObservations'][0]['values'][1]['values'][0]=0.
        elif kind=='NaN_mask':fields['markerObservations'][0]['values'][1]['values'][2]=0.
        elif kind=='property':del fields['custom_source_property']
        else:fields['invented']=123
        rows[i]['source_fields_json']=json.dumps(fields)
    alter_table(out,mutate)
    with pytest.raises(ValueError):run(exported)


@pytest.mark.parametrize('kind',['contact_bodies','model','clock_metadata','frame_count','trial_count'])
def test_metadata_and_model_changes_cannot_be_reauthorized_by_hash(exported,kind):
    _,out,_=exported;mp=out/'source_0000/source_metadata.json';meta=json.loads(mp.read_text())
    if kind=='contact_bodies':meta['contact_bodies'][0]='invented_right_foot'
    elif kind=='model':
        model=out/'source_0000/model_pass_0.osim';model.write_text('<OpenSimDocument/>');meta['models'][0]['sha256']=review.digest(model)
    elif kind=='clock_metadata':meta['time_reference']='global recording time'
    if kind in ('contact_bodies','model','clock_metadata'):
        mp.write_text(json.dumps(meta));manifest_update(out,lambda m,e:e.update(metadata_sha256=review.digest(mp),model_files=meta['models']))
    elif kind=='frame_count':manifest_update(out,lambda m,e:e['trials'][0].update(frames_written=2))
    else:manifest_update(out,lambda m,e:e['trials'].pop())
    with pytest.raises(ValueError):run(exported)


def test_source_mutation_during_independent_readback(exported):
    source,output,subject=exported;original=subject.readFrames
    def change(*args,**kwargs):
        (source/'sample.b3d').write_bytes(b'mutated original synthetic source')
        return original(*args,**kwargs)
    subject.readFrames=change
    with pytest.raises(ValueError,match='changed during'):run(exported)


def test_full_file_inventory_and_output_hash_are_required(exported):
    source,out,_=exported;(source/'extra.b3d').write_bytes(b'synthetic-extra')
    with pytest.raises(ValueError,match='inventory'):run(exported)
    (source/'extra.b3d').unlink();manifest_update(out,lambda m,e:e.update(output_sha256='0'*64))
    with pytest.raises(ValueError,match='output changed'):run(exported)
