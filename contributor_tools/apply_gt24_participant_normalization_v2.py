"""GT24 normalization successor: unknown masses withhold dependent values.

Separate from the frozen v1 helper; no automatic execution.

Preserve source-normalized joint moments; canonical moments remain missing until
an independently bound source denominator exists. Raw forces use participant mass; interaction units remain unverified. Model-weight force is a distinct explicitly derived alias.
"""
import itertools
import json
import math
from pathlib import Path
from contributor_tools.gt24_mass_field_policy import normalize_sample, validated_mass
from contributor_tools.stream_gt24_continuous_record import numerical_source_rows,source_rows
from contributor_tools.preserve_um21_planar_estimates import exact_value
from contributor_tools.preserve_mblue_planar_estimates import digest

JOINTS=(('hip_flexion','hip_flexion','hip_flexion'),('knee_angle','knee_flexion','knee_extension'),('ankle_angle','ankle_dorsiflexion','ankle_plantarflexion'))


def changed_fields():
    fields={'subject_metadata','task_info'}
    for role in ('ipsi','contra'):
        fields.add(f'grf_vertical_{role}_BW')
        for _,joint,_ in JOINTS:
            for kind in ('moment','biological_moment','assistance_moment'):fields.add(f'{joint}_{kind}_{role}_Nm_kg')
    return fields


def added_fields():
    fields=set()
    for role in ('ipsi','contra'):
        fields.add(f'derived_source_model_weight_grf_vertical_{role}')
        fields.add(f'source_grf_vertical_{role}_N')
        for _,canonical,native_coordinate in JOINTS:
            for kind in ('net','biological'):fields.add(f'source_normalized_{native_coordinate}_{kind}_moment_{role}_Nm_kg')
            if canonical!='ankle_dorsiflexion':fields.add(f'source_exo_{canonical}_interaction_torque_{role}_units_unknown')
    return fields


def metadata_update(row,record):
    participant=record['participant_mass'];model=record['model_mass'];subject=json.loads(row['subject_metadata']);info=json.loads(row['task_info'])
    subject.update(weight_kg=participant['value_kg'],weight_basis='participant_without_exoskeleton',participant_mass_kg=participant['value_kg'],source_model_mass_kg=model['source_model_mass_kg'],source_model_mass_basis=model['mass_basis'],source_model_id=model['model_id'],day=participant['calendar_day'],source_mass_evidence_sha256=record['mass_evidence_sha256'])
    info.update(normalization_policy='gt24_participant_mass_missingness_v2',force_normalization='participant_mass_kg_times_9.81',assistance_semantics='canonical_withheld_interaction_units_unverified; raw source aliases units unknown',moment_semantics='canonical_withheld_source_denominator_unverified; source_normalized_aliases_preserved',biological_moment_semantics='canonical_withheld_source_denominator_unverified; source_normalized_aliases_preserved',source_joint_moment_denominator_status='unverified',derived_model_weight_force='separate source-reported model mass denominator; not participant body weights')
    info['normalization_availability']=normalization_availability(record)
    return json.dumps(subject,sort_keys=True,allow_nan=False),json.dumps(info,sort_keys=True,allow_nan=False)


def normalization_availability(record):
    participant=validated_mass(record['participant_mass'])
    model=validated_mass(record['model_mass'],key='source_model_mass_kg')
    if participant is not None and record['participant_mass'].get('status')!='source_participant_mass_bound':raise ValueError('Participant mass is not source bound')
    return {'participant_force_BW':'available_if_force_present' if participant is not None else 'withheld_participant_mass_unresolved',
            'derived_model_weight_force':'available_if_force_present' if model is not None else 'withheld_source_model_mass_unresolved',
            'source_grf_N':'preserved_without_mass_division',
            'canonical_joint_moments':'withheld_source_normalization_denominator_unverified',
            'source_joint_moments':'preserved_as_supplied_Nm_kg_unknown_denominator',
            'canonical_assistance':'known_zero_no_exo' if record['exo_state']=='no_exo' else 'withheld_interaction_units_unverified'}


