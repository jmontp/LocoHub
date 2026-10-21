"""Exercise actual delegated argument parsers with synthetic stage receipts only."""
import argparse
import ast
import json
from pathlib import Path
import pytest
from contributor_tools import rebuild_gt23_full_source as m


def parse_real_cli(path,arguments,monkeypatch):
    tree=ast.parse(Path(path).read_text());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    prefix=[];found=False
    for statement in main.body:
        prefix.append(statement)
        if any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='parse_args' for n in ast.walk(statement)):
            found=True;break
    assert found
    monkeypatch.setattr(m.sys,'argv',[str(path),*arguments])
    # Execute only the adapter's actual parser construction/parse statement.
    # No conversion function, filesystem admission or numerical imports run.
    namespace={'argparse':argparse,'Path':Path,'__doc__':'synthetic parser exercise'}
    exec(compile(ast.Module(body=prefix,type_ignores=[]),str(path),'exec'),namespace)
    return next(v for v in namespace.values() if isinstance(v,argparse.Namespace))


def test_actual_full_record_delegated_commands_parse(tmp_path,monkeypatch):
    from contributor_tools import withhold_gt23_unverified_anatomy as anatomy
    root=tmp_path/'original';out=tmp_path/'output';folder=root/'RawData/AB99/CSV_Data/walk';folder.mkdir(parents=True)
    original_transform=root/'RawData/AB99/Transforms/walk.mat';original_transform.parent.mkdir();original_transform.write_bytes(b'synthetic transform')
    parsing=root/'Segmentation/AB99/walk_parsing.mat';parsing.parent.mkdir(parents=True);parsing.write_bytes(b'synthetic parsing')
    names=['Joint_Angle.csv','Joint_Velocities.csv','Joint_Moments.csv','GroundFrame_GRFs.csv','Link_Angle.csv','Link_Velocities.csv']
    for name in names:(folder/name).write_bytes(b'time,value\n0,1\n1,2\n')
    companion=out/'source_companions/AB99/walk';companion.mkdir(parents=True)
    (companion/'source_readback.json').write_text(json.dumps({'files':[{'source_path':str(folder/n),'source_sha256':m.digest(folder/n)} for n in names[:4]]}))
    support=tmp_path/'support';support.mkdir()
    for mode in ('time','phase'):(support/f'native_{mode}_driver.py').write_text('synthetic driver')
    record={'subject':'AB99','recording':'walk','parsing':parsing.name,'parsing_sha256':m.digest(parsing),'has_intervals':True}
    monkeypatch.setattr(m,'windows',lambda p:str(p))
    calls=[]
    class FakeRuntime:
        plan={'source_root':str(root),'support':str(support)}
        guarded_digest=staticmethod(m.digest)
        resources=staticmethod(lambda:None)
        def __init__(self):self.out=out
        def tool(self,name,args,base):
            parsed=parse_real_cli(args[0],args[1:],monkeypatch);calls.append((name,parsed))
            if name=='source_prepare':
                source=parsed.output_root;source.mkdir(parents=True)
                rows={}
                for n in names:
                    target=source/'RawData/AB99/CSV_Data/walk'/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((folder/n).read_bytes())
                    rows[n]={'source':str(folder/n),'source_sha256':m.digest(folder/n),'window_sha256':m.digest(target)}
                for relative in ('RawData/Subject_masses.csv','Segmentation/AB99/walk_parsing.mat'):
                    p=source/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'synthetic')
                (source/'source_window_manifest.json').write_text(json.dumps({'subject':'AB99','parsing':parsing.name,'recording':'walk','start_s':0.,'end_s':1.,'csv_files':rows,'other_source_sha256':{str(parsing):m.digest(parsing)},'original_transforms':str(original_transform)}))
            elif name.endswith(('cop_prepare','normalization_prepare')):parsed.plan.write_text('{}')
            elif name.endswith('normalization_run'):
                d=base/'normalized';d.mkdir();(d/'corrected.parquet').write_bytes(b'synthetic parquet placeholder');(d/'normalization_readback.json').write_text('{}')
            elif name.endswith(('raw_prepare','kinematics_prepare')):parsed.output.mkdir();(parsed.output/'plan.json').write_text('{}')
            elif name.endswith('raw_audit'):(base/'raw_audit/raw_source_readback.json').write_text(json.dumps({'status':'publisher_normalization_raw_source_checked_unreviewed','participant':'AB99','scientific_approval':False}))
            elif name.endswith('kinematics_run'):(base/'kinematics_audit/raw_kinematics_readback.json').write_text('{}')
        def native(self,name,options,destination,mode):
            destination.mkdir(parents=True);op=destination/'options.json';op.write_text(json.dumps(options));target=Path(options['output_path']);target.write_bytes(b'synthetic native placeholder')
            status=target.parent/'native_status.json';status.write_text('{}')
            if mode=='prepare-transforms':Path(str(target)+'.verification.json').write_text('{"exact_native_readback":true}')
            return op,status
    def disposition(source,target,**kwargs):target.write_bytes(b'synthetic withheld placeholder');return {'scientific_approval':False}
    monkeypatch.setattr(anatomy,'run',disposition)
    result=m.corrected_record(FakeRuntime(),record,0)
    assert set(result['modes'])=={'time','phase'}
    phase=Path(result['modes']['phase']['output']).parent
    raw=json.loads((phase/'phase_source_evidence.json').read_text())['source_sha256']
    kin=json.loads((phase/'phase_kinematics_source_evidence.json').read_text())['source_sha256']
    assert len([p for p in raw if Path(p).name=='Joint_Angle.csv'])==1
    assert len([p for p in kin if Path(p).name=='Joint_Angle.csv'])==2
    assert any(Path(p).name=='source_window_manifest.json' for p in kin)
    assert len(calls)==19 and {c[0] for c in calls}=={'source_prepare',*[f'0_{mode}_{step}' for mode in ('time','phase') for step in ('force','cop_prepare','cop_run','normalization_prepare','normalization_run','raw_prepare','raw_audit','kinematics_prepare','kinematics_run')]}


@pytest.mark.parametrize('mode',['time','phase'])
def test_literal_native_driver_mode_survives_dispatch(mode,monkeypatch):
    source=(m.SUPPORT/'native_time_driver.py').read_text().replace("'-Mode','time'",f"'-Mode','{mode}'")
    captured=[];monkeypatch.setattr(m.subprocess,'run',lambda command,**kwargs:captured.append(command))
    monkeypatch.setattr(m.sys,'argv',['driver.py','S:\\options.json','S:\\code','S:\\guard.ps1'])
    exec(compile(source,'synthetic native driver','exec'),{'__name__':'__main__','__file__':'/synthetic/driver.py'})
    assert len(captured)==1 and captured[0][-2:]==['-Mode',mode]
