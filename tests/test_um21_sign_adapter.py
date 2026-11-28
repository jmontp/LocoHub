"""CORE-11-P-UM21 adapter and pilot spec, on SYNTHETIC fixtures only.

The recordings here are a small synthetic HDF5 file laid out like UM21 Streaming.mat (Streaming/<subject>/
Tread/<condition>/{jointAngles, jointMoments, jointPowers, markers, forceplates, events} and a
ParticipantDetails cell array). Its motion is the gait-like leg of tests/test_sign_offset_detector.py
(seed 41), built in rule B and then stored in the UM21 source conventions recorded by UM21-C03 (pelvis
clinical, i.e. -rule B; hip, knee, ankle angles and moments as rule B; power layout 1 stores -(M x w)).
"AB02/i0" stores that motion normally; "AB04/i0" stores the same motion with the pelvis computed facing
backwards (tilt negated), as UM21-P01 found in the real AB04/i0; "AB05/i0" stores it with power layout 2
(components 1 and 2 zero, component 3 = +(M x w)), as the UM21-C03 record lists for the real AB05/i0. Expected values come from the synthetic
truth, not from the adapter. The real committed audited-sign table and backlog are used (UM21 entries
verified; the AB04/i0 correction active). No research dataset is read and nothing is launched.
"""
import copy
import json
import random
from pathlib import Path

import h5py
import numpy as np
import pytest

from contributor_tools import run_core11_um21_pilot as pilot
from contributor_tools.adapters import um21_sign_adapter as um21
from contributor_tools.common import sign_application as sa
from contributor_tools.guarded_launcher import SpecError, validate_spec
from tests.test_sign_offset_detector import N, synthetic_leg

BUILD = sa.file_sha256(sa.DETECTOR_PATH)
MASS_KG = 70.0
UNITS = 24  # synthetic strides stored back to back; 23 complete heel-strike pairs pass the stride rule
HOOK_INPUTS = {"pelvis_tilt", "hip_angle", "knee_angle", "ankle_angle", "hip_moment", "knee_moment",
               "ankle_moment", "hip_power", "knee_power", "ankle_power"}


def _flat(a):
    """(units, N, ...) -> continuous frames (units * N, ...)."""
    return a.reshape((a.shape[0] * a.shape[1],) + a.shape[2:])


def _char(group, name, text):
    ds = group.create_dataset(name, data=np.array([[ord(c)] for c in text], dtype=np.uint16))
    ds.attrs["MATLAB_class"] = b"char"
    return ds.ref


