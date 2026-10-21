"""Synthetic completed receipts; no scientific source reads or future hashes."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

p=Path(__file__).resolve().parents[1]/'contributor_tools/chain_gt23_cop_metadata.py'
s=importlib.util.spec_from_file_location('gt23_cop_chain',p)
FIX=importlib.util.module_from_spec(s);s.loader.exec_module(FIX)


def receipt_fixture(tmp_path,monkeypatch):
    monkeypatch.setattr(FIX,'ROOT',tmp_path)
    def write(name,value):
        path=tmp_path/name
        path.write_text(json.dumps(value) if isinstance(value,dict) else value)
        return path
    converter=write('converter.m','synthetic model adapter');tool=write('force.py','synthetic force tool')
    original=write('native.parquet','synthetic bytes, not Parquet');output=write('corrected.parquet','corrected synthetic bytes')
    manifest=write('manifest.json',{'output_sha256':FIX.digest(original)})
    driver=write('driver.py',"command=['-Mode','phase']")
    evidence={str(path):FIX.digest(path) for path in [manifest,driver]}
    lineage=write('lineage.json',{'input_sha256':FIX.digest(original),'run_manifest':str(manifest),
                                'run_driver':str(driver),'evidence_sha256':evidence})
    producer={'mode':'phase','path':'converter.m','sha256':FIX.digest(converter)}
    module=SimpleNamespace(ALIASES={'a':'source_a'},FRAME_INFO={'frame':'global'},validate_lineage=lambda *args:producer)
    bindings={**evidence,**{str(path):FIX.digest(path) for path in [lineage,converter,tool,original]}}
    report=write('correction_readback.json',{'status':'global_force_labels_corrected_source_preserved_unreviewed',
                 'scientific_approval':False,'input_sha256':bindings,'output_sha256':FIX.digest(output),
                 'actual_producing_converter':producer,'aliases':module.ALIASES,'frame':module.FRAME_INFO})
    return report,lineage,module,{str(tool):FIX.digest(tool)}


def test_completed_receipt_builds_chain_only_from_real_existing_bytes(tmp_path,monkeypatch):
    args=receipt_fixture(tmp_path,monkeypatch);chain=FIX.completed_chain(*args)
    assert chain['input']==str(tmp_path/'corrected.parquet')
    assert chain['original_input']==str(tmp_path/'native.parquet')
    assert chain['bindings'][chain['input']]==FIX.digest(tmp_path/'corrected.parquet')


@pytest.mark.parametrize('changed',['corrected.parquet','native.parquet','converter.m','driver.py'])
def test_modified_chain_evidence_is_rejected(tmp_path,monkeypatch,changed):
    args=receipt_fixture(tmp_path,monkeypatch);(tmp_path/changed).write_text('changed')
    with pytest.raises(ValueError):FIX.completed_chain(*args)


@pytest.mark.parametrize('field,value',[('status','running'),('actual_producing_converter',{}),('aliases',{}),('scientific_approval',True)])
def test_uncompleted_or_wrong_receipt_is_rejected(tmp_path,monkeypatch,field,value):
    args=receipt_fixture(tmp_path,monkeypatch);report=args[0]
    data=json.loads(report.read_text());data[field]=value;report.write_text(json.dumps(data))
    with pytest.raises(ValueError):FIX.completed_chain(*args)


def test_arrow_overlay_retains_completed_force_correction(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    force=FIX.load('chain_test_force',FIX.FORCE_PATH);cop=FIX.load('chain_test_cop',FIX.COP_PATH)
    values=pa.array([0x8000000000000000,None,0x7ff8000000000001],type=pa.uint64()).view(pa.float64())
    original=pa.table({**{name:values for name in force.ALIASES},'cop_anterior_ipsi_m':values,'task_info':['{}']*3})
    corrected=force.transform_table(original)
    FIX.validate_force_table(corrected,force)
    source=tmp_path/'force.parquet';target=tmp_path/'combined.parquet'
    pq.write_table(corrected,source)
    assert cop.annotate_parquet(source,target)==3
    result=pq.read_table(target,use_threads=False)
    cop.verify_tables(pq.read_table(source,use_threads=False),result)
    FIX.validate_force_table(result,force)
    assert json.loads(result['task_info'][0].as_py())['gt23_cop_frame']==cop.COP_INFO
    for name in force.ALIASES:assert result[name].null_count==3
    malformed=corrected.drop([next(iter(force.ALIASES.values()))])
    with pytest.raises(ValueError,match='aliases'):FIX.validate_force_table(malformed,force)
    name=next(iter(force.ALIASES));malformed=corrected.set_column(corrected.schema.get_field_index(name),corrected.schema.field(name),pa.array([0.,0.,0.]))
    with pytest.raises(ValueError,match='remains'):FIX.validate_force_table(malformed,force)
