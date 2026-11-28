"""Prepare a separate continuous-export correction from the executed phase proposal.

Never edits active converters or the earlier proposal; numerical readback is
required before adoption. Source-clock alignment and missing measurements are
handled explicitly alongside the README-documented ankle/knee coordinates.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
TIME=Path('contributor_tools/conversion_scripts/GaTech_2024_TaskAgnostic/convert_gtech_2024_time_to_parquet.py')
README_SHA='e896c6b424c45f50f261ade2e40c5f5832065fbcd745c593b7cd72fdeb84026f'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def once(source,old,new):
    if source.count(old)!=1:raise ValueError('Unreviewed continuous source shape: '+old[:80])
    return source.replace(old,new,1)


def patch(source):
    source=once(source,'import argparse\n','import argparse\nimport json\n')
    start=source.index('    required_lengths = ');end=source.index('    angle_df = ',start)
    source=source[:start]+'''    if "angle_filt" not in data or "time" not in data["angle_filt"]:
        raise ValueError("Actual source angle clock required")
    source_clock = data["angle_filt"]["time"].to_numpy(dtype=float)
    n_samples = len(source_clock)
    if n_samples < 2 or not np.isfinite(source_clock).all() or not (np.diff(source_clock) > 0).all():
        raise ValueError("Source clock must be finite and strictly increasing")
    for name, table in data.items():
        if len(table) != n_samples or "time" not in table or not np.allclose(table["time"], source_clock, rtol=0, atol=1e-9):
            raise ValueError("Source table does not align: " + name)

'''+source[end:]
    source=once(source,'    time_s = np.arange(n_samples, dtype=float) / SAMPLING_RATE\n    sample_rate_hz = float(SAMPLING_RATE)', '''    time_s = source_clock - source_clock[0]
    intervals = np.diff(source_clock)
    sample_rate_hz = float(1.0 / intervals[0]) if np.allclose(intervals, intervals[0], rtol=0, atol=1e-9) else np.nan''')
    for side in ('ipsi','contra'):
        for variable,frame,suffix in [(f'ankle_{side}','angle_df',''),(f'ankle_vel_{side}','velocity_df','_velocity'),(f'ankle_mom_{side}','moment_df','_moment'),(f'ankle_bio_{side}','bio_moment_df','_moment')]:
            old=f'    {variable} = _series_or_nan({frame}, f"ankle_angle_{{{side}}}{suffix}", n_samples)'
            source=once(source,old,old.replace('= _series_or_nan','= -_series_or_nan'))
        old=f'    knee_vel_{side} = _series_or_nan(velocity_df, f"knee_angle_{{{side}}}_velocity", n_samples)'
        source=once(source,old,old.replace('= _series_or_nan','= -_series_or_nan'))
    old='''    else:
        hip_assist_ipsi = np.zeros(n_samples)
        hip_assist_contra = np.zeros(n_samples)
        knee_assist_ipsi = np.zeros(n_samples)
        knee_assist_contra = np.zeros(n_samples)
    ankle_assist_ipsi = np.zeros(n_samples)
    ankle_assist_contra = np.zeros(n_samples)'''
    new='''    else:
        hip_assist_ipsi = np.zeros(n_samples) if exo_state == "no_exo" else np.full(n_samples, np.nan)
        hip_assist_contra = hip_assist_ipsi.copy()
        knee_assist_ipsi = hip_assist_ipsi.copy()
        knee_assist_contra = hip_assist_ipsi.copy()
    if exo_state == "no_exo":
        hip_assist_ipsi = np.zeros(n_samples)
        hip_assist_contra = np.zeros(n_samples)
        knee_assist_ipsi = np.zeros(n_samples)
        knee_assist_contra = np.zeros(n_samples)
    ankle_assist_ipsi = np.zeros(n_samples) if exo_state == "no_exo" else np.full(n_samples, np.nan)
    ankle_assist_contra = ankle_assist_ipsi.copy()'''
    source=once(source,old,new)
    start=source.index('    grf_ant_ipsi = ');end=source.index('    cop_ant_ipsi = ',start)
    source=source[:start]+'''    grf_ant_ipsi = np.full(n_samples, np.nan)
    grf_ant_contra = np.full(n_samples, np.nan)
    grf_lat_ipsi = np.full(n_samples, np.nan)
    grf_lat_contra = np.full(n_samples, np.nan)
    source_grfs = {f"source_grf_global_{axis}_{role}_N": _series_or_nan(grf_df, f"fp_{side}_force_{axis}", n_samples)
                   for role, side in [("ipsi", ipsi), ("contra", contra)] for axis in ("x", "y", "z")}

'''+source[end:]
    source=once(source,'    cop_vert_ipsi = np.zeros(n_samples)\n    cop_vert_contra = np.zeros(n_samples)','    cop_vert_ipsi = np.full(n_samples, np.nan)\n    cop_vert_contra = np.full(n_samples, np.nan)')
    start=source.index('    subject_metadata = _build_subject_metadata(');end=source.index('    return pd.DataFrame(',start)
    source=source[:start]+'''    if exo_state not in ("no_exo", "powered", "worn_unpowered"):
        raise ValueError("Unknown exoskeleton state")
    recording = f"gt24:{data_source}/{subject_id}/{task_folder}"
    observation = recording + ":continuous:" + ("left" if ipsi == "l" else "right")
    subject_metadata = json.dumps({"weight_kg": float(subject_mass) if np.isfinite(subject_mass) else None,
        "weight_basis": "source_without_exo" if exo_state == "no_exo" else "source_model_including_worn_exo",
        "phase": collection_phase, "day": 2 if is_day2 else 1}, sort_keys=True)
    info = dict(task_info)
    info.update(time_scope="continuous_trial", time_reset_per="trial", collection_source=data_source,
        sampling_rate_hz=sample_rate_hz if np.isfinite(sample_rate_hz) else None,
        source_clock="angle_filt.time; all supplied tables matched", reference_leg=reference_leg,
        exo_state=exo_state, source_grf_frame="OpenSim_global_y_vertical",
        horizontal_grf_alignment="unresolved_trial_forward_and_anatomical_lateral_axes",
        cop_frame="OpenSim_calcn_foot_frame", cop_vertical_status="unavailable_in_source",
        moment_semantics="source_filtered_total_joint_moment_Nm_per_source_model_kg",
        biological_moment_semantics="source_total_minus_exo_interaction_when_available",
        assistance_semantics="known_absent_no_exo" if exo_state == "no_exo" else "source_interaction_torque_when_available",
        ankle_source_positive_direction="plantarflexion", ankle_canonical_transform="negation for dorsiflexion positive",
        ankle_convention_readme_sha256="READMESHA",
        knee_source_velocity_transform="negation for flexion positive; fallback derived from corrected angle",
        ankle_velocity_fallback={role: bool(np.isnan(_series_or_nan(velocity_df, f"ankle_angle_{side}_velocity", n_samples)).all()) for role,side in [("ipsi",ipsi),("contra",contra)]})
    task_info_str = json.dumps(info, sort_keys=True)
    source_ankles = {}
    for role,side in [("ipsi",ipsi),("contra",contra)]:
        for kind,table,suffix,unit,scale in [("angle",angle_df,"","rad",deg2rad),
            ("velocity",velocity_df,"_velocity","rad_s",deg2rad),
            ("moment",moment_df,"_moment","Nm_kg",1.),
            ("biological_moment",bio_moment_df,"_moment","Nm_kg",1.)]:
            source_ankles[f"source_ankle_coordinate_{kind}_{role}_{unit}"] = _series_or_nan(table, f"ankle_angle_{side}{suffix}", n_samples) * scale

'''.replace('READMESHA',README_SHA)+source[end:]
    source=once(source,'            "step": trial_path.name,','''            "step": observation,
            "source_recording_id": recording,
            "observation_id": observation,
            "observation_type": "continuous_recording",
            "reference_side": "left" if ipsi == "l" else "right",
            "source_start_time_s": float(source_clock[0]),
            "source_end_time_s": float(source_clock[-1]),
            "source_time_s": source_clock,
            **source_grfs,
            **source_ankles,''')
    ast.parse(source);return source


def main():
    p=argparse.ArgumentParser(description=__doc__);base=ROOT/'converted_datasets/reconversion_v2'
    p.add_argument('--phase-proposal',type=Path,default=base/'swarm_backlog_20261021/gt24_ankle_negation_proposal');p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    out=a.output_root.resolve()
    if not out.is_relative_to(base):raise ValueError('Isolated local output required')
    old=a.phase_proposal/'preparation_manifest.json';manifest=json.loads(old.read_text());snapshot=a.phase_proposal/'isolated_repo'
    for name,sha in manifest['snapshot_code'].items():
        if digest(snapshot/name)!=sha:raise ValueError('Original executed proposal changed')
    contents={name:(snapshot/name).read_bytes() for name in manifest['snapshot_code']};contents[str(TIME)]=patch(contents[str(TIME)].decode()).encode()
    out.mkdir(parents=True,exist_ok=False)
    for name,data in contents.items():
        dest=out/'isolated_repo'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);dest.chmod(0o444)
    report={'status':'prepared_continuous_proposal_not_run','scientific_approval':False,'parent_proposal_manifest':str(old.resolve()),'parent_manifest_sha256':digest(old),'preparation_tool_sha256':digest(__file__),'snapshot_code':{name:digest(out/'isolated_repo'/name) for name in contents},'readme_sha256':README_SHA,'changed_adapter':str(TIME),'changes':['Negate ankle angle, native velocity, net and biological moment; derivatives follow corrected values','Negate source knee extension velocity consistently with flexion angle/moment','Preserve actual aligned source clock and explicit continuous recording/side identities','Preserve original ankle coordinates and global raw GRF axes','Leave unverified horizontal anatomical GRF and unavailable vertical COP missing','Represent unavailable ankle assistance as missing except structural no-exo zeros','Structured metadata preserves source units, mass basis and velocity fallback provenance'],'required_pilot':['Two complete short recordings against executed phase pilot raw sources','Both-side source values, original missingness, exact clocks/identities, JSON metadata and continuous contract','Synthetic absent-velocity fallback, irregular clock, mismatched source clocks, absent actuator and no-exo structural cases'],'limitations':['Canonical segment orientations remain unavailable','Time exporter correction is not yet executed or scientifically approved']}
    (out/'preparation_manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'output':str(out)}))


if __name__=='__main__':main()