def _write_recording(f, subject, condition, truth, pts, cop, grf, reverse_pelvis, layout=1):
    g = f.create_group(f"Streaming/{subject}/Tread/{condition}")
    n = UNITS * N
    stored = {"Pelvis": -truth["pelvis_tilt"], "Hip": truth["hip_angle"], "Knee": truth["knee_angle"],
              "Ankle": truth["ankle_angle"]}  # UM21 source conventions (UM21-C03)
    if reverse_pelvis:
        stored["Pelvis"] = np.negative(stored["Pelvis"])  # pelvis reference turned 180 deg (UM21-P01)
    for s, lat in (("R", 0.1), ("L", -0.1)):
        for name, a in stored.items():
            g.create_dataset(f"jointAngles/{s}{name}Angles",
                             data=np.vstack([np.degrees(_flat(a)), np.full(n, 1.5), np.full(n, -2.5)]))
        for j in ("hip", "knee", "ankle"):
            J = j.capitalize()
            g.create_dataset(f"jointMoments/{s}{J}Moment",
                             data=np.vstack([_flat(truth[f"{j}_moment"]), np.full(n, 0.1), np.full(n, 0.2)]))
            p = -_flat(truth[f"{j}_power"])  # layout 1: component 1 = -(M x w)
            power = (np.vstack([p, 0.5 * p + 0.01, 0.25 * p + 0.02]) if layout == 1 else
                     np.vstack([np.zeros(n), np.zeros(n), -p]))  # layout 2: component 3 = +(M x w)
            g.create_dataset(f"jointPowers/{s}{J}Power", data=power)

        def marker(name, sag2):
            xyz = np.stack([np.full(n, lat), _flat(sag2[..., 0]), _flat(sag2[..., 1]), np.ones(n)])
            g.create_dataset(f"markers/{name}", data=xyz)
        for name, key in (("GT", "hip"), ("KNE", "knee"), ("KNEM", "knee"), ("ANK", "ankle"),
                          ("ANKM", "ankle"), ("HEE", "heel"), ("TOE", "toe")):
            marker(s + name, pts[key])
        marker(f"{s}ASI", pts["pelvis_front"])
        marker(f"{s}PSI", pts["pelvis_rear"])
        force = -np.stack([np.zeros(n), _flat(grf[..., 0]), _flat(grf[..., 1])]) * MASS_KG  # plate = -GRF (N)
        g.create_dataset(f"forceplates/{s}Force", data=np.repeat(force, 10, axis=1))
        copmm = np.stack([np.zeros(n), _flat(cop[..., 0]) * 1000.0, np.zeros(n)])
        g.create_dataset(f"forceplates/{s}CoP", data=np.repeat(copmm, 10, axis=1))
        g.create_dataset(f"events/{s}HS", data=(1.0 + N * np.arange(UNITS))[:, None])
    if "ParticipantDetails" not in f[f"Streaming/{subject}"]:
        refs = f.require_group("#refs#")
        cells = np.array([[_char(refs, f"{subject}_n", "Bodymass")],
                          [refs.create_dataset(f"{subject}_v", data=np.array([[MASS_KG]])).ref],
                          [_char(refs, f"{subject}_u", "kg")]], dtype=h5py.ref_dtype)
        f[f"Streaming/{subject}"].create_dataset("ParticipantDetails", data=cells)


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    truth, pts, joints, cop, grf, stance = synthetic_leg(n_units=UNITS, seed=41)
    path = tmp_path_factory.mktemp("um21") / "Streaming_synthetic.mat"
    with h5py.File(path, "w") as f:
        _write_recording(f, "AB02", "i0", truth, pts, cop, grf, reverse_pelvis=False)
        _write_recording(f, "AB04", "i0", truth, pts, cop, grf, reverse_pelvis=True)
        _write_recording(f, "AB05", "i0", truth, pts, cop, grf, reverse_pelvis=False, layout=2)
        # storage that contradicts the C03 layout record: AB03/i10 is layout 2 there, AB06/i0 layout 1
        _write_recording(f, "AB03", "i10", truth, pts, cop, grf, reverse_pelvis=False, layout=1)
        _write_recording(f, "AB06", "i0", truth, pts, cop, grf, reverse_pelvis=False, layout=2)
    before = sa.file_sha256(path)
    out = {}
    with h5py.File(path, "r") as handle:
        for rec in ("AB02/i0", "AB04/i0", "AB05/i0"):
            out[rec] = um21.convert_recording(handle, rec, BUILD)
    return {"truth": truth, "path": path, "before": before, "results": out}


def _leg(world, rec, leg="right"):
    return next(r for r in world["results"][rec][1] if r.leg == leg)


def _bits_equal(a, b):
    a, b = np.ascontiguousarray(a), np.ascontiguousarray(b)
    return a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes()


def _truth_units(a):
    """Synthetic truth for the 23 strides the stride rule keeps (frames a..b span stride u and one sample
    of stride u + 1; the resampled curve stays within the stated tolerances of stride u)."""
    return a[:UNITS - 1]


# ---------------------------------------------------------------- scope
class _NoAccess:
    def __getitem__(self, key):
        raise AssertionError(f"data accessed for an excluded recording: {key}")


@pytest.mark.parametrize("rec", ["AB01/d10", "AB01/d5", "AB01/i5", "AB09/i10", "AB08/i10", "AB10/i0"])
def test_excluded_recordings_are_refused_before_any_data_access(rec):
    with pytest.raises(um21.ExcludedRecordingError, match="refused"):
        um21.convert_recording(_NoAccess(), rec, BUILD)


@pytest.mark.parametrize("rec", ["ab04/i0", "AB04/i0 ", "AB04/s1", "AB4/i0", "AB04\\i0", None])
def test_malformed_recording_ids_are_refused(rec):
    with pytest.raises(ValueError):
        um21.convert_recording(_NoAccess(), rec, BUILD)


def test_exclusions_follow_the_recorded_decision(tmp_path):
    backlog = json.loads(sa.BACKLOG_PATH.read_text())
    assert um21.check_exclusion_decision(backlog)["answer"] == "A"  # the real backlog: D-UM21-T02-1 = A
    for answer in ("B", "C", None):
        changed = copy.deepcopy(backlog)
        for d in changed["decisions"]:
            if d["id"] == "D-UM21-T02-1":
                d["answer"] = answer
        with pytest.raises(ValueError, match="D-UM21-T02-1"):
            um21.check_exclusion_decision(changed)
        p = tmp_path / f"backlog_{answer}.json"
        p.write_text(json.dumps(changed))
        with pytest.raises(ValueError, match="D-UM21-T02-1"):  # refused before any data access
            um21.convert_recording(_NoAccess(), "AB02/i0", BUILD, backlog_path=p)
    # the six exclusions are exactly the recordings that fail the committed UM21-T02 clock census
    census = json.loads((pilot.ROOT / pilot.CENSUS).read_text())
    assert {m["record"] for m in census["misaligned"]} == set(um21.EXCLUDED)


