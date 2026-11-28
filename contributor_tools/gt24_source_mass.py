"""Independent GT24 mass evidence from released README and tiny Statics metadata.

No numerical imports or signal CSV reads. Calendar day is never inferred from
trial counters or static model IDs. Phase1And2 repeat-day subjects require an
explicit source-backed day; Phase3 resolves the exact model by native trial.
"""
import csv
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
import hashlib
import io
import math
from pathlib import Path
import re
import zipfile

README_SHA='e896c6b424c45f50f261ade2e40c5f5832065fbcd745c593b7cd72fdeb84026f'


def digest_bytes(data):return hashlib.sha256(data).hexdigest()


def readme_masses(text):
    result={};phase=None;inside=False
    for lineno,line in enumerate(text.splitlines(),1):
        if '/////  SUBJECT MASS' in line:inside=True;continue
        if inside and '/////' in line:break
        if not inside:continue
        if line.strip() in ('Phase1And2','Phase3'):phase=line.strip();result[phase]={};continue
        match=re.match(r'^(BT\d+):\s*(.*)$',line)
        if not match:continue
        entries=[value.strip() for value in match[2].split('|')]
        fields={};numbers=[]
        for entry in entries:
            number=re.match(r'([0-9]+(?:\.[0-9]+)?)\s*kg',entry)
            if not number:raise ValueError('Unrecognized source mass cell')
            numbers.append(number[1])
        if len(numbers)<2:raise ValueError('Missing body/model mass distinction')
        fields.update(participant_day1_kg=numbers[0],model_day1_with_exo_kg=numbers[1])
        for entry,number in zip(entries[2:],numbers[2:]):
            if 'day 2 testing w/o exo' in entry:fields['participant_day2_kg']=number
            elif 'day 2 testing w/ exo' in entry:fields['model_day2_with_exo_kg']=number
            else:raise ValueError('Unrecognized day-specific source mass')
        subject=match[1]
        if subject in result[phase]:raise ValueError('Duplicate README subject identity')
        result[phase][subject]={'line':lineno,'source_text':line,**fields}
    if set(result)!={'Phase1And2','Phase3'}:raise ValueError('Both source mass phases required')
    return result


def parse_statics(data):
    if len(data)>16384:raise ValueError('Static metadata admission exceeded')
    reader=csv.DictReader(io.StringIO(data.decode('utf-8-sig')))
    if reader.fieldnames!=['trial','static','mass']:raise ValueError('Unreviewed Statics schema')
    result={}
    for line,row in enumerate(reader,2):
        if None in row or any(x is None for x in row.values()):raise ValueError('Malformed Statics row')
        if not row['trial'] or row['trial'] in result:raise ValueError('Missing/duplicate native model identity')
        mass=Decimal(row['mass'])
        if not mass.is_finite() or mass<=0:raise ValueError('Invalid source model mass')
        model=int(row['static'])
        if model<1 or str(model)!=row['static']:raise ValueError('Unreviewed model identifier')
        result[row['trial']]={'line':line,'source_model_id':row['static'],'source_model_mass_kg_decimal':row['mass']}
    if not result:raise ValueError('Empty Statics metadata')
    return result


def collect_metadata(inventory,readme_path):
    raw=Path(readme_path).read_bytes()
    if digest_bytes(raw)!=README_SHA:raise ValueError('Released README evidence changed')
    masses=readme_masses(raw.decode());phase=next(p for p in inventory['phases'] if p['phase']=='Phase3')
    archive=Path(phase['archive']['path']);before=archive.stat()
    if before.st_size!=phase['archive']['bytes'] or before.st_mtime_ns!=phase['archive']['mtime_ns']:raise ValueError('Source archive metadata changed')
    tables={};total=0
    with zipfile.ZipFile(archive) as z:
        for group in phase['static_source_tables']:
            if len(group['members'])!=1:raise ValueError('Ambiguous static metadata group')
            member=group['members'][0];info=z.getinfo(member['name'])
            if (info.file_size,info.CRC,info.header_offset)!=(member['bytes'],member['crc32'],member['header_offset']) or info.file_size>16384:raise ValueError('Static member identity/admission changed')
            data=z.read(info);total+=len(data)
            if total>163840:raise ValueError('Total static metadata admission exceeded')
            subject=Path(group['folder']).name
            if subject in tables:raise ValueError('Duplicate subject static metadata')
            tables[subject]={'archive':str(archive),'member':member['name'],'csv_sha256':digest_bytes(data),'bytes':len(data),'records':parse_statics(data)}
    after=archive.stat()
    if before.st_size!=after.st_size or before.st_mtime_ns!=after.st_mtime_ns:raise ValueError('Archive changed during metadata read')
    return {'readme':{'path':str(Path(readme_path).resolve()),'sha256':README_SHA,'phase_masses':masses},'phase3_static_models':tables,'metadata_csv_bytes_read':total}


