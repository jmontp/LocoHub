"""Read-only StrokePiG inventory and independent subject-mass reconciliation."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import hashlib
import argparse
import importlib.util
import json
import math
from pathlib import Path
import re
import resource
import sys
resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from contributor_tools.run_reconversion_batch import inventory
from contributor_tools.reconvert_recording import STROKE_RECORDING
SOURCE=Path('/mnt/s/locomotion_data/50_StrokePiG')
CODE=ROOT/'contributor_tools/conversion_scripts/StrokePiG/metadata_parser.py'


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root',type=Path,required=True)
    out=parser.parse_args().output_root;out.mkdir(parents=True,exist_ok=False)
    plan=inventory('strokepig',SOURCE)
    spec=importlib.util.spec_from_file_location('stroke_metadata',CODE);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    sheet=module.load_subject_char_xlsx(SOURCE/'SubjectChar.xlsx')
    subjects=[]
    for folder in sorted(SOURCE.glob('TVC*')):
        if not folder.is_dir():continue
        subject=folder.name;number=int(subject[3:]);matching=[]
        for p in folder.glob('*.mp'):
            m=re.fullmatch(r'TVC[-_]?0*(\d+)',p.stem,re.I)
            if m and int(m.group(1))==number:matching.append(p)
        source_mass=None;mass_sources=[]
        for p in sorted(matching):
            lines=p.read_text(errors='strict').splitlines();values=[float(line.split('=',1)[1].strip()) for line in lines if line.strip().startswith('$Bodymass')]
            assert len(values)<=1
            mass_sources.append({'path':str(p),'sha256':digest(p),'bodymass_kg':values[0] if values else None})
        if len(mass_sources)==1:source_mass=mass_sources[0]['bodymass_kg']
        row=sheet[sheet.subject_id==subject];excel_mass=None
        if len(row):
            v=row.iloc[0].get('Bodymass')
            try:excel_mass=float(str(v).replace(',','.'))
            except (ValueError,TypeError):pass
            if excel_mass is not None and not math.isfinite(excel_mass):excel_mass=None
        actual=module.get_subject_metadata(subject,SOURCE,sheet)
        expected=source_mass if source_mass is not None and source_mass>0 else excel_mass
        if expected is not None and expected>0:assert actual['mass_kg']==expected,(subject,actual['mass_kg'],expected)
        else:assert not math.isfinite(actual['mass_kg'])
        subjects.append({'subject':subject,'mp_sources':mass_sources,'xlsx_mass_kg':excel_mass,'selected_mass_kg':actual['mass_kg'] if math.isfinite(actual['mass_kg']) else None,
            'mass_source_disagreement':source_mass is not None and excel_mass is not None and abs(source_mass-excel_mass)>0.05,
            'affected_side':actual['affected_side']})
    recordings=[]
    for r in plan['recordings']:
        p=SOURCE/r['subject']/r['recording'];c3d=p.with_name(p.name.removesuffix('_ik.mot')+'.c3d')
        recordings.append({**r,'ik_bytes':p.stat().st_size,'c3d_exists':c3d.exists(),'c3d_bytes':c3d.stat().st_size if c3d.exists() else None})
    # Enumerate all C3D files before classifying; unfamiliar names must stay visible.
    c3d_sources=[]
    for p in sorted(SOURCE.rglob('*')):
        if not p.is_file() or p.suffix.lower()!='.c3d':continue
        if re.fullmatch(r'BWA(?:[-_ ]?\d+| \(\d+\))?',p.stem,re.I):kind='walking'
        elif re.fullmatch(r'TVC[-_ ]?\d+ Cal \d+',p.stem,re.I):kind='calibration'
        else:kind='unclassified'
        ik=p.with_name(p.stem+'_ik.mot')
        c3d_sources.append({'source_recording':p.relative_to(SOURCE).as_posix(),
            'subject':p.parent.name,'kind':kind,'bytes':p.stat().st_size,
            'ik_exists':ik.is_file(),'ik_name_supported':bool(STROKE_RECORDING.fullmatch(ik.name))})
    coverage={'total_c3d':len(c3d_sources),
        'walking_c3d':sum(r['kind']=='walking' for r in c3d_sources),
        'walking_subjects':len({r['subject'] for r in c3d_sources if r['kind']=='walking'}),
        'walking_without_ik':sum(r['kind']=='walking' and not r['ik_exists'] for r in c3d_sources),
        'walking_with_unsupported_ik_name':sum(r['kind']=='walking' and not r['ik_name_supported'] for r in c3d_sources),
        'calibration_c3d':sum(r['kind']=='calibration' for r in c3d_sources),
        'unclassified_c3d':sum(r['kind']=='unclassified' for r in c3d_sources)}
    report={'inventory':plan,'recording_sources':recordings,'c3d_sources':c3d_sources,'source_coverage':coverage,'subject_metadata':subjects,'xlsx_sha256':digest(SOURCE/'SubjectChar.xlsx'),'adapter_sha256':digest(CODE),'probe_sha256':digest(Path(__file__)),'scientific_approval':False,
        'limitations':['Metadata and local recording inventory only; C3D events and signals are not checked here',
            'Unknown clinical affected side is retained; anatomical default reference is not a clinical inference',
            'MP versus workbook disagreements require review; matching the selected source does not prove source accuracy']}
    (out/'source_inventory.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(coverage))
    print(json.dumps({'subjects':len(subjects),'recordings':len(recordings),'missing_c3d':sum(not r['c3d_exists'] for r in recordings),'mass_source_disagreements':[r['subject'] for r in subjects if r['mass_source_disagreement']],'missing_mass':[r['subject'] for r in subjects if r['selected_mass_kg'] is None],'unknown_clinical_side':sum(r['affected_side']=='unknown' for r in subjects),'excluded_derived_recordings':len(plan['excluded_derived_recordings'])}))


if __name__=='__main__':main()