def test_undeclared_build_is_refused(world):
    with h5py.File(world["path"], "r") as handle:
        with pytest.raises(sa.UnboundBuildError):
            um21.convert_recording(handle, "AB02/i0", "0" * 64)


# ---------------------------------------------------------------- hook inputs
def test_hook_receives_untransformed_source_channels_only(world):
    truth = world["truth"]
    for rec in ("AB02/i0", "AB04/i0"):
        for res in world["results"][rec][1]:
            log = res.application.log
            assert set(log["channels"]) == HOOK_INPUTS, rec  # no segment angle, no velocity (F2)
            assert log["dataset"] == "UM21" and log["recording"] == rec and log["mode"] == "pilot"
            assert log["detector"]["sha256"] == BUILD and log["bound_build"] == sa.bound_build()
            assert res.adapter_log["power_slots"] == {"hip": 1, "knee": 1, "ankle": 1}
            assert len(res.unit_ids) == UNITS - 1 and res.unit_ids[0].endswith(f":{res.leg}:frames:1:151")
            stored = sa.undo_sign_application(res.application.channels, log)  # the arrays the hook received
            assert all(stored[k].dtype == np.float64 for k in stored)
            # source convention, radians: pelvis clinical (-rule B), or +rule B where it was stored reversed
            want = (1 if rec == "AB04/i0" else -1) * _truth_units(truth["pelvis_tilt"])
            assert np.mean(np.abs(stored["pelvis_tilt"] - want)) < 0.01, rec
            assert np.mean(np.abs(stored["hip_power"] + _truth_units(truth["hip_power"]))) < \
                0.1 * np.mean(np.abs(truth["hip_power"]))  # stored -(M x w), not converted


def test_segment_or_velocity_inputs_are_refused():
    leg = um21.LegInputs(side="R", leg="right", pairs=[], unit_ids=["u"], channels={}, source_columns={},
                         evidence={}, unit_durations_s=np.ones(1), power_slots={}, facts={})
    for bad in ("thigh_angle", "foot_angle", "pelvis_tilt_velocity", "hip_angle_velocity"):
        leg.channels = {bad: np.zeros((1, 150))}
        with pytest.raises(ValueError, match="F2"):
            um21.apply_leg(leg, "AB02/i0", BUILD)


# ---------------------------------------------------------------- AB04/i0 correction
def test_ab04_i0_correction_flows_through_and_is_logged(world):
    truth = world["truth"]
    for leg in ("right", "left"):
        ab04, ab02 = _leg(world, "AB04/i0", leg), _leg(world, "AB02/i0", leg)
        c4, c2 = ab04.application.log["channels"]["pelvis_tilt"], ab02.application.log["channels"]["pelvis_tilt"]
        # net multiplier on the stored tilt: correction -1 x dataset sign -1 = +1; the normal recording: -1
        assert c4["publication"] == "publish" and c4["multiplier"] == 1 and c4["sign_vs_corrected_source"] == -1
        assert c2["publication"] == "publish" and c2["multiplier"] == -1 and c2["source_correction"] is None
        assert c4["source_correction"]["applied"] and c4["source_correction"]["id"] == "UM21-P01-AB04-i0-pelvis"
        assert ab04.application.log["corrections_applied"] == [{
            "id": "UM21-P01-AB04-i0-pelvis", "channel": "pelvis_tilt", "factor": -1,
            "decision": {"id": "D-UM21-P01-1", "answer": "C"}, "audit_tasks": ["UM21-P01", "UM21-P02"],
            "net_multiplier": 1}]
        assert ab02.application.log["corrections_applied"] == []
        assert any(i["kind"] == "correction" for i in ab04.application.review)
        # the published rule-B tilt is the same array as the normally stored recording's, and near the truth
        assert _bits_equal(ab04.published["pelvis_tilt"], ab02.published["pelvis_tilt"])
        assert np.mean(np.abs(ab04.published["pelvis_tilt"] - _truth_units(truth["pelvis_tilt"]))) < 0.01
        assert ab04.segment_log["from_corrected_channels"] == [{"id": "UM21-P01-AB04-i0-pelvis",
                                                                 "channel": "pelvis_tilt"}]
        assert not pilot.check_group(ab04)["correction"] and not pilot.check_group(ab02)["correction"]