def corrected_row(old,source,record):
    if record.get('verified_source_denominator') is not None:raise ValueError('This pilot has no independently verified joint moment denominator; supplied assertion is not evidence')
    normalization_availability(record)
    result=dict(old);side=old['reference_side']
    if side not in ('left','right'):raise ValueError('Unknown physical reference side')
    for role,leg in [('ipsi','l' if side=='left' else 'r'),('contra','r' if side=='left' else 'l')]:
        raw=lambda table,column:source.get(table,{}).get(column,math.nan)
        for native,canonical,coordinate in JOINTS:
            torque=math.nan if canonical=='ankle_dorsiflexion' else raw('exo',native.replace('_flexion','_angle')+'_'+leg+'_torque_interaction')
            values=normalize_sample(source_force_vertical_N=raw('grf',f'fp_{leg}_force_y'),source_interaction_torque_units_unknown=torque,source_net_moment_Nm_kg=raw('moment_filt',native+'_'+leg+'_moment'),source_biological_moment_Nm_kg=raw('moment_filt_bio',native+'_'+leg+'_moment'),joint=canonical,exo_state=record['exo_state'],participant=record['participant_mass'],reported_model={'value_kg':record['model_mass']['source_model_mass_kg']},verified_source_denominator=None)
            result[f'{canonical}_moment_{role}_Nm_kg']=values['canonical_net_moment_Nm_kg']
            result[f'{canonical}_biological_moment_{role}_Nm_kg']=values['canonical_biological_moment_Nm_kg']
            result[f'{canonical}_assistance_moment_{role}_Nm_kg']=values['canonical_assistance_moment_Nm_kg']
            result[f'source_normalized_{coordinate}_net_moment_{role}_Nm_kg']=values['source_net_moment_Nm_kg']
            result[f'source_normalized_{coordinate}_biological_moment_{role}_Nm_kg']=values['source_biological_moment_Nm_kg']
            if canonical!='ankle_dorsiflexion':result[f'source_exo_{canonical}_interaction_torque_{role}_units_unknown']=torque
            result[f'source_grf_vertical_{role}_N']=values['source_force_vertical_N']
            result[f'grf_vertical_{role}_BW']=values['canonical_force_vertical_BW']
            result[f'derived_source_model_weight_grf_vertical_{role}']=values['derived_source_reported_model_weight_force']
    result['subject_metadata'],result['task_info']=metadata_update(old,record)
    return result


def apply_record(record,reference,output,guard=lambda:None):
    import pyarrow as pa
    import pyarrow.parquet as pq
    output=Path(output)
    if output.exists():raise FileExistsError('Preserve existing scientific output')
    old=pq.ParquetFile(reference);writer=None;count=0
    if set(old.schema_arrow.names)&added_fields():raise ValueError('Source aliases already exist; explicit successor reconciliation required')
    schema=pa.schema([*old.schema_arrow,*[pa.field(name,pa.float64()) for name in sorted(added_fields())]],metadata=old.schema_arrow.metadata)
    try:
        with numerical_source_rows(record,guard) as source:
            for batch in old.iter_batches(batch_size=512,use_threads=False):
                guard()
                if batch.nbytes>8*1024**2:raise MemoryError('Batch exceeds8MiB admission')
                rows=list(itertools.islice(source,batch.num_rows))
                if len(rows)!=batch.num_rows:raise ValueError('Reference/source row count differs')
                before=batch.to_pylist()
                if any(row['source_time_s']!=raw['angle_filt']['time'] for row,raw in zip(before,rows)):raise ValueError('Reference source clock differs')
                corrected=[corrected_row(row,raw,record) for row,raw in zip(before,rows)]
                table=pa.Table.from_pylist(corrected,schema=schema)
                if writer is None:writer=pq.ParquetWriter(output,schema,compression='zstd')
                writer.write_table(table,row_group_size=512);count+=batch.num_rows
            if next(source,None) is not None:raise ValueError('Source rows omitted by reference')
    finally:
        if writer is not None:writer.close()
    if count<2:raise ValueError('No complete continuous recording')
    return {'status':'participant_normalization_export_unverified','rows':count,'output_sha256':digest(output),'canonical_source_normalized_moments_withheld':True,'normalization_availability':normalization_availability(record),'scientific_approval':False}