def model_readme_candidates(entry,model,exo_state):
    """Compare only printed decimal precision, not fitted physiological ranges.

    Source model totals have more digits than README's two decimals; accept its
    displayed rounding or truncation. A different subject-scale value is a
    cross-document conflict requiring external evidence, never an auto-swap.
    """
    value=Decimal(model)
    represented={value.quantize(Decimal('.01'),rounding=mode) for mode in (ROUND_DOWN,ROUND_HALF_UP)}
    fields=('participant_day1_kg','participant_day2_kg') if exo_state=='no_exo' else ('model_day1_with_exo_kg','model_day2_with_exo_kg')
    return [field for field in fields if field in entry and Decimal(entry[field]) in represented]


def resolve_mass(metadata,phase,subject,exo_state,*,native_trial=None,day=None,day_evidence=None):
    if phase not in ('Phase1And2','Phase3'):raise ValueError('Explicit collection source required')
    if exo_state not in ('powered','worn_unpowered','no_exo'):raise ValueError('Explicit exoskeleton state required')
    entry=metadata['readme']['phase_masses'][phase].get(subject)
    if entry is None:raise ValueError('Subject absent from this source phase')
    if day is not None and (day not in (1,2) or not day_evidence):raise ValueError('Day requires explicit source evidence')
    evidence={'readme_sha256':metadata['readme']['sha256'],'readme_line':entry['line']}
    if phase=='Phase1And2':
        if exo_state=='no_exo':raise ValueError('Source protocol collected Phase1And2 wearing exoskeleton')
        if 'model_day2_with_exo_kg' in entry and day is None:raise ValueError('Repeat-day Phase1And2 subject requires source-backed recording day')
        if day==2 and 'model_day2_with_exo_kg' not in entry:raise ValueError('No source day2 mass evidence')
        model=entry['model_day2_with_exo_kg' if day==2 else 'model_day1_with_exo_kg']
        participant=entry.get('participant_day2_kg') if day==2 else entry['participant_day1_kg']
        evidence.update(source='released_README_phase_subject_day',day_evidence=day_evidence)
        return {'source_model_mass_kg':float(model),'source_model_mass_kg_decimal':model,'participant_mass_kg':None if participant is None else float(participant),'mass_basis':'source_reported_worn_system_mass','calendar_day':day,'model_id':None,'evidence':evidence}
    if native_trial is None:raise ValueError('Exact native Phase3 trial required; subject mass alone is insufficient')
    table=metadata['phase3_static_models'].get(subject)
    if table is None or native_trial not in table['records']:raise ValueError('Native trial absent from source model table')
    row=table['records'][native_trial];model=row['source_model_mass_kg_decimal']
    candidates=model_readme_candidates(entry,model,exo_state)
    if not candidates:raise ValueError('Source conflict: Statics model mass does not match this subject README mass at its printed precision')
    if day is not None and not any(f'day{day}_' in field for field in candidates):raise ValueError('Explicit calendar day conflicts with source model mass')
    evidence.update(source='released_native_Statics_trial_model_mass',statics_csv_sha256=table['csv_sha256'],statics_member=table['member'],statics_line=row['line'],day_evidence=day_evidence,readme_mass_candidates=candidates,day_interpretation='Calendar day not inferred from model ID or rounded mass agreement')
    # Static identifiers are model IDs, not calendar days. No rounded README
    # substitution: the exact source model mass is authoritative for this trial.
    return {'source_model_mass_kg':float(model),'source_model_mass_kg_decimal':model,'participant_mass_kg':None,'mass_basis':'source_opensim_model_including_worn_system' if exo_state!='no_exo' else 'source_opensim_model_no_exoskeleton','calendar_day':day,'model_id':row['source_model_id'],'evidence':evidence}