# ---------------------------------------------------------------- segments and velocities after the hook
def test_segments_and_velocities_are_derived_after_the_hook_from_published_channels(world):
    truth = world["truth"]
    for rec in ("AB02/i0", "AB04/i0"):
        for res in world["results"][rec][1]:
            ch = res.application.log["channels"]
            assert set(res.segments) == set(sa.SEGMENT_CHANNELS), rec
            for seg, d in res.segment_log["derived"].items():  # hash-linked to the hook's outputs
                for name, h in d["inputs_sha256"].items():
                    assert h == (ch[name]["output_sha256"] if name in ch else
                                 res.segment_log["derived"][name]["output_sha256"]), (rec, seg, name)
            # rule-B chain of the published channels, bit for bit
            p = res.published
            assert _bits_equal(res.segments["thigh_angle"], p["pelvis_tilt"] + p["hip_angle"])
            assert _bits_equal(res.segments["shank_angle"], res.segments["thigh_angle"] - p["knee_angle"])
            assert _bits_equal(res.segments["foot_angle"], res.segments["shank_angle"] + p["ankle_angle"])
            for seg in sa.SEGMENT_CHANNELS:  # and close to the independently built synthetic segment truth
                assert np.mean(np.abs(res.segments[seg] - _truth_units(truth[seg]))) < 0.02, (rec, seg)
            assert set(res.velocities) == {f"{k}_velocity" for k in ("pelvis_tilt",) + sa.SEGMENT_CHANNELS}
            for vel, d in res.velocity_log["derived"].items():
                src = p.get(d["from"], res.segments.get(d["from"]))
                assert d["input_sha256"] == sa.array_sha256(src), vel
            # spacing = stride duration / 149: (151 - 1) frames / 100 Hz / 149, hand-written central difference
            h = 1.5 / 149
            a = res.segments["thigh_angle"]
            assert np.allclose(res.velocities["thigh_angle_velocity"][:, 1:-1], (a[:, 2:] - a[:, :-2]) / (2 * h),
                               rtol=1e-12, atol=1e-12)
            assert np.isclose(res.velocities["thigh_angle_velocity"][0, 0], (a[0, 1] - a[0, 0]) / h)
            f = pilot.check_group(res)
            assert not f["segment_not_from_published"] and not f["velocity_not_from_published"], rec


def test_reversed_pelvis_reaches_segments_and_velocities_only_through_the_correction(world):
    for leg in ("right", "left"):
        ab04, ab02 = _leg(world, "AB04/i0", leg), _leg(world, "AB02/i0", leg)
        for k in list(sa.SEGMENT_CHANNELS):
            assert _bits_equal(ab04.segments[k], ab02.segments[k]), k
        for k in ab02.velocities:
            assert _bits_equal(ab04.velocities[k], ab02.velocities[k]), k
        # contrast: the reconvert_umich_streaming.py lines 91-92 recipe (thigh = pelvis + hip on the stored,
        # source-convention pelvis) is off by twice the tilt for a normally stored recording, and gives two
        # different thighs for the same motion depending on how the pelvis was stored
        stored2 = sa.undo_sign_application(ab02.application.channels, ab02.application.log)
        recipe2 = stored2["pelvis_tilt"] + stored2["hip_angle"]
        assert np.allclose(recipe2 - ab02.segments["thigh_angle"], -2 * ab02.published["pelvis_tilt"], atol=1e-12)
        stored4 = sa.undo_sign_application(ab04.application.channels, ab04.application.log)
        recipe4 = stored4["pelvis_tilt"] + stored4["hip_angle"]
        assert np.mean(np.abs(recipe4 - recipe2)) > 0.25  # tilt is about -0.17 rad: 2 x tilt apart


# ---------------------------------------------------------------- nothing else changes
def test_nothing_else_changes(world):
    assert sa.file_sha256(world["path"]) == world["before"]  # the source file is untouched
    for rec in ("AB02/i0", "AB04/i0"):
        for res in world["results"][rec][1]:
            log = res.application.log
            stored = sa.undo_sign_application(res.application.channels, log)
            for k, c in log["channels"].items():
                out = res.application.channels[k]
                expect = np.negative(stored[k]) if c["multiplier"] == -1 else stored[k]
                assert _bits_equal(out, expect), (rec, k)  # output = multiplier x input, exactly
                assert c["input_sha256"] == res.adapter_log["inputs_sha256"][k]
                assert c["offset"]["applied"] is False
            published = {k for k, c in log["channels"].items() if c["publication"] == "publish"}
            assert set(res.published) == published  # held channels are never returned as published
            assert all(_bits_equal(res.published[k], res.application.channels[k]) for k in published)
            assert set(res.adapter_log["published"]) | set(res.adapter_log["held"]) == HOOK_INPUTS
            f = pilot.check_group(res)
            assert not f["wrong_published_sign"] and not f["unexplained_hold"] and not f["forbidden_hook_input"]


