"""Small executed converter regressions; no source datasets or GPU imports."""

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
from scipy.io import savemat


CONVERTERS = Path(__file__).resolve().parents[1] / "contributor_tools" / "conversion_scripts"


def load_converter(relative_path, monkeypatch):
    path = CONVERTERS / relative_path
    monkeypatch.syspath_prepend(str(path.parent))
    spec = importlib.util.spec_from_file_location(f"fixture_{path.parent.name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stroke_metadata_does_not_invent_anthropometry(monkeypatch, tmp_path):
    parser = load_converter("StrokePiG/metadata_parser.py", monkeypatch)
    metadata = parser.get_subject_metadata("TVC00", tmp_path)
    assert np.isnan(metadata["mass_kg"])
    assert np.isnan(metadata["height_m"])
    assert metadata["affected_side"] == "unknown"
    parser.set_affected_side_map({"TVC00": "r"})
    assert parser.get_subject_metadata("TVC00", tmp_path)["affected_side"] == "r"
    with pytest.raises(ValueError):
        parser.set_affected_side_map({"TVC00": "maybe_left"})


def test_stroke_measured_default_sized_mass_is_preserved(monkeypatch, tmp_path):
    parser = load_converter("StrokePiG/metadata_parser.py", monkeypatch)
    subject = tmp_path / "TVC00"
    subject.mkdir()
    (subject / "TVC-0.mp").write_text("$Bodymass = 70.0\n$Height = 1700\n")
    (subject / "TVC-1.mp").write_text("$Bodymass = 100.0\n$Height = 2000\n")
    spreadsheet = pd.DataFrame([{"subject_id": "TVC00", "Bodymass": 90.0, "Height": 1900}])
    metadata = parser.get_subject_metadata("TVC00", tmp_path, spreadsheet)
    assert metadata["mass_kg"] == 70.0
    assert metadata["height_m"] == 1.7


@pytest.fixture
def um24(monkeypatch):
    return load_converter("UMich_2024_KneeExo/convert_umich_2024_phase_to_parquet.py", monkeypatch)


def ensemble_source(tasks=("LW",)):
    curve = np.linspace(0.0, 30.0, 101)[:, None] * np.ones((1, 10))
    return {
        name: {task: curve.copy() for task in tasks}
        for name in ("kneeAngle", "thighAngle", "shankAngle", "torque", "grf")
    }


def test_ensemble_is_not_a_timed_stride(um24):
    frames = um24.process_task(ensemble_source(), "LW", "level_walking", "level", "assistance:exo_worn")
    result = pd.concat(frames)
    assert result.observation_id.nunique() == 10
    assert set(result.observation_type) == {"ensemble_curve"}
    assert set(result.reference_side) == {"unknown"}
    assert set(result.source_sample_count) == {101}
    assert all(frame.phase_ipsi.iloc[[0, -1]].tolist() == [0.0, 100.0] for frame in frames)
    derivative_columns = result.filter(regex="_velocity_|_acceleration_")
    assert derivative_columns.isna().all().all()
    np.testing.assert_allclose(frames[0].knee_flexion_angle_ipsi_rad.iloc[-1], np.pi / 6)
    np.testing.assert_allclose(frames[0].exo_torque_knee_ipsi_Nm.iloc[-1], -30.0)
    assert json.loads(frames[0].task_info.iloc[0])["timing"] == "unavailable"


def test_ensemble_mat_to_parquet_round_trip(um24, monkeypatch, tmp_path, capsys):
    source = tmp_path / "dataset_S1.mat"
    savemat(source, {"exo": ensemble_source(um24.TASK_MAPPING)})
    monkeypatch.setattr(sys, "argv", ["convert", "--input", str(source), "--output-dir", str(tmp_path)])
    um24.main()
    result = pd.read_parquet(tmp_path / "umich_2024_knee_exo_phase.parquet")
    assert result.observation_id.nunique() == 60
    assert result.groupby("observation_id").size().eq(150).all()
    output = capsys.readouterr().out
    assert "Total ensemble curves: 60" in output
    assert "Total strides:" not in output


@pytest.fixture
def gt24(monkeypatch):
    return load_converter("GaTech_2024_TaskAgnostic/convert_gtech_2024_phase_to_parquet.py", monkeypatch)


def gait_source():
    time = np.linspace(0.0, 1.0, 201)
    angles = {"time": time}
    moments, forces, cop = {}, {}, {}
    for side in ("l", "r"):
        for joint in ("hip_flexion", "knee_angle", "ankle_angle"):
            angles[f"{joint}_{side}"] = 2 * time
            moments[f"{joint}_{side}_moment"] = np.ones_like(time)
        for axis in ("x", "y", "z"):
            forces[f"fp_{side}_force_{axis}"] = np.full_like(time, 100.0)
        for axis in ("x", "z"):
            cop[f"insole_{side}_cop_{axis}"] = np.zeros_like(time)
    return {
        "angle_filt": pd.DataFrame(angles),
        "moment_filt": pd.DataFrame(moments),
        "grf": pd.DataFrame(forces),
        "insole_sim": pd.DataFrame(cop),
    }


def convert_gt24(gt24, recording, step=0, side="l"):
    return gt24.process_stride(
        gait_source(), 0, 200, "BT01", 70.0, "level_walking", "level",
        {}, step, side, 1, "no_exo", source_recording_id=recording,
        skip_segment_angles=True,
    )


def test_gt24_identity_distinguishes_trials_and_survives_counter_changes(gt24):
    first = convert_gt24(gt24, "gt24:Parsed/BT01/trial_A", step=0)
    repeated = convert_gt24(gt24, "gt24:Parsed/BT01/trial_A", step=123)
    other_trial = convert_gt24(gt24, "gt24:Parsed/BT01/trial_B", step=0)
    other_leg = convert_gt24(gt24, "gt24:Parsed/BT01/trial_A", side="r")
    assert first.observation_id.iloc[0] == repeated.observation_id.iloc[0]
    assert len({frame.observation_id.iloc[0] for frame in (first, other_trial, other_leg)}) == 3
    assert first.step.equals(first.observation_id)
    assert first.reference_side.iloc[0] == "left"
    assert first.source_end_time_s.iloc[0] == 1.0
    assert json.loads(first.subject_metadata.iloc[0])["weight_kg"] == 70.0


def test_gt24_derivative_matches_included_endpoint(gt24):
    result = convert_gt24(gt24, "gt24:Parsed/BT01/trial_A")
    np.testing.assert_allclose(result.hip_flexion_angle_ipsi_rad.iloc[-1], np.deg2rad(2.0))
    np.testing.assert_allclose(result.hip_flexion_velocity_ipsi_rad_s, np.deg2rad(2.0), atol=1e-12)
    np.testing.assert_allclose(result.hip_flexion_acceleration_ipsi_rad_s2, 0.0, atol=1e-10)


def test_gt24_unknown_subject_mass_is_unavailable(gt24):
    assert np.isnan(gt24.get_subject_mass("unknown_subject", "Parsed"))


@pytest.mark.parametrize("source_sign", [-1.0, 1.0])
def test_gt24_preserves_source_force_sign_and_marks_unresolved_channels(gt24, source_sign):
    source = gait_source()
    for side in ("l", "r"):
        for axis in ("x", "z"):
            source["grf"][f"fp_{side}_force_{axis}"] = source_sign * 100.0
    result = gt24.process_stride(
        source, 0, 200, "BT01", 70.0, "level_walking", "level",
        {}, 0, "l", 1, "powered", source_recording_id="gt24:Phase1And2/BT01/fixture",
        skip_segment_angles=True,
    )
    for axis in ("x", "z"):
        for side in ("ipsi", "contra"):
            np.testing.assert_allclose(result[f"source_grf_global_{axis}_{side}_N"], source_sign * 100.0)
    for side in ("ipsi", "contra"):
        assert result[f"grf_anterior_{side}_BW"].isna().all()
        assert result[f"grf_lateral_{side}_BW"].isna().all()
        assert result[f"cop_vertical_{side}_m"].isna().all()
    assistance = result.filter(regex="assistance.*Nm_kg")
    assert not assistance.empty
    assert assistance.isna().all().all()
    info = json.loads(result.task_info.iloc[0])
    assert info["horizontal_grf_sign_transform"] == "none_source_axes_preserved"
    assert info["source_grf_frame"] == "OpenSim_global_y_vertical"
    assert json.loads(result.subject_metadata.iloc[0])["weight_basis"] == "source_model_including_worn_exo"


@pytest.fixture
def stroke(monkeypatch):
    return load_converter("StrokePiG/convert_strokepig_to_parquet.py", monkeypatch)


@pytest.mark.parametrize("affected,reference", [("unknown", "l"), ("l", "l"), ("r", "r")])
def test_stroke_clinical_side_is_preserved(stroke, affected, reference):
    metadata = {"mass_kg": 70.0, "affected_side": affected}
    side = stroke.reference_side_for_subject(metadata)
    assert side == reference
    source = gait_source()["angle_filt"]
    source["pelvis_tilt"] = 0.0
    processed = stroke.process_stride(source, 0, 200, side, 70.0, 0)
    result = stroke._build_stride_dataframe(
        processed, None, None, "TVC03", metadata, side,
        processed["stride_duration_s"], 0, "sp50:TVC03/BWA6_ik.mot",
    )
    expected = {"l": "left", "r": "right"}.get(affected, "unknown")
    assert set(result.affected_side) == {expected}
    assert json.loads(result.task_info.iloc[0])["affected_side"] == expected
    assert json.loads(result.subject_metadata.iloc[0])["affected_side"] == expected
    assert result.source_start_sample.iloc[0] == 0
    assert result.source_end_sample.iloc[0] == 200


def test_stroke_missing_channel_remains_missing_and_invalid_time_is_rejected(stroke):
    source = gait_source()["angle_filt"].drop(columns=["hip_flexion_l"])
    result = stroke.process_stride(source, 0, 200, "l", 70.0, 0)
    assert np.isnan(result["hip_flexion_angle_ipsi_rad"]).all()
    source["time"] = 0.0
    assert stroke.process_stride(source, 0, 200, "l", 70.0, 0) is None


def test_gt24_mapped_tasks_are_canonical_and_backward_remains_distinct(gt24, monkeypatch):
    from contributor_tools.common.task_registry import is_valid_task
    from contributor_tools.common.data_contract import inspect_contract
    for task, _, _ in gt24.TASK_MAPPING.values():
        assert task is None or is_valid_task(task), task
    mapping = load_converter('GaTech_2024_TaskAgnostic/task_mapping.py', monkeypatch)
    for task, _, _ in mapping.FULL_TASK_MAPPING.values():
        assert task is None or is_valid_task(task), task
    for speed in ['0-6', '0-8', '1-0']:
        task, task_id, info = gt24.map_task_name(f'walk_backward_1_1_{speed}_on')
        assert task == 'walk_backward'
        result = gt24.process_stride(gait_source(), 0, 200, 'BT01', 70., task, task_id,
                                    info, 0, 'l', 1, 'powered',
                                    source_recording_id=f'gt24:Phase3/BT01/backward_{speed}',
                                    skip_segment_angles=True)
        assert inspect_contract(result, mode='phase').schema_passed


@pytest.fixture
def gt25(monkeypatch):
    return load_converter('GaTech_2025_DomainAdaptation/convert_gtech_2025_da_to_parquet.py', monkeypatch)


def test_gt25_inclusive_endpoint_and_velocity_use_actual_source_times(gt25):
    source = gait_source()
    # A nonuniform clock makes index-based interpolation observably incorrect.
    clock = np.linspace(0,1,201)**1.1
    source['angle_filt']['time'] = clock
    for side in ['l','r']:
        for joint in ['hip_flexion','knee_angle','ankle_angle']:
            source['angle_filt'][f'{joint}_{side}'] = 2*clock
    result = gt25.process_stride(source,0,200,'BT01',70.,'level_walking','level',{},0,'l','baseline',skip_segment_angles=True,source_recording_id='gt25:Parsed/BT01/fixture')
    np.testing.assert_allclose(result.hip_flexion_angle_ipsi_rad,np.deg2rad(2*np.linspace(0,1,150)),atol=1e-12)
    np.testing.assert_allclose(result.hip_flexion_velocity_ipsi_rad_s,np.deg2rad(2.),atol=1e-12)


def test_gt25_unknown_mass_and_unmeasured_assistance_stay_missing(gt25):
    mass = gt25.get_subject_mass('unknown_subject')
    assert np.isnan(mass)
    result=gt25.process_stride(gait_source(),0,200,'unknown_subject',mass,'level_walking','level',{},0,'l','baseline',skip_segment_angles=True,source_recording_id='gt25:Parsed/BT01/fixture')
    assert result.grf_vertical_ipsi_BW.isna().all()
    assert result.hip_flexion_angle_ipsi_rad.notna().all()
    assistance=result.filter(regex='assistance_moment_')
    assert len(assistance.columns)>0
    assert assistance.isna().all().all()


def test_gt25_resampling_does_not_bridge_missing_source_samples(gt25):
    values=np.array([0.,1.,np.nan,3.,4.])
    result=gt25.interpolate_to_phase(values,num_points=9)
    assert np.isnan(result[3:6]).all()
    assert result[0]==0 and result[-1]==4


def test_gt25_force_sign_is_not_selected_from_expected_waveform(gt25):
    positive=gait_source();negative=gait_source()
    negative['grf']=-negative['grf']
    def convert(source):
        return gt25.process_stride(source,0,200,'BT01',70.,'level_walking','level',{},0,'l','baseline',skip_segment_angles=True,source_recording_id='gt25:Parsed/BT01/fixture')
    a,b=convert(positive),convert(negative)
    for feature in ['source_grf_global_x_ipsi_N','source_grf_global_z_ipsi_N','source_grf_global_x_contra_N','source_grf_global_z_contra_N']:
        np.testing.assert_allclose(a[feature],-b[feature])
    assert a.cop_vertical_ipsi_m.isna().all()
    assert a.grf_anterior_ipsi_BW.isna().all()
    assert a.grf_lateral_ipsi_BW.isna().all()


def test_gt25_identity_is_source_based_and_contract_valid(gt25):
    from contributor_tools.common.data_contract import inspect_contract
    def make(recording, step=0, side='l'):
        return gt25.process_stride(gait_source(),0,200,'BT01',70.,'level_walking','level',{},step,side,'baseline',skip_segment_angles=True,source_recording_id=recording)
    first=make('gt25:Parsed/BT01/trial_A')
    assert inspect_contract(first,mode='phase').schema_passed
    assert make('gt25:Parsed/BT01/trial_A',99).observation_id.equals(first.observation_id)
    assert make('gt25:Parsed/BT01/trial_B').observation_id.iloc[0] != first.observation_id.iloc[0]
    assert make('gt25:Parsed/BT01/trial_A',side='r').observation_id.iloc[0] != first.observation_id.iloc[0]
    assert first.source_end_time_s.iloc[0] == 1.
    assert first.time_s.iloc[-1] == 1.
    with pytest.raises(ValueError,match='source_recording_id'):
        make(None)


def test_gt25_trial_propagates_original_recording_identity(gt25, monkeypatch, tmp_path):
    from types import SimpleNamespace
    trial=tmp_path/'normal_walk_1_baseline_1-2_on';trial.mkdir()
    monkeypatch.setattr(gt25,'load_trial_data',lambda *args:gait_source())
    monkeypatch.setattr(gt25,'segment_trial_gait',lambda *args:[SimpleNamespace(start_idx=0,end_idx=200)])
    frames=gt25.process_trial(trial,'BT01')
    assert len(frames)==2
    assert {f.source_recording_id.iloc[0] for f in frames}=={'gt25:Parsed/BT01/normal_walk_1_baseline_1-2_on'}
    assert {f.reference_side.iloc[0] for f in frames}=={'left','right'}


def test_gt25_long_transfer_is_not_rejected_as_a_long_walking_stride(gt25):
    source=gait_source()
    # Expand the fixture to a 4-second transfer sampled at 200 Hz.
    for key,frame in source.items():
        source[key]=pd.concat([frame.iloc[:-1]]*4+[frame.iloc[-1:]],ignore_index=True)
    source['angle_filt']['time']=np.arange(801)/200
    for side in ['l','r']:
        source['angle_filt'][f'hip_flexion_{side}']=np.linspace(30,0,801)
    result=gt25.process_stride(source,0,800,'BT01',70.,'sit_to_stand','sit_to_stand',{},0,'l','baseline',skip_segment_angles=True,source_recording_id='gt25:Parsed/BT01/transfer')
    assert result is not None
    assert result.observation_type.iloc[0]=='transfer'
    assert result.time_s.iloc[-1]==4
    np.testing.assert_allclose(result.hip_flexion_velocity_ipsi_rad_s,np.deg2rad(-7.5))


def test_gt25_all_enabled_task_mappings_are_canonical(gt25, monkeypatch):
    from contributor_tools.common.task_registry import is_valid_task
    for task,_,_ in gt25.TASK_MAPPING.values():
        assert task is None or is_valid_task(task)
    mapping=load_converter('GaTech_2025_DomainAdaptation/task_mapping.py',monkeypatch)
    for task,_,_ in mapping.FULL_TASK_MAPPING.values():
        assert task is None or is_valid_task(task)


def test_gt25_retains_complete_cycles_in_short_parsed_stair_trials(gt25):
    time=np.arange(701)/200
    force=np.zeros(701)
    for start in [100,300,500]:force[start:start+100]=700
    source=pd.DataFrame({'time_s':time,'grf_vertical_ipsi_N':force})
    segments=gt25.segment_trial_gait(source,'l')
    assert len(segments)==2
    assert all(np.isclose(s.duration_s,1.) for s in segments)


def test_gt24_retains_complete_cycles_in_short_parsed_stair_trials(gt24):
    time=np.arange(701)/200
    force=np.zeros(701)
    for start in [100,300,500]:force[start:start+100]=700
    source=pd.DataFrame({'time_s':time,'grf_vertical_ipsi_N':force})
    segments=gt24.segment_trial_gait(source,'l')
    assert len(segments)==2
    assert all(np.isclose(s.duration_s,1.) for s in segments)


def test_gt24_long_transfer_is_not_rejected_as_a_long_walking_stride(gt24):
    source=gait_source()
    for key,frame in source.items():
        source[key]=pd.concat([frame.iloc[:-1]]*4+[frame.iloc[-1:]],ignore_index=True)
    source['angle_filt']['time']=np.arange(801)/200
    for side in ['l','r']:
        source['angle_filt'][f'hip_flexion_{side}']=np.linspace(30,0,801)
    result=gt24.process_stride(source,0,800,'BT01',70.,'sit_to_stand','sit_to_stand',{},0,'l',3,'powered',skip_segment_angles=True,source_recording_id='gt24:Phase3/BT01/transfer')
    assert result is not None
    assert result.observation_type.iloc[0]=='transfer'
    assert result.source_end_time_s.iloc[0]-result.source_start_time_s.iloc[0]==4
    np.testing.assert_allclose(result.hip_flexion_velocity_ipsi_rad_s,np.deg2rad(-7.5))


def test_gt24_uses_actual_nonuniform_source_timestamps(gt24):
    source=gait_source()
    clock=np.linspace(0,1,201)**1.1
    source['angle_filt']['time']=clock
    for side in ['l','r']:
        source['angle_filt'][f'hip_flexion_{side}']=2*clock
    result=gt24.process_stride(source,0,200,'BT01',70.,'level_walking','level',{},0,'l',3,'powered',skip_segment_angles=True,source_recording_id='gt24:Phase3/BT01/nonuniform')
    np.testing.assert_allclose(result.hip_flexion_angle_ipsi_rad,np.deg2rad(2*np.linspace(0,1,150)),atol=1e-12)
    np.testing.assert_allclose(result.hip_flexion_velocity_ipsi_rad_s,np.deg2rad(2),atol=1e-12)


def test_gt24_preserves_missing_samples_and_rejects_misaligned_clocks(gt24):
    values=gt24.interpolate_to_phase(np.array([0.,1.,np.nan,3.,4.]),num_points=9)
    assert np.isnan(values[3:6]).all()
    source=gait_source()
    source['grf']['time']=source['angle_filt']['time']+0.02
    with pytest.raises(ValueError,match='timestamps do not align'):
        gt24.process_stride(source,0,200,'BT01',70.,'level_walking','level',{},0,'l',3,'powered',skip_segment_angles=True,source_recording_id='gt24:Phase3/BT01/misaligned')


@pytest.fixture
def mblue(monkeypatch):
    return load_converter('MBLUEAnkle/convert_mblue_ankle_to_parquet.py',monkeypatch)


def mblue_source(with_times=True):
    fields={}
    for side in ['l','r']:
        for joint in ['hip_flexion','knee_angle','ankle_angle']:
            fields[f'{joint}_{side}']=np.linspace(0,10,101)[:,None]
        if with_times:fields[f'time_{side}']=np.linspace(0,1,101)[:,None]
    result=np.empty((),dtype=[(name,object) for name in fields])
    for name,value in fields.items():result[name][()]=value
    return result[()]


def test_mblue_missing_time_and_pelvis_do_not_become_measurements(mblue):
    source=mblue_source(False)
    assert np.isnan(mblue.extract_stride_duration(source,'l',0))
    frames,_=mblue.process_gait_task(source,'AB01',70.,'level_walking','level',1.,'bare')
    assert len(frames)==2
    for frame in frames:
        assert frame.phase_ipsi_dot.isna().all()
        assert frame.hip_flexion_velocity_ipsi_rad_s.isna().all()
        assert frame.pelvis_sagittal_angle_rad.isna().all()
        assert frame.hip_flexion_angle_contra_rad.isna().all()
        assert frame.hip_flexion_angle_ipsi_rad.notna().all()


def test_mblue_overlap_uses_time_not_stride_index_and_retains_gaps(mblue):
    ipsi=np.linspace(0,4,9)
    times=np.array([[0,3],[.5,3.5],[1,4.]])
    values=2*times
    result=mblue.time_sync_contra_data(ipsi,times,values,9)
    np.testing.assert_allclose(result[[0,1,2,6,7,8]],[0,1,2,6,7,8])
    assert np.isnan(result[3:6]).all()
    # Unequal curve counts are rejected instead of clamping the last curve.
    with pytest.raises(ValueError,match='identical shapes'):
        mblue.time_sync_contra_data(ipsi,times,values[:,:1],9)
    conflict=mblue.time_sync_contra_data([0,1],np.array([[0,0],[1,1]]),np.array([[0,5],[1,6]]),3)
    assert np.isnan(conflict).all()


def test_mblue_missing_source_samples_are_not_bridged(mblue):
    result=mblue.interpolate_to_phase(np.array([0.,1.,np.nan,3.,4.]),9).ravel()
    assert np.isnan(result[3:6]).all()
    source=mblue_source()
    source['time_l'][50,0]=source['time_l'][49,0]
    assert np.isnan(mblue.extract_stride_duration(source,'l',0))


@pytest.fixture
def gait120(monkeypatch):
    return load_converter('Gait120/convert_gait120_to_parquet.py',monkeypatch)


def test_gait120_timing_requires_finite_increasing_source_clock(gait120):
    for frame in [pd.DataFrame({'angle':[1,2]}),pd.DataFrame({'time':[0,0]}),pd.DataFrame({'time':[0,np.nan,1]}),pd.DataFrame({'time':[0,2,1]})]:
        assert np.isnan(gait120.estimate_stride_duration_from_mot(frame))
    assert gait120.estimate_stride_duration_from_mot(pd.DataFrame({'time':[10,10.3,11.2]}))==pytest.approx(1.2)


def test_gait120_reconstruction_rejects_unknown_anthropometry(gait120,monkeypatch,tmp_path):
    monkeypatch.setattr(gait120,'RUN_FULL_PIPELINE',True)
    with pytest.raises(ValueError,match='Measured mass and height'):
        gait120.process_step_file(tmp_path/'absent.mot','G120_unknown','level_walking','level',0)


def test_gait120_anthropometry_does_not_invent_or_ambiguously_select(monkeypatch,tmp_path):
    helper=load_converter('Gait120/scale_model.py',monkeypatch)
    source=pd.DataFrame({'Subject':['S001'],'Height(mm)':[1750.], 'Bodymass(Kg)':[np.nan], 'Leglength(mm)':[900.]})
    monkeypatch.setattr(helper,'load_anthropometric_data',lambda root:source)
    result=helper.get_subject_anthropometrics('S001',tmp_path)
    assert np.isnan(result['mass_kg']) and result['height_m']==1.75
    with pytest.raises(ValueError,match='Expected one'):
        helper.get_subject_anthropometrics('missing',tmp_path)
    source=pd.concat([source,source],ignore_index=True)
    with pytest.raises(ValueError,match='Expected one'):
        helper.get_subject_anthropometrics('S001',tmp_path)


def test_gait120_kinematics_keeps_missing_metadata_and_pelvis(gait120,monkeypatch,tmp_path):
    time=np.linspace(0,1,101)
    source=pd.DataFrame({f'{joint}_{side}':10*time for joint in ['hip_flexion','knee_angle','ankle_angle'] for side in ['l','r']})
    source['time']=time
    monkeypatch.setattr(gait120,'load_mot_file',lambda path:source)
    frame=gait120.process_step_file(tmp_path/'Step01.mot','G120_unknown','level_walking','level',0)
    assert frame is not None
    metadata=json.loads(frame.subject_metadata.iloc[0])
    assert metadata['weight_kg'] is None and metadata['height_m'] is None
    assert 'sex' not in metadata
    assert frame.pelvis_sagittal_angle_rad.isna().all()
    assert frame.thigh_sagittal_angle_ipsi_rad.isna().all()
    assert frame.hip_flexion_angle_ipsi_rad.notna().all()


def test_gait120_preserves_right_reference_source_order_and_clock(gait120,monkeypatch,tmp_path):
    clock=np.linspace(0,1,101)**1.3
    source=pd.DataFrame({f'{joint}_{side}':offset+10*clock
                         for joint in ['hip_flexion','knee_angle','ankle_angle']
                         for side,offset in [('r',5),('l',40)]})
    source['time']=clock+3
    monkeypatch.setattr(gait120,'load_mot_file',lambda path:source)
    path=tmp_path/'S001/JointAngle/LevelWalking/Trial01/step01.mot'
    frame=gait120.process_step_file(path,'G120_S001','level_walking','level',0)
    np.testing.assert_allclose(frame.hip_flexion_angle_ipsi_rad,np.deg2rad(5+10*np.linspace(0,1,150)))
    np.testing.assert_allclose(frame.hip_flexion_angle_contra_rad,np.deg2rad(40+10*np.linspace(0,1,150)))
    np.testing.assert_allclose(frame.hip_flexion_velocity_ipsi_rad_s,np.deg2rad(10),atol=1e-12)
    assert frame.reference_side.eq('right').all()
    assert frame.source_start_time_s.iloc[0]==3 and frame.source_end_time_s.iloc[0]==4
    from contributor_tools.common.data_contract import inspect_contract
    assert inspect_contract(frame,mode='phase').schema_passed
    with pytest.raises(ValueError,match='right-foot reference'):
        gait120.process_step_file(path,'G120_S001','level_walking','level',0,leg_side='l')


def test_gait120_missing_samples_are_not_interpolated_away(gait120):
    result=gait120.interpolate_to_phase(np.array([0.,1.,np.nan,3.,4.]),9)
    assert np.isnan(result[3:6]).all()


def test_gait120_force_plates_preserve_axes_clock_and_missing_values(gait120):
    source=pd.DataFrame({'time':[2.,2.2,3.], 'ground_force1_vx':[10.,20.,40.],
                         'ground_force2_vy':[100.,np.nan,300.],
                         'ground_force1_pz':[.1,.2,.4], 'ground_torque1_y':[1.,2.,4.]})
    result=gait120.resample_source_force_plates(source,np.array([1.9,2.,2.1,2.2,3.,3.1]))
    np.testing.assert_allclose(result['source_plate1_force_x_N'],[np.nan,10.,15.,20.,40.,np.nan],equal_nan=True)
    np.testing.assert_allclose(result['source_plate1_cop_z_m'],[np.nan,.1,.15,.2,.4,np.nan],equal_nan=True)
    assert np.isnan(result['source_plate2_force_y_N'][2:4]).all()
    assert 'source_plate2_force_x_N' not in result
    source.time=[2.,2.,3.]
    with pytest.raises(ValueError,match='strictly increasing'):
        gait120.resample_source_force_plates(source,np.array([2.,3.]))



def test_stroke_annotated_strikes_override_peak_heuristic(stroke,monkeypatch):
    source=pd.DataFrame({'time':np.arange(601)/100})
    events=[{'label':'Foot Strike','side':'left','time_s':t} for t in [.5,5.]]
    monkeypatch.setattr(stroke,'detect_heel_strikes_from_kinematics',lambda *args:pytest.fail('Source annotations must take precedence'))
    assert stroke.segment_trial_into_strides(source,'l',source_events=events)==[(50,500)]
    assert source.attrs['phase_boundary_method']=='source_c3d_foot_strike_annotations'
    assert source.attrs['segmentation_candidates'][0]['accepted']


def test_stroke_inclusive_endpoint_and_actual_time(stroke):
    clock=np.linspace(0,1,201)**1.1
    source=pd.DataFrame({'time':clock,'hip_flexion_l':2*clock})
    result=stroke.process_stride(source,0,200,'l',70.,0)
    assert result['source_end_sample']==200 and result['source_end_time_s']==1.
    np.testing.assert_allclose(result['hip_flexion_angle_ipsi_rad'],np.deg2rad(2*np.linspace(0,1,150)),atol=1e-12)
    np.testing.assert_allclose(result['hip_flexion_velocity_ipsi_rad_s'],np.deg2rad(2),atol=1e-12)
    assert np.isnan(stroke.interpolate_to_phase(np.array([0.,1.,np.nan,3.,4.]),9)[3:6]).all()


def test_stroke_c3d_clock_restores_acquisition_frame_number(monkeypatch,tmp_path):
    from types import SimpleNamespace
    parser=load_converter('StrokePiG/c3d_parser.py',monkeypatch)
    raw={'header':{'points':{'frame_rate':100.,'first_frame':933},'analogs':{'frame_rate':1000.}},'data':{'points':np.empty((4,0,2))}}
    monkeypatch.setattr(parser,'EZC3D_AVAILABLE',True)
    monkeypatch.setattr(parser,'ezc3d',SimpleNamespace(c3d=lambda path:raw),raising=False)
    monkeypatch.setattr(parser,'_extract_markers',lambda raw,time:None)
    monkeypatch.setattr(parser,'_extract_force_plates',lambda raw,time:None)
    path=tmp_path/'source.c3d';path.write_bytes(b'fixture')
    np.testing.assert_allclose(parser.load_c3d_file(path)['time'],[9.34,9.35])


def test_mblue_source_identity_survives_output_reordering(mblue):
    import json
    from contributor_tools.common.data_contract import inspect_contract
    source=mblue_source()
    first,_=mblue.process_gait_task(source,'AB01',70.,'level_walking','level',1.,'bare',0,task_key='level_1x0')
    reordered,_=mblue.process_gait_task(source,'AB01',70.,'level_walking','level',1.,'bare',999,task_key='level_1x0')
    assert [f.observation_id.iloc[0] for f in first]==[f.observation_id.iloc[0] for f in reordered]
    assert len({f.observation_id.iloc[0] for f in first})==2
    for frame in first:
        assert inspect_contract(frame,mode='phase').schema_passed
        assert json.loads(frame.subject_metadata.iloc[0])['weight_kg']==70.
        np.testing.assert_allclose(frame.time_s,np.linspace(0,1,150))
    stairs=first[0].copy()
    a=mblue.identify_gait_curve
    # Two distinct source blocks must not share identities even at equal timestamps.
    for col in ['subject_metadata','task_info']:
        stairs[col]='source:fixture'
    other=a(stairs,'AB01','exo','stairs/descent/s2','l',0,0.,1.)
    assert other.observation_id.iloc[0]!=first[0].observation_id.iloc[0]


def test_mblue_bilateral_duration_uses_matching_source_clocks(mblue):
    source=mblue_source()
    assert mblue.bilateral_source_times(source,0)==(0.,1.)
    source['time_r'][50,0]+=.001
    with pytest.raises(ValueError,match='clocks disagree'):
        mblue.bilateral_source_times(source,0)
    with pytest.raises(ValueError,match='clocks are required'):
        mblue.bilateral_source_times(mblue_source(False),0)


def test_mblue_transfer_interpolation_uses_recorded_nonuniform_clock(mblue):
    from contributor_tools.common.data_contract import inspect_contract
    source=mblue_source()
    clock=np.linspace(0,1,101)**2
    for side in ['l','r']:
        source['time_'+side][:,0]=clock
        source['hip_flexion_'+side][:,0]=10*clock
    frames,_=mblue.process_bilateral_task(source,'AB01',70.,'sit_to_stand','sit_stand','bare',source_task_path='STS/sit_stand')
    assert len(frames)==1 and inspect_contract(frames[0],mode='phase').schema_passed
    np.testing.assert_allclose(frames[0].hip_flexion_angle_ipsi_rad,np.linspace(0,10,150)*np.pi/180,atol=1e-12)
    np.testing.assert_allclose(frames[0].hip_flexion_velocity_ipsi_rad_s,10*np.pi/180,atol=1e-12)
    assert frames[0].observation_type.eq('transfer').all()


def test_mblue_gait_interpolation_uses_source_clock_on_both_sides(mblue):
    source=mblue_source()
    clock=np.linspace(0,1,101)**2
    for side in ['l','r']:
        source['time_'+side][:,0]=clock
        source['hip_flexion_'+side][:,0]=10*clock
    frames,_=mblue.process_gait_task(source,'AB01',70.,'level_walking','level',1.,'bare')
    for frame in frames:
        for role in ['ipsi','contra']:
            np.testing.assert_allclose(frame[f'hip_flexion_angle_{role}_rad'],np.linspace(0,10,150)*np.pi/180,atol=1e-12)
            np.testing.assert_allclose(frame[f'hip_flexion_velocity_{role}_rad_s'],10*np.pi/180,atol=1e-12)


def test_mblue_derivatives_do_not_fill_a_missing_center_sample(mblue):
    values=np.array([0.,1.,np.nan,3.,4.])
    velocity=mblue.compute_velocity_from_angle(values,4.)
    acceleration=mblue.compute_acceleration_from_velocity(values,4.)
    assert np.isnan(velocity[1:4]).all()
    assert np.isnan(acceleration[1:4]).all()
    np.testing.assert_allclose(velocity[[0,4]],1.)


@pytest.mark.parametrize('reference_side', ['l', 'r'])
def test_gt24_failed_loadcell_torques_remain_missing_for_both_reference_sides(gt24, reference_side):
    data = gait_source()
    for joint in ('hip_flexion', 'knee_angle', 'ankle_angle'):
        data['moment_filt'][f'{joint}_r_moment'] = np.nan
    data['moment_filt_bio'] = data['moment_filt'].copy()
    result = gt24.process_stride(
        data, 0, 200, 'BT01', 70.0, 'level_walking', 'level', {}, 0,
        reference_side, 1, 'no_exo', source_recording_id='synthetic:failed_right_loadcell',
        skip_segment_angles=True,
    )
    failed_role = 'ipsi' if reference_side == 'r' else 'contra'
    healthy_role = 'contra' if reference_side == 'r' else 'ipsi'
    for joint in ('hip_flexion', 'knee_flexion', 'ankle_dorsiflexion'):
        for kind in ('moment', 'biological_moment'):
            assert result[f'{joint}_{kind}_{failed_role}_Nm_kg'].isna().all()
            assert np.isfinite(result[f'{joint}_{kind}_{healthy_role}_Nm_kg']).all()
        assert np.isfinite(result[f'{joint}_angle_{failed_role}_rad']).all()


def pelvis_source(left, right, pelvis):
    fields={'time_l':np.asarray(left), 'time_r':np.asarray(right), 'pelvis_tilt':np.asarray(pelvis)}
    for side,clock in [('l',fields['time_l']),('r',fields['time_r'])]:
        for joint in ['hip_flexion','knee_angle','ankle_angle']:
            fields[f'{joint}_{side}']=np.zeros_like(clock)
    result=np.empty((),dtype=[(name,object) for name in fields])
    for name,value in fields.items():result[name][()]=value
    return result[()]


def test_mblue_pelvis_uses_left_clock_for_right_reference_cycle(mblue):
    left=np.linspace(0,1,101)[:,None]
    right=np.linspace(.5,1.5,101)[:,None]
    source=pelvis_source(left,right,20*left)
    frames,_=mblue.process_gait_task(source,'AB01',70.,'level_walking','level',1.,'bare')
    frame=next(f for f in frames if f.reference_side.iloc[0]=='right')
    target=np.linspace(.5,1.5,150)
    expected=np.where(target<=1,20*target*np.pi/180,np.nan)
    np.testing.assert_allclose(frame.pelvis_sagittal_angle_rad,expected,equal_nan=True)
    np.testing.assert_allclose(frame.thigh_sagittal_angle_ipsi_rad,expected,equal_nan=True)
    assert frame.pelvis_sagittal_velocity_rad_s.iloc[80:].isna().all()


def test_mblue_pelvis_recovers_time_overlap_without_matching_column_index(mblue):
    left=np.linspace(0,1,101)[:,None]
    target=np.linspace(.2,.8,101)
    source=pelvis_source(left,np.column_stack([left[:,0],target]),10*left)
    actual=mblue.align_pelvis_to_stride(source,'r',1,target)
    np.testing.assert_allclose(actual,np.linspace(2,8,150)*np.pi/180)


def test_mblue_pelvis_preserves_explicit_shared_stair_windows(mblue):
    clock=np.column_stack([np.linspace(0,1,101)]*2)
    # Distinct trials can reuse their clocks; direct shared column identity wins.
    values=np.column_stack([np.full(101,5.),np.full(101,20.)])
    source=pelvis_source(clock,clock,values)
    actual=mblue.align_pelvis_to_stride(source,'r',1,clock[:,1])
    np.testing.assert_allclose(actual,20*np.pi/180)


def test_mblue_right_pelvis_missing_clock_does_not_use_left_phase(mblue):
    clock=np.linspace(0,1,101)[:,None]
    source=pelvis_source(clock,clock,10*clock)
    assert np.isnan(mblue.align_pelvis_to_stride(source,'r',0,None)).all()
