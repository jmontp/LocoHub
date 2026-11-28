"""Compare original MBLUE subject masses with adapter normalization constants."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse
import ast
import hashlib
import json
from pathlib import Path
from scipy.io import loadmat
ROOT=Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
code=ROOT/'contributor_tools/conversion_scripts/MBLUEAnkle/convert_mblue_ankle_to_parquet.py'
tree=ast.parse(code.read_text());mapping=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SUBJECT_INFO' for t in n.targets))
source=Path('/mnt/s/workspace/MBLUEAnkleOpenSimProcessing/Subject_Data');rows=[]
for subject,expected in mapping.items():
    path=source/(subject+'_FileInfo.mat');data=loadmat(path,simplify_cells=True)['subject_info'];actual=float(data['mass'])
    assert actual==expected['mass'],(subject,actual,expected['mass'])
    rows.append({'subject':subject,'source_mass_kg':actual,'adapter_mass_kg':expected['mass'],'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
report={'scientific_approval':False,'scope':'Original subject_info.mass versus all adapter masses','rows':rows,'adapter_sha256':hashlib.sha256(code.read_bytes()).hexdigest(),'probe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
with args.output.open('x') as stream:json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps({'subjects_checked':len(rows),'mismatches':0}))