def test_check_group_flags_a_wrong_published_sign(world):
    res = copy.copy(_leg(world, "AB02/i0"))
    app = copy.deepcopy(res.application)
    app.log["channels"]["hip_angle"].update(publication="publish", sign_vs_corrected_source=-1)
    res.application = app
    assert pilot.check_group(res)["wrong_published_sign"] == ["hip_angle: published -1, truth +1"]
    assert pilot.expected_sign("ankle_power", {"ankle": 3}) == 1 and pilot.expected_sign("hip_power", {"hip": 1}) == -1


# ---------------------------------------------------------------- power layout (R2)
def test_layout_2_recording_uses_slot_3_and_publishes_plus_one(world):
    c03 = json.loads((pilot.ROOT / pilot.C03).read_text())
    assert "AB05/i0" in c03["kinetic_layout"]["power_layout_2_recordings"]  # the record, not the adapter, says so
    for res in world["results"]["AB05/i0"][1]:
        assert res.adapter_log["power_slots"] == {"hip": 3, "knee": 3, "ankle": 3}
        assert res.adapter_log["power_layout"]["layout"] == 2 and res.adapter_log["power_layout"]["expected_slot"] == 3
        c = res.application.log["channels"]["ankle_power"]
        assert c["publication"] == "publish" and c["multiplier"] == 1  # stored +(M x w): published as is
        f = pilot.check_group(res)
        assert not any(v for k, v in f.items() if k != "not_checked"), f
    assert _leg(world, "AB02/i0").adapter_log["power_layout"]["layout"] == 1


@pytest.mark.parametrize("rec, found", [("AB03/i10", 1), ("AB06/i0", 3)])
def test_power_slot_disagreeing_with_the_c03_layout_fails_the_recording(world, rec, found):
    with h5py.File(world["path"], "r") as handle:
        with pytest.raises(um21.PowerSlotError, match=f"first filled slot {found}"):
            um21.convert_recording(handle, rec, BUILD)


def _logs_and_slots(world, recs):
    results = [r for rec in recs for r in world["results"][rec][1]]
    logs = [copy.deepcopy({k: r.application.log[k] for k in pilot.LOG_KEYS}) for r in results]
    return logs, {r.group_id: r.adapter_log["power_slots"] for r in results}


def test_cross_group_power_item_is_explained_by_the_slots(world):
    logs, slots = _logs_and_slots(world, ("AB02/i0", "AB04/i0", "AB05/i0"))
    items = pilot.explain_cross_group(sa.cross_group_review(logs), logs, slots)
    ankle = next(i for i in items if i["channel"] == "ankle_power")
    assert ankle["explained"] and "power slots differ ([1, 3])" in ankle["explanations"][0]
    assert ankle["published_signs"]["AB05/i0:right right"] == 1 and ankle["published_signs"]["AB02/i0:right right"] == -1
    # contrast: the same sign difference on a layout-1-only set (slots forged equal) is unexplained
    forged = {g: {**s, "ankle": 1} for g, s in slots.items()}
    bad = pilot.explain_cross_group(sa.cross_group_review(logs), logs, forged)
    assert not next(i for i in bad if i["channel"] == "ankle_power")["explained"]


def _held_in_left(world, channel, **detector):
    """AB02/i0: `channel` published in the right leg; the left leg's log edited to hold it with the given
    detector verdict and sign (crafted logs, as a disagreeing recording would produce)."""
    logs, slots = _logs_and_slots(world, ("AB02/i0",))
    left = next(lg for lg in logs if lg["leg"] == "left")
    left["channels"][channel].update(publication="hold", multiplier=1, sign_vs_corrected_source=1,
                                     hold_reason="any text", **detector)
    items = pilot.explain_cross_group(sa.cross_group_review(logs), logs, slots)
    return next(i for i in items if i["channel"] == channel), left, logs, slots


@pytest.mark.parametrize("detector", [
    {"verdict": "suggest", "detector_sign": -1},   # suggests the opposite of the audited +1
    {"verdict": "apply", "detector_sign": -1},     # applies the opposite
    {"verdict": "conflict", "detector_sign": None},
    {"verdict": "conflict", "detector_sign": 1},   # a conflict is a disagreement even with the right sign
])
def test_a_held_detector_disagreement_stays_unexplained(world, detector):
    item, *_ = _held_in_left(world, "knee_angle", **detector)
    assert not item["explained"] and any("held in AB02/i0:left left" in u for u in item["unexplained"]), item


@pytest.mark.parametrize("detector", [{"verdict": "abstain", "detector_sign": None},
                                      {"verdict": "suggest", "detector_sign": 1}])
def test_a_benign_hold_is_explained_from_structured_fields(world, detector):
    item, *_ = _held_in_left(world, "knee_angle", **detector)
    assert item["explained"] and item["unexplained"] == [], item


