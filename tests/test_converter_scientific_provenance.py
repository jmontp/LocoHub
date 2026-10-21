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
    assert result.source_end_sample.iloc[0] == 199


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