def audit_record(record,reference,output,guard=lambda:None):
    """Independent scalar raw-source arithmetic plus exact unrelated readback."""
    import pyarrow.parquet as pq
    old,new=pq.ParquetFile(reference),pq.ParquetFile(output)
    if new.metadata.num_rows!=old.metadata.num_rows or set(new.schema_arrow.names)!=set(old.schema_arrow.names)|added_fields():raise ValueError('Output scope/schema differs')
    if old.schema_arrow.metadata!=new.schema_arrow.metadata:raise ValueError('Unrelated schema metadata changed')
    participant=record['participant_mass']['value_kg'];model=record['model_mass']['source_model_mass_kg'];count=0;finite={};missing={}
    # Independent acceptance: missing is not zero, borrowed model mass, or a pass.
    for name,value in [('participant',participant),('model',model)]:
        if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or value<=0):raise ValueError('Invalid '+name+' normalization mass')
    if participant is not None and record['participant_mass'].get('status')!='source_participant_mass_bound':raise ValueError('Independent documented participant mass required')
    def checked(actual,expected,name):
        absent=actual is None or math.isnan(actual);expected_absent=math.isnan(expected)
        if absent!=expected_absent:raise ValueError('Source missingness changed: '+name)
        if not absent and not math.isclose(actual,expected,rel_tol=1e-9,abs_tol=1e-9):raise ValueError('Independent participant normalization differs: '+name)
        target=missing if absent else finite;target[name]=target.get(name,0)+1
    with source_rows(record,guard) as (source,readers):
        for before,after in itertools.zip_longest(old.iter_batches(batch_size=512,use_threads=False),new.iter_batches(batch_size=512,use_threads=False)):
            guard()
            if before is None or after is None or before.num_rows!=after.num_rows:raise ValueError('Unequal complete readback')
            for name in old.schema_arrow.names:
                if name in changed_fields():continue
                a=before.column(before.schema.get_field_index(name));b=after.column(after.schema.get_field_index(name))
                if not old.schema_arrow.field(name).equals(new.schema_arrow.field(name),check_metadata=True) or not a.is_null().equals(b.is_null()) or not exact_value(a.to_pylist(),b.to_pylist()):raise ValueError('Unrelated persisted value/metadata/mask changed: '+name)
            raw_rows=list(itertools.islice(source,before.num_rows))
            if len(raw_rows)!=before.num_rows:raise ValueError('Incomplete source readback')
            for legacy,row,raw in zip(before.to_pylist(),after.to_pylist(),raw_rows):
                if not math.isclose(row['source_time_s'],raw['angle_filt']['time'],rel_tol=0,abs_tol=1e-9):raise ValueError('Source row identity differs')
                expected_subject,expected_info=metadata_update(legacy,record)
                if row['subject_metadata']!=expected_subject or row['task_info']!=expected_info:raise ValueError('Mass provenance metadata differs')
                side=row['reference_side']
                if side not in ('left','right'):raise ValueError('Unknown physical reference side')
                for role,leg in [('ipsi','l' if side=='left' else 'r'),('contra','r' if side=='left' else 'l')]:
                    get=lambda table,column:raw.get(table,{}).get(column,math.nan)
                    force=get('grf',f'fp_{leg}_force_y')
                    checked(row[f'source_grf_vertical_{role}_N'],force,'source_force_N_'+role)
                    checked(row[f'grf_vertical_{role}_BW'],force/(participant*9.81) if participant is not None else math.nan,'grf_vertical_'+role)
                    checked(row[f'derived_source_model_weight_grf_vertical_{role}'],force/(model*9.81) if model is not None else math.nan,'derived_model_weight_'+role)
                    for native,canonical,coordinate in JOINTS:
                        for kind,table in [('net','moment_filt'),('biological','moment_filt_bio')]:
                            checked(row[f'source_normalized_{coordinate}_{kind}_moment_{role}_Nm_kg'],get(table,native+'_'+leg+'_moment'),'source_'+coordinate+'_'+kind+'_'+role)
                        checked(row[f'{canonical}_moment_{role}_Nm_kg'],math.nan,'unverified_net_'+canonical+'_'+role)
                        checked(row[f'{canonical}_biological_moment_{role}_Nm_kg'],math.nan,'unverified_bio_'+canonical+'_'+role)
                        torque=math.nan if canonical=='ankle_dorsiflexion' else get('exo',native.replace('_flexion','_angle')+'_'+leg+'_torque_interaction')
                        assistance=0. if record['exo_state']=='no_exo' else math.nan
                        checked(row[f'{canonical}_assistance_moment_{role}_Nm_kg'],assistance,'assistance_'+canonical+'_'+role)
                        if canonical!='ankle_dorsiflexion':checked(row[f'source_exo_{canonical}_interaction_torque_{role}_units_unknown'],torque,'raw_interaction_'+canonical+'_'+role)
            count+=before.num_rows
        if next(source,None) is not None:raise ValueError('Source rows omitted')
        source_evidence={name:reader.evidence() for name,reader in readers.items()}
    return {'status':'participant_normalization_independent_readback_checked_unreviewed','rows':count,'source_evidence':source_evidence,'reference_sha256':digest(reference),'output_sha256':digest(output),'all_unrelated_values_field_metadata_null_masks_exact':True,'explicit_changed_fields':sorted(changed_fields()),'added_fields':sorted(added_fields()),'finite_checked_values':finite,'missing_or_withheld_values_unassessed':missing,'normalization_availability':normalization_availability(record),'scientific_approval':False}