def test_power_hold_is_judged_against_its_slot_and_exceptions_explain_holds(world):
    item, *_ = _held_in_left(world, "ankle_power", verdict="suggest", detector_sign=-1)  # slot 1 truth is -1
    assert item["explained"]
    item, *_ = _held_in_left(world, "ankle_power", verdict="suggest", detector_sign=1)
    assert not item["explained"]
    # a hold that comes from a per-recording exception is explained even when the detector opposes the truth
    _, left, logs, slots = _held_in_left(world, "knee_angle", verdict="apply", detector_sign=-1)
    left["exceptions_applied"] = [{"id": "SYNTH-hold", "action": "hold", "channel": "knee_angle"}]
    item = next(i for i in pilot.explain_cross_group(sa.cross_group_review(logs), logs, slots)
                if i["channel"] == "knee_angle")
    assert item["explained"] and "per-recording exception" in item["explanations"][0]


# ---------------------------------------------------------------- pilot record writer
def _git(repo, *args):
    import subprocess
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=synthetic", "-c", "user.email=synthetic@example.invalid",
                    "-c", "commit.gpgsign=false", *args], check=True, capture_output=True)


def _record_world(tmp_path, receipt_edit=None, summary_edit=None):
    repo = tmp_path / "repo"
    (repo / "docs/quality/audits").mkdir(parents=True)
    bindings = {**sa.bound_build(), pilot.ADAPTER: "a" * 64, pilot.RUNNER: "b" * 64}
    spec_file = repo / pilot.SPEC  # the reviewed spec the launcher was given
    spec_file.write_text(json.dumps({"job_id": pilot.JOB_ID, "bindings": bindings}, indent=1))
    summary = {"automated_outcome": "passed", "bound_build": sa.bound_build(), "recordings": ["AB04/i0"]}
    if summary_edit:
        summary_edit(summary)
    spath = tmp_path / "pilot_summary.json"
    spath.write_text(json.dumps(summary))
    match = {k: {"expected": v, "actual": v, "matches": True} for k, v in bindings.items()}
    receipt = {"status": "completed", "clean_success": True, "spec_sha256": sa.file_sha256(spec_file),
               "spec": {"job_id": pilot.JOB_ID, "cwd": str(repo), "bindings": dict(bindings)},
               "bindings_before": copy.deepcopy(match), "bindings_after": copy.deepcopy(match),
               "outputs": [{"path": "pilot_summary.json", "sha256": sa.file_sha256(spath)}]}
    if receipt_edit:
        receipt_edit(receipt)
    rpath = repo / "docs/quality/audits/receipt.json"
    rpath.write_text(json.dumps(receipt))
    return repo, rpath, spath


def _gate(repo, rpath, rec_path, cite=True):
    _git(repo, "init", "-q")
    _git(repo, "add", str(rpath.relative_to(repo)), str(rec_path.relative_to(repo)))
    _git(repo, "commit", "-q", "-m", "synthetic pilot")
    text = (f"Pilot record {rec_path.relative_to(repo)} sha256 {sa.file_sha256(rec_path)}; receipt sha256 "
            f"{sa.file_sha256(rpath)}") if cite else ""
    records = {pilot.TASK_ID: {"status": "done", "dataset": "um21", "handoff": {"checks": [text]}}}
    return sa.check_pilot_record(rec_path, "UM21", sa.bound_build(), lambda t: (True, ""), records, repo)


def test_record_writer_output_passes_the_full_run_gate(tmp_path):
    repo, rpath, spath = _record_world(tmp_path)
    out = repo / "docs/quality/audits/record.json"
    record, digest = pilot.write_record(rpath, spath, out, repo_root=repo)
    assert record["outcome"] == "passed" and record["problems"] == [] and digest == sa.file_sha256(out)
    rec, facts = _gate(repo, rpath, out)
    assert rec["pilot_task"] == "CORE-11-P-UM21" and facts["receipt_sha256"] == sa.file_sha256(rpath)
    with pytest.raises(FileExistsError):
        pilot.write_record(rpath, spath, out, repo_root=repo)  # never overwritten


@pytest.mark.parametrize("why, kw", [
    ("unclean receipt", dict(receipt_edit=lambda r: r.update(clean_success=False))),
    ("other job", dict(receipt_edit=lambda r: r["spec"].update(job_id="CORE-11-P-UM21-pilot-v1"))),
    ("binding changed", dict(receipt_edit=lambda r: r["bindings_after"][pilot.ADAPTER].update(matches=False))),
    ("summary not hashed", dict(receipt_edit=lambda r: r.update(outputs=[]))),
    ("automated failure", dict(summary_edit=lambda s: s.update(automated_outcome="failed"))),
    ("stale build", dict(summary_edit=lambda s: s["bound_build"].update({"contributor_tools/common/audited_signs.json": "c" * 64}))),
    ("other spec", dict(receipt_edit=lambda r: r.update(spec_sha256="d" * 64))),
    ("adapter binding dropped", dict(receipt_edit=lambda r: [r[k].pop(pilot.ADAPTER)
                                                           for k in ("bindings_before", "bindings_after")]
                                     + [r["spec"]["bindings"].pop(pilot.ADAPTER)])),
])
def test_record_writer_fails_bad_runs_and_the_gate_refuses_them(tmp_path, why, kw):
    repo, rpath, spath = _record_world(tmp_path, **kw)
    out = repo / "docs/quality/audits/record.json"
    record, _ = pilot.write_record(rpath, spath, out, repo_root=repo)
    assert record["outcome"] == "failed" and record["problems"], why
    with pytest.raises(sa.PilotGateError):
        _gate(repo, rpath, out)


# ---------------------------------------------------------------- the job's import chain
def test_job_import_chain_runs_no_package_init():
    import subprocess
    import sys
    code = ("import importlib.util, sys; s = importlib.util.spec_from_file_location('runner', sys.argv[1]); "
            "m = importlib.util.module_from_spec(s); s.loader.exec_module(m); "
            "print(sorted(k for k in sys.modules if k in m.PACKAGE_INITS or k == 'pandas'))")
    out = subprocess.run([sys.executable, "-P", "-c", code, str(pilot.ROOT / pilot.RUNNER)],
                         capture_output=True, text=True, check=True, cwd="/")
    assert out.stdout.strip() == "[]", out.stdout + out.stderr


# ---------------------------------------------------------------- plan-only pilot spec
def test_pilot_spec_is_seeded_includes_ab04_i0_and_a_layout_2_recording_and_validates(tmp_path):
    spec = pilot.build_spec()
    s = validate_spec(spec)  # in-process; nothing launched
    rec = spec["command"][spec["command"].index("--recordings") + 1].split(",")
    census = json.loads((pilot.ROOT / pilot.CENSUS).read_text())
    c03 = json.loads((pilot.ROOT / pilot.C03).read_text())
    layout2 = sorted(set(c03["kinetic_layout"]["power_layout_2_recordings"]) - set(um21.EXCLUDED) - {"AB04/i0"})
    rng = random.Random(pilot.SEED)
    pick = rng.choice(layout2)
    pool = [r for r in pilot.in_scope_recordings(census) if r not in ("AB04/i0", pick)]
    assert rec == ["AB04/i0", pick] + rng.sample(pool, pilot.N_RANDOM)
    assert rec[1] in c03["kinetic_layout"]["power_layout_2_recordings"]
    assert len(pool) == 42 and not set(rec) & set(um21.EXCLUDED) and len(set(rec)) == len(rec)
    assert spec["job_id"] == "CORE-11-P-UM21-pilot-v3"
    assert spec["command"][spec["command"].index("--detector-sha256") + 1] == BUILD
    b = spec["bindings"]
    assert all(b[k] == v for k, v in sa.bound_build().items())  # the full-run gate needs the bound build
    assert b[pilot.ADAPTER] == sa.file_sha256(pilot.ROOT / pilot.ADAPTER)
    assert b[pilot.RUNNER] == sa.file_sha256(pilot.ROOT / pilot.RUNNER)
    assert b[pilot.SOURCE] == json.loads((pilot.ROOT / pilot.C03).read_text())["source"]["sha256_recorded"]
    assert s["cwd"] == str(pilot.ROOT) and s["address_space_mib"] <= 768
    assert s["output_root"].endswith("converted_datasets/reconversion_v2/core11_p_um21_pilot_v3")
    assert s["receipt_path"].endswith("docs/quality/audits/core11-p-um21-launcher-receipt-v3.json")
    # Launched specs: v3r1 (planned spec with another receipt_path, after the v3 launch was refused; run on the
    # bound build of its time) and v4 (re-pilot after HIST-06 changed audited_signs.json: the planned spec on the
    # current bound build with a new output root and receipt path). Each must keep the planned seed, sample,
    # command, limits and job id. A launched spec's output root may exist only as the output of a clean run of
    # exactly that spec. The current spec (v4) must bind the current build; v3r1 is history.
    def launched(name, receipt_name, output_root, current):
        path = pilot.ROOT / f"docs/quality/audits/{name}"
        if not path.exists():
            return
        ls = json.loads(path.read_text())
        validate_spec(ls)
        cmd = list(ls["command"])
        assert cmd[cmd.index("--output-root") + 1] == output_root
        cmd[cmd.index("--output-root") + 1] = spec["output_root"]
        same = {**ls, "command": cmd, "output_root": spec["output_root"], "receipt_path": spec["receipt_path"]}
        if current:
            assert same == spec  # current bound build, adapter and runner
        else:
            assert {k: v for k, v in same.items() if k != "bindings"} == {k: v for k, v in spec.items() if k != "bindings"}
            assert set(ls["bindings"]) == set(spec["bindings"])
        assert ls["output_root"] == output_root and ls["receipt_path"] == f"docs/quality/audits/{receipt_name}"
        if (pilot.ROOT / output_root).exists():  # written only by the launched job
            receipt = json.loads((pilot.ROOT / ls["receipt_path"]).read_text())
            assert receipt["status"] == "completed" and receipt["clean_success"] is True
            assert receipt["spec_sha256"] == sa.file_sha256(path)
            assert receipt["spec"]["bindings"] == ls["bindings"]
            assert Path(receipt["spec"]["output_root"]) == pilot.ROOT / output_root
            assert any(o["path"] == "pilot_summary.json" for o in receipt["outputs"])
    launched("core11-p-um21-pilot-spec-v3r1.json", "core11-p-um21-launcher-receipt-v3r1.json",
             "converted_datasets/reconversion_v2/core11_p_um21_pilot_v3", current=False)
    launched("core11-p-um21-pilot-spec-v4.json", "core11-p-um21-launcher-receipt-v4.json",
             "converted_datasets/reconversion_v2/core11_p_um21_pilot_v4", current=True)
    assert (pilot.ROOT / "docs/quality/audits/core11-p-um21-pilot-spec-v4.json").exists()
    assert set(pilot.SUPERSEDED) == {"docs/quality/audits/core11-p-um21-pilot-spec.json",
                                     "docs/quality/audits/core11-p-um21-pilot-spec-v2.json"}
    for old in pilot.SUPERSEDED:  # the never-launched v1 and v2 specs are gone and their paths are not reused
        assert not (pilot.ROOT / old).exists() and old != pilot.SPEC
    with pytest.raises(SpecError):
        validate_spec({**spec, "address_space_mib": 4096})
    out = tmp_path / "spec.json"
    pilot.plan(out)
    assert json.loads(out.read_text()) == spec
    with pytest.raises(FileExistsError):
        pilot.plan(out)  # a spec is never overwritten


def test_run_step_refuses_outside_the_guarded_launcher(tmp_path):
    with pytest.raises(SystemExit, match="guarded_launcher"):
        pilot.main(["run", "--output-root", str(tmp_path / "x"), "--detector-sha256", BUILD,
                    "--recordings", "AB04/i0", "--seed", str(pilot.SEED)])
    assert not (tmp_path / "x").exists()


def test_written_spec_is_the_seeded_plan_when_present():
    """The written plan-only spec validates and runs the seeded sample. Binding drift after an edit of a bound
    file is not tested here: the launcher refuses it (binding_mismatch) and the spec must be re-planned."""
    path = pilot.ROOT / pilot.SPEC
    if not path.exists():
        pytest.skip("plan-only spec not written yet")
    spec = json.loads(path.read_text())
    validate_spec(spec)
    census = json.loads((pilot.ROOT / pilot.CENSUS).read_text())
    rec = spec["command"][spec["command"].index("--recordings") + 1].split(",")
    assert rec == pilot.pilot_sample(census) and rec[0] == "AB04/i0"
    assert set(sa.bound_build()) <= set(spec["bindings"]) and pilot.ADAPTER in spec["bindings"]
    assert rec[1] in um21.power_layout()["layout_2"]
    assert {k: spec[k] for k in ("output_root", "receipt_path", "job_id")} == \
        {k: pilot.build_spec()[k] for k in ("output_root", "receipt_path", "job_id")}


def test_record_writer_requires_the_reviewed_spec(tmp_path):
    """R4: a receipt whose spec dropped the adapter binding (before and after too) is not the reviewed spec."""
    def drop(r):
        for k in ("bindings_before", "bindings_after"):
            r[k].pop(pilot.ADAPTER)
        r["spec"]["bindings"].pop(pilot.ADAPTER)
    repo, rpath, spath = _record_world(tmp_path, receipt_edit=drop)
    rec = pilot.build_record(rpath, spath, repo_root=repo)
    assert rec["outcome"] == "failed"
    assert rec["problems"] == ["receipt spec bindings differ from the reviewed spec file's bindings"]
    (tmp_path / "b").mkdir()
    repo, rpath, spath = _record_world(tmp_path / "b", receipt_edit=lambda r: r.update(spec_sha256="d" * 64))
    rec = pilot.build_record(rpath, spath, repo_root=repo)
    assert rec["problems"] == ["receipt spec_sha256 is not the reviewed spec file's sha256"]
