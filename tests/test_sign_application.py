"""CORE-11 converter hook for the sign detector, on SYNTHETIC fixtures only.

Every array here is synthetic: the gait-like leg from tests/test_sign_offset_detector.py, built in
the rule-B convention and then given KNOWN source conventions (knee flexion negative, knee extensor
moment positive, pelvis anterior tilt positive, power stored as -(M x w)), a known 5 deg ankle
offset and two 180 deg branch episodes. Backlogs, pilot records, launcher receipts and git
repositories are synthetic files under pytest's tmp_path. No research dataset is read. Expected
multipliers come from the injected conventions, not from the hook.
"""
import copy
import json
import re
import subprocess

import numpy as np
import pytest

from contributor_tools.common import sign_application as sa
from tests.test_sign_offset_detector import DT, DUR, injected_source, synthetic_leg

BUILD = sa.file_sha256(sa.DETECTOR_PATH)
# target = sign x source for the injected synthetic source (independently known).
INJECTED_TRUTH = {"pelvis_tilt": -1, "hip_angle": 1, "knee_angle": -1, "ankle_angle": 1, "hip_moment": 1,
                  "knee_moment": -1, "ankle_moment": 1, "hip_power": -1, "knee_power": -1, "ankle_power": -1}
UNITS = [f"SYNTH/rec1/stride{u:02d}" for u in range(24)]


def _fixture(seed=41):
    truth, pts, joints, cop, grf, stance = synthetic_leg(seed=seed)
    src = injected_source(truth)
    src["knee_moment"][2, 10:14] = np.nan  # missing samples must round-trip bit for bit
    evidence = dict(marker_points=pts, cop=cop, grf=grf, task="level_walking", grf_unit="N_per_kg",
                    unit_durations_s=DUR, dt=DT, cop_registration="synthetic: CoP and markers share one frame")
    return src, evidence


@pytest.fixture(scope="module", autouse=True)
def _synthetic_default_table(tmp_path_factory):
    """Every run names a dataset key that must be in the audited-sign table; synthetic runs use a synthetic
    table with an empty SYNTH dataset unless a test passes its own."""
    global SYNTH_TABLE
    SYNTH_TABLE = tmp_path_factory.mktemp("table") / "audited.json"
    SYNTH_TABLE.write_text(json.dumps({"datasets": {"SYNTH": {"recording_id_pattern": "rec[0-9]+",
                                                              "entries": [], "exceptions": []}}}))
    yield


def _run(src, evidence, **kw):
    kw.setdefault("detector_sha256", BUILD)
    kw.setdefault("audited_path", SYNTH_TABLE)
    return sa.run_sign_application(dataset=kw.pop("dataset", "SYNTH"), leg="right", group_id="rec1",
                                   recording=kw.pop("recording", "rec1"), unit_ids=UNITS, channels=src, evidence=evidence,
                                   source_columns={k: f"src_{k}" for k in src}, **kw)


def _backlog(tmp_path, tasks, name="backlog.json"):
    """tasks: id -> status, or id -> full synthetic record (dict)."""
    path = tmp_path / name
    path.write_text(json.dumps({"tasks": [{"id": t, **(s if isinstance(s, dict) else {"status": s})}
                                          for t, s in tasks.items()]}))
    return path


@pytest.fixture(scope="module")
def result():
    src, evidence = _fixture()
    before = {k: sa.array_sha256(v) for k, v in src.items()}
    ev_before = {k: sa.array_sha256(v) for k, v in evidence["marker_points"].items()}
    res = _run(src, evidence)
    return src, evidence, before, ev_before, res


def _bits_equal(a, b):
    a, b = np.ascontiguousarray(a), np.ascontiguousarray(b)
    return a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes()


# ---------------------------------------------------------------- detector-only behaviour (no audits)
def test_applies_only_two_family_verdicts_with_the_known_sign(result):
    src, _, _, _, res = result
    applied = {k: c["multiplier"] for k, c in res.log["channels"].items() if c["detector_applied"]}
    assert applied
    for k, c in res.log["channels"].items():
        if c["detector_applied"]:
            assert c["verdict"] == "apply" and len(set(c["families"])) >= 2, k
            assert c["multiplier"] == INJECTED_TRUTH[k] and c["sign_basis"] == "detector", k
            agreeing = {v["family"] for v in c["votes"]
                        if v["sign"] == c["multiplier"] and v["strength"] in ("moderate", "strong")}
            assert len(agreeing - {None}) >= 2, k
            assert _bits_equal(res.channels[k], -src[k] if c["multiplier"] == -1 else src[k])
        else:  # no audit given: the detector alone decides, so everything else is held unchanged
            assert c["multiplier"] == 1 and c["publication"] == "hold"
    assert applied.get("knee_angle") == -1
    assert res.log["counts"]["detector_applied"] == len(applied) == res.log["counts"]["published"]


def test_suggestions_conflicts_and_abstentions_are_untouched_and_listed(result):
    src, _, _, _, res = result
    review_channels = {(i["kind"], i["channel"]) for i in res.review}
    for k, c in res.log["channels"].items():
        if c["verdict"] != "apply":
            assert not c["detector_applied"] and _bits_equal(res.channels[k], src[k]), k
            assert (c["verdict"], k) in review_channels and ("hold", k) in review_channels, k
    assert res.log["channels"]["pelvis_tilt"]["verdict"] == "suggest"


def test_unrefuted_documentation_conflict_blocks_and_leaves_data_untouched():
    src, evidence = _fixture(seed=43)
    doc = [("knee_angle", 1, "synthetic README line 3: knee flexion positive", "synth-readme:L3")]
    res = _run(src, evidence, documentation=doc)
    c = res.log["channels"]["knee_angle"]
    assert c["verdict"] == "conflict" and not c["detector_applied"] and c["publication"] == "hold"
    assert _bits_equal(res.channels["knee_angle"], src["knee_angle"])
    assert res.log["documentation"][0]["action"] == "kept"


def test_offsets_are_never_applied(result):
    src, _, _, _, res = result
    c = res.log["channels"]["ankle_angle"]
    assert c["offset"]["applied"] is False and c["offset"]["flag_for_review"]
    assert abs(c["offset"]["estimate"] - np.deg2rad(5.0)) < np.deg2rad(1.5)  # the injected offset
    assert _bits_equal(res.channels["ankle_angle"], src["ankle_angle"] if c["multiplier"] == 1 else -src["ankle_angle"])
    offsets = [i for i in res.review if i["kind"] == "offset"]
    assert offsets and all(i["applied"] is False for i in offsets)


def test_inputs_and_evidence_are_not_modified_and_evidence_is_hashed(result):
    src, evidence, before, ev_before, res = result
    assert {k: sa.array_sha256(v) for k, v in src.items()} == before
    assert {k: sa.array_sha256(v) for k, v in evidence["marker_points"].items()} == ev_before
    assert all(res.channels[k] is not src[k] for k in src)
    assert res.log["evidence_sha256"]["marker_points.heel"] == ev_before["heel"]
    assert res.log["evidence_sha256"]["cop"] == sa.array_sha256(evidence["cop"])


def test_evidence_changed_during_detection_is_refused(monkeypatch):
    src, evidence = _fixture()
    det = sa.load_bound_detector(BUILD)
    original = det.detect_leg

    def mutating(*a, **kw):
        kw["cop"][0, 0, 0] += 1.0  # a detector that edits its evidence in place
        return original(*a, **kw)
    monkeypatch.setattr(det, "detect_leg", mutating)
    with pytest.raises(RuntimeError, match="evidence"):
        _run(src, evidence)


# ---------------------------------------------------------------- input types
@pytest.mark.parametrize("make", [
    lambda a: np.ma.masked_array(a, mask=np.zeros(a.shape, bool)),
    lambda a: a.astype(np.float32),
    lambda a: a.astype(">f8"),
    lambda a: a.astype(int),
    lambda a: np.asmatrix(a),
])
def test_refuses_array_subclasses_and_non_float64(make):
    src, evidence = _fixture()
    with pytest.raises(ValueError):
        _run({"knee_angle": make(src["knee_angle"])}, evidence)


def test_masked_array_is_refused_not_silently_unmasked():
    src, evidence = _fixture()
    a = src["knee_angle"].copy()
    a[0, :10] = 9999.0
    with pytest.raises(ValueError, match="plain numpy.ndarray"):
        _run({"knee_angle": np.ma.masked_greater(a, 100.0)}, evidence)


def test_channel_shape_and_unit_identity_checks():
    src, evidence = _fixture()
    with pytest.raises(ValueError):
        sa.run_sign_application(dataset="SYNTH", leg="right", group_id="rec1", recording="rec1", unit_ids=UNITS[:-1],
                                channels=src, evidence=evidence, detector_sha256=BUILD, audited_path=SYNTH_TABLE)


# ---------------------------------------------------------------- log, undo
def test_log_round_trips_and_undo_restores_input_exactly(result, tmp_path):
    src, _, _, _, res = result
    path = tmp_path / "sign_application.json"
    digest = sa.write_json_exclusive(path, res.log)
    with pytest.raises(FileExistsError):
        sa.write_json_exclusive(path, res.log)  # never overwrites
    assert json.loads(path.read_text()) == res.log
    restored = sa.undo_sign_application(res.channels, path, expected_log_sha256=digest)
    for k in src:
        assert _bits_equal(restored[k], src[k]), k
    assert np.isnan(restored["knee_moment"][2, 10:14]).all()
    assert res.log["detector"]["sha256"] == BUILD and res.log["scientific_approval"] is False
    assert res.log["unit_ids"] == UNITS


def test_undo_refuses_arrays_that_are_not_the_logged_output(result):
    src, _, _, _, res = result
    tampered = dict(res.channels)
    tampered["knee_angle"] = res.channels["knee_angle"].copy()
    tampered["knee_angle"][0, 0] += 1e-12
    with pytest.raises(sa.UndoError):
        sa.undo_sign_application(tampered, res.log)
    with pytest.raises(sa.UndoError):
        sa.undo_sign_application(src, res.log)


def test_undo_refuses_a_consistently_edited_log_against_the_manifest_hash(result, tmp_path):
    src, _, _, _, res = result
    good = tmp_path / "good.json"
    digest = sa.write_json_exclusive(good, res.log)
    # Forge: claim the knee was never negated and make the hashes consistent with that claim.
    forged = copy.deepcopy(res.log)
    forged["channels"]["knee_angle"]["multiplier"] = 1
    forged["channels"]["knee_angle"]["input_sha256"] = sa.array_sha256(res.channels["knee_angle"])
    bad = tmp_path / "forged.json"
    sa.write_json_exclusive(bad, forged)
    sa.undo_sign_application(res.channels, bad)  # without an anchor the forgery is self-consistent
    with pytest.raises(sa.UndoError, match="manifest"):
        sa.undo_sign_application(res.channels, bad, expected_log_sha256=digest)
    with pytest.raises(sa.UndoError):
        sa.undo_sign_application(res.channels, res.log, expected_log_sha256=digest)  # dict cannot be checked


# ---------------------------------------------------------------- build binding
@pytest.mark.parametrize("declared", [None, "", "ed52fc49", BUILD.upper(), "0" * 64, BUILD + "\n"])
def test_refuses_undeclared_or_unknown_build(declared):
    src, evidence = _fixture()
    with pytest.raises(sa.UnboundBuildError):
        _run(src, evidence, detector_sha256=declared)


def test_refuses_a_modified_detector_file(tmp_path):
    copy_ = tmp_path / "sign_offset_detector.py"
    copy_.write_bytes(sa.DETECTOR_PATH.read_bytes() + b"\n# edited\n")
    src, evidence = _fixture()
    with pytest.raises(sa.UnboundBuildError):
        _run(src, evidence, detector_path=copy_)


def test_refuses_parameter_overrides_and_unpoliced_documentation():
    src, evidence = _fixture()
    for extra in ({"params": {"min_families": 1}}, {"documentation": [("knee_angle", -1, "x")]}):
        with pytest.raises(ValueError):
            _run(src, {**evidence, **extra})


def test_logged_build_hashes_are_of_what_ran_and_the_table_is_read_once(result, monkeypatch):
    _, _, _, _, res = result
    b = res.log["bound_build"]
    assert b["contributor_tools/common/sign_offset_detector.py"] == BUILD
    assert b["contributor_tools/common/sign_application.py"] == sa.HOOK_SHA256
    assert b["contributor_tools/common/documentation_policy.py"] == sa.file_sha256(sa.POLICY_PATH)
    assert b["contributor_tools/common/refuted_documentation.json"] == sa.file_sha256(sa.REFUTED_PATH)
    policy, _ = sa._load_policy()
    seen = []
    original = policy.split_documentation

    def spy(dataset, items, path, backlog_path):
        seen.append(path)
        return original(dataset, items, path=path, backlog_path=backlog_path)
    monkeypatch.setattr(policy, "split_documentation", spy)
    src, evidence = _fixture()
    _run(src, evidence)
    assert seen and seen[0] != sa.REFUTED_PATH  # the policy reads the hook's single copy


# ---------------------------------------------------------------- pilot gate (full mode)
def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=synthetic", "-c", "user.email=synthetic@example.invalid",
                    "-c", "commit.gpgsign=false", *args], check=True, capture_output=True)


def _pilot_world(tmp_path, *, task_status="done", task_id="CORE-11-P-SYNTH", task_dataset="synth", cite=True,
                 record_edit=None, receipt_edit=None, commit_record=True, commit_receipt=True,
                 record_dir="docs/quality/audits"):
    repo = tmp_path / "repo"
    (repo / record_dir).mkdir(parents=True)
    (repo / "receipts").mkdir()
    (repo / "README").write_text("synthetic repository\n")
    bindings = {**sa.bound_build(audited_path=SYNTH_TABLE), "contributor_tools/synthetic_adapter.py": "b" * 64}
    match = {k: {"expected": v, "actual": v, "matches": True} for k, v in bindings.items()}
    receipt = {"status": "completed", "clean_success": True, "spec": {"cwd": str(repo), "bindings": dict(bindings)},
               "bindings_before": copy.deepcopy(match), "bindings_after": copy.deepcopy(match)}
    if receipt_edit:
        receipt_edit(receipt)
    rpath = repo / "receipts" / "pilot.json"
    rpath.write_text(json.dumps(receipt))
    record = {"dataset": "SYNTH", "outcome": "passed", "pilot_task": "CORE-11-P-SYNTH",
              "launcher_receipt": {"path": "receipts/pilot.json", "sha256": sa.file_sha256(rpath)},
              "bindings": dict(bindings)}
    if record_edit:
        record_edit(record)
    path = repo / record_dir / "core11-synth-pilot.json"
    path.write_text(json.dumps(record))
    _git(repo, "init", "-q")
    _git(repo, "add", "README", *([str(path.relative_to(repo))] if commit_record else []),
         *(["receipts/pilot.json"] if commit_receipt else []))
    _git(repo, "commit", "-q", "-m", "synthetic pilot")
    citation = (f"Pilot record {path.relative_to(repo)} sha256 {sa.file_sha256(path)}; launcher receipt sha256 "
                f"{sa.file_sha256(rpath)}" if cite else "Pilot passed (no citation).")
    backlog = _backlog(tmp_path, {task_id: {"status": task_status, "dataset": task_dataset,
                                            "handoff": {"checks": [citation]}}})
    return dict(pilot_record_path=path, repo_root=repo, backlog_path=backlog), rpath, path


def test_full_run_passes_with_a_committed_verified_pilot(tmp_path):
    src, evidence = _fixture()
    world, rpath, path = _pilot_world(tmp_path)
    res = _run(src, evidence, mode="full", **world)
    assert res.log["mode"] == "full" and res.log["pilot"]["pilot_task"] == "CORE-11-P-SYNTH"
    assert res.log["pilot"]["receipt_sha256"] == sa.file_sha256(rpath)


def _set(*keys_and_value):
    *keys, value = keys_and_value

    def edit(d):
        for k in keys[:-1]:
            d = d[k]
        d[keys[-1]] = value
    return edit


FORGERIES = {
    "no record": None,
    "record not committed": dict(commit_record=False),
    "record outside the audits folder": dict(record_dir="notes"),
    "pilot task only in review": dict(task_status="review"),
    "unrelated done task, self-consistent committed receipt (verifier round 2)":
        dict(task_id="DOC-01", record_edit=_set("pilot_task", "DOC-01")),
    "pilot task of another dataset": dict(task_id="CORE-11-P-UM21", record_edit=_set("pilot_task", "CORE-11-P-UM21")),
    "pilot task backlog dataset differs": dict(task_dataset="um21"),
    "backlog record does not cite the record and receipt": dict(cite=False),
    "receipt not committed (hand-written)": dict(commit_receipt=False),
    "forged receipt hash": dict(record_edit=_set("launcher_receipt", "sha256", "0" * 64)),
    "receipt file missing": dict(record_edit=_set("launcher_receipt", "path", "receipts/missing.json")),
    "other dataset": dict(record_edit=_set("dataset", "OTHER")),
    "failed pilot": dict(record_edit=_set("outcome", "failed")),
    "stale detector binding": dict(
        record_edit=_set("bindings", "contributor_tools/common/sign_offset_detector.py", "0" * 64),
        receipt_edit=_set("spec", "bindings", "contributor_tools/common/sign_offset_detector.py", "0" * 64)),
    "stale audited-sign table binding": dict(
        record_edit=lambda r: r["bindings"].update({sa._rel(SYNTH_TABLE): "0" * 64}),
        receipt_edit=lambda r: r["spec"]["bindings"].update({sa._rel(SYNTH_TABLE): "0" * 64})),
    "receipt binds other hashes than the record": dict(receipt_edit=_set("spec", "bindings", "contributor_tools/synthetic_adapter.py", "c" * 64)),
    "receipt not a clean run": dict(receipt_edit=_set("clean_success", False)),
    "binding changed during the run": dict(receipt_edit=_set("bindings_after", "contributor_tools/synthetic_adapter.py", "matches", False)),
}


@pytest.mark.parametrize("name", list(FORGERIES))
def test_full_run_refuses_forged_or_unverified_pilots(tmp_path, name):
    src, evidence = _fixture()
    if FORGERIES[name] is None:
        with pytest.raises(sa.PilotGateError):
            _run(src, evidence, mode="full")
        return
    world, _, _ = _pilot_world(tmp_path, **FORGERIES[name])
    with pytest.raises(sa.PilotGateError):
        _run(src, evidence, mode="full", **world)


def test_full_run_refuses_a_record_edited_after_commit(tmp_path):
    src, evidence = _fixture()
    world, _, path = _pilot_world(tmp_path)
    rec = json.loads(path.read_text())
    rec["outcome"] = "passed "
    path.write_text(json.dumps(rec))
    with pytest.raises(sa.PilotGateError, match="committed"):
        _run(src, evidence, mode="full", **world)


# ---------------------------------------------------------------- documentation policy
def _policy_world(tmp_path, status):
    table = tmp_path / "refuted.json"
    table.write_text(json.dumps({"datasets": {"SYNTH": [{
        "id": "SYNTH-README-knee", "statement": "synthetic README line 3: knee flexion positive",
        "citation_ids": ["synth-readme:L3"], "channels": ["knee_angle"], "refuted_sign": 1,
        "refuted_by_task": "T-SYN"}]}}))
    return dict(refuted_path=table, backlog_path=_backlog(tmp_path, {"T-SYN": status}))


@pytest.mark.parametrize("status, withheld", [("done", True), ("review", False)])
def test_documentation_policy_is_honoured(tmp_path, status, withheld):
    src, evidence = _fixture(seed=43)
    doc = [("knee_angle", 1, "synthetic README line 3: knee flexion positive", "synth-readme:L3")]
    res = _run(src, evidence, documentation=doc, **_policy_world(tmp_path, status))
    entry = res.log["documentation"][0]
    c = res.log["channels"]["knee_angle"]
    if withheld:
        assert entry["action"] == "withheld" and entry["refuted_by_task"] == "T-SYN"
        assert not any(v["test"] == "documentation" for v in c["votes"])
        assert c["detector_applied"] and c["multiplier"] == -1
    else:
        assert entry["action"] == "kept" and "not done" in entry["reason"]
        assert c["verdict"] == "conflict" and not c["detector_applied"]
        assert _bits_equal(res.channels["knee_angle"], src["knee_angle"])


def test_documentation_alone_never_applies():
    src, _ = _fixture()
    doc = [("knee_angle", -1, "synthetic README line 3: knee flexion negative", "synth-readme:L3")]
    res = _run({"knee_angle": src["knee_angle"]}, {"task": None}, documentation=doc)
    c = res.log["channels"]["knee_angle"]
    assert not c["detector_applied"] and c["verdict"] == "abstain" and c["publication"] == "hold"
    assert _bits_equal(res.channels["knee_angle"], src["knee_angle"])


# ---------------------------------------------------------------- guard and family table
def test_hook_family_table_equals_the_detector_table():
    det = sa.load_bound_detector(BUILD)
    assert sa.FAMILY_TABLE == det.FAMILY_GROUPINGS
    assert sa.PLATE_TIMING_TESTS == frozenset(det.PLATE_TIMING_TESTS)


def test_guard_uses_its_own_family_table(monkeypatch):
    det = sa.load_bound_detector(BUILD)
    remapped = {g: dict(t) for g, t in det.FAMILY_GROUPINGS.items()}
    remapped["fine"]["hip_stance_extension"] = "joint_anatomy"  # a detector-table bug
    monkeypatch.setattr(det, "FAMILY_GROUPINGS", remapped)
    c = {"sign": 1, "families": ["joint_anatomy", "plate_timing"],
         "evidence": [_ev("hip_stance_extension", 1, "moderate"), _ev("ankle_pushoff_plantarflexion", 1, "moderate")]}
    assert not sa.guard_apply(c, 2, "fine")[0]


def _ev(test, sign, strength="strong", **stats):
    return {"test": test, "sign": sign, "strength": strength, "stats": stats}


@pytest.mark.parametrize("channel, why", [
    ({"sign": -1, "families": ["marker_geometry"], "evidence": [_ev("reference_angle:marker", -1)]}, "one family"),
    ({"sign": -1, "families": ["marker_geometry", "joint_anatomy"],
      "evidence": [_ev("reference_angle:marker", -1), _ev("knee_hinge_asymmetry", -1, "moderate"),
                   _ev("lever_arm", 1, "moderate")]}, "dissent"),
    ({"sign": -1, "families": ["marker_geometry", "joint_anatomy"],
      "evidence": [_ev("reference_angle:marker", -1), _ev("knee_hinge_asymmetry", -1, "moderate"),
                   _ev("documentation", 1, "documentation")]}, "documentation dissent"),
    ({"sign": -1, "families": ["marker_geometry", "plate_timing"],
      "evidence": [_ev("reference_angle:marker", -1, half_cycle_ambiguous=True),
                   _ev("hip_stance_extension", -1, "moderate")]}, "half-cycle merged family"),
    ({"sign": -1, "families": ["marker_geometry", "joint_anatomy"],
      "evidence": [_ev("reference_angle:marker", -1), _ev("template", -1, "weak")]}, "weak second test"),
    ({"sign": True, "families": ["marker_geometry", "joint_anatomy"],
      "evidence": [_ev("reference_angle:marker", 1), _ev("knee_hinge_asymmetry", 1, "moderate")]}, "bool sign"),
])
def test_guard_refuses_apply_verdicts_without_two_agreeing_families(channel, why):
    ok, reason = sa.guard_apply(channel, 2, "fine")
    assert not ok, (why, reason)


def test_guard_accepts_two_agreeing_families_and_refuses_min_families_one():
    c = {"sign": -1, "families": ["joint_anatomy", "marker_geometry"],
         "evidence": [_ev("reference_angle:marker", -1), _ev("knee_hinge_asymmetry", -1, "moderate")]}
    assert sa.guard_apply(c, 2, "fine")[0]
    assert not sa.guard_apply(c, 1, "fine")[0]


# ---------------------------------------------------------------- publication rule (standing preference)
@pytest.mark.parametrize("verdict, dsign, applied, audit, expected", [
    ("apply", -1, True, -1, (-1, "audit_and_detector", "publish")),
    ("suggest", -1, False, -1, (-1, "audit", "publish")),
    ("abstain", None, False, -1, (-1, "audit", "publish")),
    ("abstain", None, False, 1, (1, "audit", "publish")),
    ("apply", -1, False, -1, (-1, "audit", "publish")),      # guard refused, same sign as the audit
    ("suggest", 1, False, -1, (1, "none", "hold")),          # detector suggests the opposite
    ("conflict", None, False, -1, (1, "none", "hold")),
    ("apply", 1, True, -1, (1, "none", "hold")),             # applied opposite: never publish
    ("apply", -1, True, None, (-1, "detector", "publish")),  # no verified audit: detector alone
    ("suggest", -1, False, None, (1, "none", "hold")),
    ("abstain", None, False, None, (1, "none", "hold")),
])
def test_publication_rule(verdict, dsign, applied, audit, expected):
    assert sa.publication_rule(verdict, dsign, applied, audit)[:3] == expected


def _audit_world(tmp_path, *, status="done", signs=None, audit_task="T-AUDIT", record=None, exceptions=(),
                 decisions=()):
    """Synthetic audited-sign table and backlog (with synthetic `decisions`). By default the T-AUDIT record
    cites every entry and exception id."""
    signs = signs or INJECTED_TRUTH
    entries = [{"id": f"SYNTH-{k}", "channel": k, "sign": v, "audit_tasks": [audit_task],
                "evidence_basis": "synthetic", "citation": "synthetic"} for k, v in signs.items()]
    table = tmp_path / "audited.json"
    table.write_text(json.dumps({"datasets": {"SYNTH": {"recording_id_pattern": "rec[0-9]+", "entries": entries,
                                                         "exceptions": list(exceptions)}}}))
    record = record or {"status": status, "dataset": "synth",
                        "handoff": {"checks": ["Entries: " + ", ".join([e["id"] for e in entries]
                                                                       + [x["id"] for x in exceptions])]}}
    backlog = _backlog(tmp_path, {audit_task: record})
    if decisions:
        data = json.loads(backlog.read_text())
        backlog.write_text(json.dumps({**data, "decisions": list(decisions)}))
    return dict(audited_path=table, backlog_path=backlog)


def test_verified_audit_publishes_agreeing_and_abstaining_channels_with_the_audited_sign(tmp_path):
    src, evidence = _fixture()
    res = _run(src, evidence, **_audit_world(tmp_path))
    for k, c in res.log["channels"].items():
        assert c["audit"]["verified"], k
        dsign = c["detector_sign"]
        if c["verdict"] == "conflict" or (dsign is not None and dsign != INJECTED_TRUTH[k]):
            assert c["publication"] == "hold" and _bits_equal(res.channels[k], src[k]), k
        else:
            assert c["publication"] == "publish" and c["multiplier"] == INJECTED_TRUTH[k], k
            assert _bits_equal(res.channels[k], -src[k] if c["multiplier"] == -1 else src[k]), k
    assert res.log["channels"]["knee_power"]["verdict"] == "abstain"
    assert res.log["channels"]["knee_power"]["sign_basis"] == "audit"
    assert res.log["counts"]["basis_audit_and_detector"] == res.log["counts"]["detector_applied"]
    restored = sa.undo_sign_application(res.channels, res.log)
    assert all(_bits_equal(restored[k], src[k]) for k in src)


def test_audit_disagreeing_with_the_detector_is_held(tmp_path):
    src, evidence = _fixture()
    wrong = {**INJECTED_TRUTH, "knee_angle": 1, "pelvis_tilt": 1}  # detector applies / suggests -1
    res = _run(src, evidence, **_audit_world(tmp_path, signs=wrong))
    for k in ("knee_angle", "pelvis_tilt"):
        c = res.log["channels"][k]
        assert c["publication"] == "hold" and c["multiplier"] == 1, k
        assert _bits_equal(res.channels[k], src[k])
        assert any(i["kind"] == "hold" and i["channel"] == k for i in res.review)


def test_unverified_audit_is_not_used(tmp_path):
    src, evidence = _fixture()
    res = _run(src, evidence, **_audit_world(tmp_path, status="review"))
    for k, c in res.log["channels"].items():
        assert c["audit"]["verified"] is False
        assert c["publication"] == ("publish" if c["detector_applied"] else "hold"), k


def test_an_unrelated_done_task_cannot_publish(tmp_path):
    """Verifier round 2: an entry naming a done task that never examined it (here a GT24 task record)."""
    src, evidence = _fixture()
    unrelated = {"status": "done", "dataset": "synth",
                 "handoff": {"checks": ["knee power, knee angle and pelvis tilt: sign not checked"]}}  # mentions, no ids
    res = _run(src, evidence, **_audit_world(tmp_path, audit_task="GT24-C02", record=unrelated))
    c = res.log["channels"]["knee_power"]
    assert c["verdict"] == "abstain" and c["audit"]["verified"] is False and c["publication"] == "hold"
    assert _bits_equal(res.channels["knee_power"], src["knee_power"])
    assert all(c["publication"] == ("publish" if c["detector_applied"] else "hold")
               for c in res.log["channels"].values())


def test_entry_links_only_by_explicit_id_in_every_listed_task():
    entry = {"id": "SYNTH-knee_power", "channel": "knee_power", "audit_tasks": ["T-A", "T-B"]}
    cite = {"dataset": "synth", "summary": "Entries: SYNTH-knee_power."}
    mention = {"dataset": "synth", "summary": "knee power: sign unknown, not checked"}  # a negative mention
    assert sa.entry_linked(entry, {"T-A": cite, "T-B": cite})[0]
    assert not sa.entry_linked(entry, {"T-A": cite, "T-B": mention})[0]
    assert not sa.entry_linked(entry, {"T-A": cite})[0]  # a listed task missing from the backlog
    longer = {"dataset": "synth", "summary": "SYNTH-knee_power_2 and xSYNTH-knee_power"}
    assert not sa.entry_linked(entry, {"T-A": longer, "T-B": longer})[0]  # whole-token ids only
    with pytest.raises(ValueError):
        sa.entry_linked({"id": "x", "audit_task": "T-A"}, {})  # the old single-task field is refused


def test_entry_needs_every_listed_task_done(tmp_path):
    src, evidence = _fixture()
    world = _audit_world(tmp_path)
    table = json.loads(world["audited_path"].read_text())
    for e in table["datasets"]["SYNTH"]["entries"]:
        e["audit_tasks"] = ["T-AUDIT", "T-SECOND"]
    world["audited_path"].write_text(json.dumps(table))
    tasks = {t["id"]: t for t in json.loads(world["backlog_path"].read_text())["tasks"]}
    second = {**tasks["T-AUDIT"], "status": "review"}
    backlog = _backlog(tmp_path, {"T-AUDIT": {k: v for k, v in tasks["T-AUDIT"].items() if k != "id"},
                                  "T-SECOND": {k: v for k, v in second.items() if k != "id"}}, name="b2.json")
    res = _run(src, evidence, audited_path=world["audited_path"], backlog_path=backlog)
    c = res.log["channels"]["knee_power"]
    assert c["audit"]["verified"] is False and "not done" in c["audit"]["reason"] and c["publication"] == "hold"


@pytest.mark.parametrize("key", ["um21", "Um21", "UNKNOWN", "SYNTH"])
def test_unknown_or_miscased_dataset_key_raises(key):
    src, evidence = _fixture()
    with pytest.raises(ValueError, match="dataset key"):
        _run(src, evidence, dataset=key, recording="AB04/i0", audited_path=sa.AUDITED_PATH)


EXCEPTION = {"id": "SYNTH-rec1-knee", "recordings": ["rec1"], "channels": ["knee_angle", "pelvis_tilt"],
             "action": "hold", "audit_tasks": ["T-AUDIT"], "pending_decision": "D-SYNTH-1", "reason": "synthetic"}


def test_per_recording_exception_holds_before_any_sign(tmp_path):
    src, evidence = _fixture()
    world = _audit_world(tmp_path, exceptions=[EXCEPTION])
    res = _run(src, evidence, recording="rec1", **world)
    for k in ("knee_angle", "pelvis_tilt"):
        c = res.log["channels"][k]
        assert c["publication"] == "hold" and c["multiplier"] == 1 and "SYNTH-rec1-knee" in c["hold_reason"], k
        assert _bits_equal(res.channels[k], src[k])
    assert res.log["channels"]["knee_angle"]["detector_applied"]  # held although the detector applied it
    assert {x["channel"] for x in res.log["exceptions_applied"]} == {"knee_angle", "pelvis_tilt"}
    other = _run(src, evidence, recording="rec2", **world)
    assert other.log["channels"]["knee_angle"]["publication"] == "publish"
    assert other.log["exceptions_applied"] == []


def test_recording_id_must_match_the_dataset_pattern(tmp_path):
    src, evidence = _fixture()
    with pytest.raises(ValueError, match="recording"):
        _run(src, evidence, recording="AB04 i0", **_audit_world(tmp_path))


def test_malformed_table_entries_are_refused(tmp_path):
    src, evidence = _fixture()
    for bad in ({"knee_angle": True}, {"knee_angle": 2}):
        with pytest.raises(ValueError):
            _run(src, evidence, **_audit_world(tmp_path, signs=bad))


def test_adapters_cannot_pass_signs():
    src, evidence = _fixture()
    with pytest.raises(TypeError):
        _run(src, evidence, audited_signs={"knee_power": {"sign": -1, "audit_task": "GT24-C02"}})


# ---------------------------------------------------------------- per-recording corrections (synthetic)
CORRECTION = {"id": "SYNTH-rec4-pelvis", "recordings": ["rec4"], "action": "correct",
              "corrections": {"pelvis_tilt": -1}, "derived_channels": ["thigh_angle", "shank_angle", "foot_angle"],
              "derived_velocities": ["pelvis_tilt_velocity", "thigh_angle_velocity", "shank_angle_velocity",
                                     "foot_angle_velocity"],
              "not_released": {"pelvis_obliquity": "synthetic: flipped by the same reversal",
                               "pelvis_obliquity_velocity": "synthetic: derivative of the flipped obliquity"},
              "decision": {"id": "D-SYNTH-2", "answer": "C"}, "audit_tasks": ["T-AUDIT"],
              "evidence_basis": "synthetic", "citation": "synthetic", "reason": "synthetic reversed pelvis"}
ANSWERED = {"id": "D-SYNTH-2", "status": "answered", "answer": "C"}
SIX = ("pelvis_tilt", "hip_angle", "knee_angle", "ankle_angle", "knee_moment", "ankle_moment")


def _correction_run(tmp_path, recording="rec4", correction=CORRECTION, decisions=(ANSWERED,), extra=None, **kw):
    src, evidence = _fixture()
    chans = {k: src[k] for k in SIX}
    stored = _reversed(chans) if recording == "rec4" else chans
    stored.update(extra or {})
    world = _audit_world(tmp_path, exceptions=[correction], decisions=decisions, **kw)
    return chans, stored, _run(stored, evidence, recording=recording, **world)


@pytest.fixture(scope="module")
def corrected(tmp_path_factory):
    return _correction_run(tmp_path_factory.mktemp("corr"))


def test_correction_publishes_the_corrected_pelvis_and_is_logged(corrected):
    _, stored, res = corrected
    truth = synthetic_leg(seed=41)[0]
    c = res.log["channels"]["pelvis_tilt"]
    # the stored (reversed) tilt equals the rule-B truth, so the net multiplier is +1: correction -1 x dataset -1
    assert c["publication"] == "publish" and c["multiplier"] == 1 and c["sign_vs_corrected_source"] == -1
    assert _bits_equal(res.channels["pelvis_tilt"], truth["pelvis_tilt"])
    assert c["source_correction"] == {**c["source_correction"], "id": "SYNTH-rec4-pelvis", "factor": -1,
                                      "applied": True, "decision": {"id": "D-SYNTH-2", "answer": "C"},
                                      "audit_tasks": ["T-AUDIT"]}
    assert res.log["corrections_applied"] == [{"id": "SYNTH-rec4-pelvis", "channel": "pelvis_tilt", "factor": -1,
                                               "decision": {"id": "D-SYNTH-2", "answer": "C"},
                                               "audit_tasks": ["T-AUDIT"], "net_multiplier": 1}]
    assert res.log["counts"]["corrected"] == 1
    assert any(i["kind"] == "correction" and i["channel"] == "pelvis_tilt" for i in res.review)
    rx = res.log["recording_exceptions"][0]
    assert rx["active"] and set(rx["not_released"]) == {"pelvis_obliquity", "pelvis_obliquity_velocity"}
    assert c["input_sha256"] == sa.array_sha256(stored["pelvis_tilt"])  # the log anchors the stored array
    for k in SIX[1:]:  # nothing else in the recording changes because of the correction
        assert res.log["channels"][k]["source_correction"] is None, k


def test_correction_is_undone_exactly_to_the_stored_array(corrected, tmp_path):
    _, stored, res = corrected
    restored = sa.undo_sign_application(res.channels, res.log)
    assert all(_bits_equal(restored[k], stored[k]) for k in stored)
    path = tmp_path / "sign_application.json"
    digest = sa.write_json_exclusive(path, res.log)
    restored = sa.undo_sign_application(res.channels, path, expected_log_sha256=digest)
    assert _bits_equal(restored["pelvis_tilt"], stored["pelvis_tilt"])


def test_correction_touches_only_its_recording(tmp_path):
    (tmp_path / "a").mkdir(), (tmp_path / "b").mkdir()
    _, _, normal = _correction_run(tmp_path / "a", recording="rec1")
    _, _, rev = _correction_run(tmp_path / "b")
    assert normal.log["corrections_applied"] == [] and normal.log["recording_exceptions"] == []
    assert normal.log["channels"]["pelvis_tilt"]["multiplier"] == -1
    for k in SIX:  # both recordings publish the same rule-B arrays: the correction undoes the reversal exactly
        assert _bits_equal(normal.channels[k], rev.channels[k]), k
    assert sa.cross_group_review([{**normal.log, "group_id": "rec1"}, {**rev.log, "group_id": "rec4"}]) == []


def test_reversed_recording_without_the_correction_is_not_published(tmp_path):
    """Contrast: the same reversed pelvis with no correction is held (the detector sees the flip)."""
    src, evidence = _fixture()
    res = _run(_reversed({k: src[k] for k in SIX}), evidence, recording="rec4", **_audit_world(tmp_path))
    assert res.log["channels"]["pelvis_tilt"]["publication"] == "hold"
    ok = {**res.log, "group_id": "rec4", "channels": {"pelvis_tilt": {**res.log["channels"]["pelvis_tilt"], "publication": "publish",
                                                  "multiplier": 1, "sign_vs_corrected_source": 1}}}
    ref = {**res.log, "group_id": "rec1", "channels": {"pelvis_tilt": {"publication": "publish", "multiplier": -1}}}
    assert sa.cross_group_review([ok, ref])  # an uncorrected reversal published as stored would be flagged


def test_segment_angles_are_derived_from_the_corrected_tilt(corrected):
    _, stored, res = corrected
    truth = synthetic_leg(seed=41)[0]
    seg, dlog = sa.derive_segment_angles(res)
    # rule-B chain of the known rule-B pelvis, hip and knee (no offsets in those synthetic sources), bit for bit
    assert _bits_equal(seg["thigh_angle"], truth["pelvis_tilt"] + truth["hip_angle"])
    assert _bits_equal(seg["shank_angle"], truth["pelvis_tilt"] + truth["hip_angle"] - truth["knee_angle"])
    # and against the independently noised segment truth: only the 0.005 rad noise of each term remains
    assert np.mean(np.abs(seg["thigh_angle"] - truth["thigh_angle"])) < 0.01
    assert np.mean(np.abs(seg["shank_angle"] - truth["shank_angle"])) < 0.012
    # foot carries the published ankle (known 5 deg source offset, never removed)
    assert _bits_equal(seg["foot_angle"], seg["shank_angle"] + res.channels["ankle_angle"])
    assert dlog["from_corrected_channels"] == [{"id": "SYNTH-rec4-pelvis", "channel": "pelvis_tilt"}]
    assert dlog["derived"]["thigh_angle"]["inputs_sha256"]["pelvis_tilt"] == \
        res.log["channels"]["pelvis_tilt"]["output_sha256"]
    # contrast: the stored (reversed) tilt would put the thigh off by twice the tilt
    wrong = stored["pelvis_tilt"] * -1 + res.channels["hip_angle"]  # the dataset sign alone, no correction
    assert np.mean(np.abs(wrong - truth["thigh_angle"])) > 0.25  # truth tilt is about -0.17 rad


def test_derived_inputs_for_the_corrected_recording_are_held_not_flipped(tmp_path):
    src, evidence = _fixture()
    stale = {"thigh_angle": np.negative(src["pelvis_tilt"]) + src["hip_angle"]}  # built from the stored tilt
    _, stored, res = _correction_run(tmp_path, extra=stale)
    c = res.log["channels"]["thigh_angle"]
    assert c["publication"] == "hold" and c["multiplier"] == 1 and "recompute" in c["hold_reason"]
    assert _bits_equal(res.channels["thigh_angle"], stored["thigh_angle"])
    seg, _ = sa.derive_segment_angles(res)  # the held input is ignored; thigh comes from the published chain
    truth = synthetic_leg(seed=41)[0]
    assert _bits_equal(seg["thigh_angle"], truth["pelvis_tilt"] + truth["hip_angle"])


@pytest.mark.parametrize("why, kw", [
    ("decision unanswered", dict(decisions=({"id": "D-SYNTH-2", "status": "open"},))),
    ("other answer", dict(decisions=({**ANSWERED, "answer": "B"},))),
    ("decision missing", dict(decisions=())),
    ("task not done", dict(status="review")),
    ("not cited", dict(record={"status": "done", "dataset": "synth", "summary": "pelvis reversed"})),
])
def test_inactive_correction_holds_everything_it_touches(tmp_path, why, kw):
    src, evidence = _fixture()
    extra = {"thigh_angle": src["hip_angle"].copy(), "pelvis_tilt_velocity": np.gradient(src["pelvis_tilt"], DT, axis=1)}
    _, stored, res = _correction_run(tmp_path, extra=extra, **kw)
    for k in ("pelvis_tilt", "thigh_angle", "pelvis_tilt_velocity"):
        c = res.log["channels"][k]
        assert c["publication"] == "hold" and "not active" in c["hold_reason"], (why, k)
        assert _bits_equal(res.channels[k], stored[k])
    assert res.log["corrections_applied"] == [] and res.log["counts"]["corrected"] == 0
    seg, dlog = sa.derive_segment_angles(res)  # no segment is built from a held pelvis or a held thigh input
    assert seg == {} and "pelvis_tilt (hold)" in dlog["not_derived"]["thigh_angle"], why
    assert set(dlog["not_derived"]) == {"thigh_angle", "shank_angle", "foot_angle"}


@pytest.mark.parametrize("bad", [
    {"corrections": {"pelvis_tilt": 1}}, {"corrections": {"pelvis_tilt": -1.0}}, {"corrections": {}},
    {"decision": None}, {"decision": {"id": "D-SYNTH-2"}}, {"derived_channels": ["pelvis_tilt"]},
    {"derived_channels": ["knee_angle"]}, {"channels": ["pelvis_tilt"]}, {"evidence_basis": ""},
    {"derived_velocities": ["pelvis_tilt_velocity", "thigh_angle_velocity", "shank_angle_velocity"]},
    {"derived_velocities": None},
    {"action": "flip"}])
def test_malformed_corrections_are_refused(tmp_path, bad):
    with pytest.raises(ValueError):
        _correction_run(tmp_path, correction={**CORRECTION, **bad})


def test_a_channel_named_by_two_exceptions_of_one_recording_raises(tmp_path):
    src, evidence = _fixture()
    hold = {**EXCEPTION, "recordings": ["rec4"], "channels": ["pelvis_tilt"]}
    world = _audit_world(tmp_path, exceptions=[CORRECTION, hold], decisions=(ANSWERED,))
    with pytest.raises(ValueError, match="named by exceptions"):
        _run({k: src[k] for k in SIX}, evidence, recording="rec4", **world)


def test_velocity_inputs_are_held_not_flipped_or_detected(tmp_path):
    """AB04/i0-like recording: the converters' velocities come from the stored (reversed) pelvis."""
    src, evidence = _fixture()
    stored_p = np.negative(src["pelvis_tilt"])
    extra = {"pelvis_tilt_velocity": np.gradient(stored_p, DT, axis=1),
             "thigh_angle_velocity": np.gradient(np.negative(stored_p) + src["hip_angle"], DT, axis=1),
             "pelvis_obliquity_velocity": np.ones_like(stored_p)}
    _, stored, res = _correction_run(tmp_path, extra=extra)
    for k in extra:
        c = res.log["channels"][k]
        assert c["publication"] == "hold" and c["multiplier"] == 1 and c["verdict"] == "not_run", k
        assert _bits_equal(res.channels[k], stored[k]), k
        assert k not in res.report["channels"], k  # never given to the detector
    assert "derive_angular_velocities" in res.log["channels"]["thigh_angle_velocity"]["hold_reason"]
    assert "not released" in res.log["channels"]["pelvis_obliquity_velocity"]["hold_reason"]
    assert res.log["channels"]["pelvis_tilt"]["publication"] == "publish"  # the angle itself is unaffected
    # a velocity passed for any other recording is held too: velocities are never sign-applied
    (tmp_path / "n").mkdir()
    _, _, normal = _correction_run(tmp_path / "n", recording="rec1",
                                   extra={"pelvis_tilt_velocity": np.gradient(src["pelvis_tilt"], DT, axis=1)})
    c = normal.log["channels"]["pelvis_tilt_velocity"]
    assert c["publication"] == "hold" and "not sign-applied" in c["hold_reason"]


def _central_differences(a, h):
    """Independent hand-written MATLAB gradient(a, h) along samples."""
    v = np.empty_like(a)
    v[:, 1:-1] = (a[:, 2:] - a[:, :-2]) / (2 * h)
    v[:, 0] = (a[:, 1] - a[:, 0]) / h
    v[:, -1] = (a[:, -1] - a[:, -2]) / h
    return v


def test_velocities_are_recomputed_from_the_corrected_angles(corrected, tmp_path):
    _, stored, res = corrected
    truth = synthetic_leg(seed=41)[0]
    seg, _ = sa.derive_segment_angles(res)
    vel, vlog = sa.derive_angular_velocities({"pelvis_tilt": res.channels["pelvis_tilt"], **seg}, DT)
    assert set(vel) == {"pelvis_tilt_velocity", "thigh_angle_velocity", "shank_angle_velocity", "foot_angle_velocity"}
    chain = {"pelvis_tilt": truth["pelvis_tilt"], "thigh_angle": truth["pelvis_tilt"] + truth["hip_angle"]}
    for k, a in chain.items():
        assert np.allclose(vel[k + "_velocity"], _central_differences(a, DT), rtol=1e-12, atol=1e-12), k
    assert "MATLAB gradient" in vlog["method"]
    # the same rule-B velocities as a normally stored recording
    (tmp_path / "n").mkdir()
    _, _, normal = _correction_run(tmp_path / "n", recording="rec1")
    nseg, _ = sa.derive_segment_angles(normal)
    nvel, _ = sa.derive_angular_velocities({"pelvis_tilt": normal.channels["pelvis_tilt"], **nseg}, DT)
    assert all(_bits_equal(vel[k], nvel[k]) for k in vel)
    # contrast: the converters' recipe on the stored tilt carries 2 x d(tilt)/dt in the thigh velocity
    stale = np.gradient(np.negative(stored["pelvis_tilt"]) + res.channels["hip_angle"], DT, axis=1)
    assert np.allclose(stale - vel["thigh_angle_velocity"], -2 * _central_differences(truth["pelvis_tilt"], DT),
                       atol=1e-9)
    assert np.mean(np.abs(stale - vel["thigh_angle_velocity"])) > 0.1


def test_angular_velocity_method_on_known_values():
    t = np.arange(150) * 0.01
    ramp = np.vstack([3.0 * t - 1.0, -0.5 * t])
    v, _ = sa.derive_angular_velocities({"a": ramp}, 0.01)
    assert np.allclose(v["a_velocity"], [[3.0] * 150, [-0.5] * 150], rtol=0, atol=1e-9)  # exact slope, ends too
    quad = np.vstack([t ** 2])
    v, _ = sa.derive_angular_velocities({"q": quad}, 0.01)
    assert np.allclose(v["q_velocity"][0, 1:-1], 2 * t[1:-1], atol=1e-9)  # central differences: exact inside
    assert np.isclose(v["q_velocity"][0, 0], 0.01) and np.isclose(v["q_velocity"][0, -1], t[-1] + t[-2])  # one-sided
    # phase-normalized strides: one spacing per unit (stride_duration_s / 149)
    dur = np.array([1.49, 0.745])
    x = np.vstack([np.linspace(0, 1, 150), np.linspace(0, 1, 150)])
    v, vlog = sa.derive_angular_velocities({"p": x}, dur / 149)
    assert np.allclose(v["p_velocity"], (1 / dur)[:, None], rtol=1e-9) and vlog["spacing_s"] == list(dur / 149)
    for bad in (0.0, -0.01, np.nan, [0.01, 0.0]):
        with pytest.raises(ValueError):
            sa.derive_angular_velocities({"p": x}, bad)
    with pytest.raises(ValueError):
        sa.derive_angular_velocities({"p": x.astype(np.float32)}, 0.01)


def test_hook_segment_chain_equals_the_detector_chain():
    det = sa.load_bound_detector(BUILD)
    assert tuple((d, q, j) for d, q, j, _ in sa.SEGMENT_CHAIN) == det.CHAIN
    assert all(c == det.JOINT_CCW[j.split("_")[0]] for _, _, j, c in sa.SEGMENT_CHAIN)


# ---------------------------------------------------------------- the committed table and provenance
TABLE = json.loads(sa.AUDITED_PATH.read_text())
BACKLOG = {t["id"]: t for t in json.loads(sa.BACKLOG_PATH.read_text())["tasks"]}
ITEMS = [(ds, item) for ds, d in TABLE["datasets"].items() for item in d["entries"] + d["exceptions"]]
# Coordinator-owned backlog records that do not yet cite these items by id (requested in the CORE-11 handoff,
# backlog_edits_requested). Strict: once every listed task cites an item, its test
# passes and the id must be removed from this set.
PENDING_BACKLOG_CITATIONS = set()
DECISIONS = {d["id"]: d for d in json.loads(sa.BACKLOG_PATH.read_text()).get("decisions", [])}


def test_committed_table_is_well_formed_and_bound():
    assert "contributor_tools/common/audited_signs.json" in sa.bound_build()
    assert "SIGN-SURVEY" not in json.dumps([i for _, i in ITEMS])  # the survey is not a verified task
    assert not any(i["id"] == "GT24-hip_moment" for _, i in ITEMS)  # removed: one family, no model definition
    for _, i in ITEMS:
        assert i["audit_tasks"] and all(t in BACKLOG for t in i["audit_tasks"]), i["id"]
        if i.get("action") != "correct":  # a correction may wait on its own task; it holds until then
            assert all(BACKLOG[t].get("status") == "done" for t in i["audit_tasks"]), i["id"]
        assert "channels" in i or i["evidence_basis"].strip()
    policy, _ = sa._load_policy()
    for ds in TABLE["datasets"]:
        entries, exceptions, pattern = sa.load_audited_signs(ds, TABLE, BACKLOG,
                                                             lambda t: policy.task_done(t, sa.BACKLOG_PATH),
                                                             DECISIONS)
        assert pattern
        for x in exceptions:
            assert all(re.fullmatch(pattern, r) for r in x["recordings"]), x["id"]
    ids = [i["id"] for _, i in ITEMS]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("dataset, item", [
    pytest.param(ds, i, id=i["id"], marks=pytest.mark.xfail(strict=True, reason="backlog citation requested")
                 if i["id"] in PENDING_BACKLOG_CITATIONS else ())
    for ds, i in ITEMS])
def test_each_audit_task_record_cites_its_table_entry(dataset, item):
    assert sa.entry_linked(item, BACKLOG)[0], item["id"]


AB04 = next(i for ds, i in ITEMS if i["id"] == "UM21-P01-AB04-i0-pelvis")


def test_um21_ab04_i0_correction_records_josé_answer():
    """D-UM21-P01-1 = C: the hold became a per-recording pelvis tilt correction (UM21-P02)."""
    x = AB04
    assert x["recordings"] == ["AB04/i0"] and x["action"] == "correct"
    assert x["corrections"] == {"pelvis_tilt": -1}
    # every segment angle built from the pelvis is recomputed from the corrected tilt, never flipped
    assert x["derived_channels"] == ["thigh_angle", "shank_angle", "foot_angle"] and "channels" not in x
    # the reversal also flips obliquity and shifts rotation; outside the sagittal release, not released here
    assert set(x["not_released"]) == {"pelvis_obliquity", "pelvis_rotation",
                                      "pelvis_obliquity_velocity", "pelvis_rotation_velocity"}
    # velocities of the corrected and derived channels are recomputed after the hook or left out (F1, UM21-P02)
    assert x["derived_velocities"] == ["pelvis_tilt_velocity", "thigh_angle_velocity", "shank_angle_velocity",
                                       "foot_angle_velocity"]
    for col in ("pelvis_sagittal_velocity_rad_s", "thigh/shank/foot_sagittal_velocity", "derive_angular_velocities"):
        assert col in x["velocity_rule"], col
    assert x["audit_tasks"] == ["UM21-P01", "UM21-P02"] and BACKLOG["UM21-P01"]["status"] == "done"
    assert x["decision"] == {"id": "D-UM21-P01-1", "answer": "C"}
    assert DECISIONS["D-UM21-P01-1"]["answer"] == "C"  # the recorded answer is the backlog's answer
    assert "um21-p01-pelvis-heading.json" in x["citation"] and "UM21-P01" in x["evidence_basis"]


def _reversed(src):
    """Synthetic AB04/i0: the same leg stored with the pelvis computed facing backwards (tilt negated)."""
    return {**src, "pelvis_tilt": np.negative(src["pelvis_tilt"])}


def _activated_backlog(tmp_path):
    """Copy of the real backlog in which UM21-P02 is done and cites the correction (what verification does)."""
    data = json.loads(sa.BACKLOG_PATH.read_text())
    for t in data["tasks"]:
        if t["id"] == "UM21-P02":
            t["status"] = "done"
            t.setdefault("handoff", {}).setdefault("checks", []).append("Correction: UM21-P01-AB04-i0-pelvis.")
    path = tmp_path / "backlog.json"
    path.write_text(json.dumps(data))
    return path


def test_um21_ab04_i0_with_the_committed_table(tmp_path):
    """Real table: AB04/i0 pelvis is held until UM21-P02 is done and cites the correction, then published
    corrected; AB01/i0 is never touched by it."""
    src, evidence = _fixture()
    truth = synthetic_leg(seed=41)[0]
    chans = {k: src[k] for k in ("pelvis_tilt", "hip_angle", "knee_angle")}
    ab04 = _reversed(chans)
    now = _run(ab04, evidence, dataset="UM21", recording="AB04/i0", audited_path=sa.AUDITED_PATH)
    if BACKLOG["UM21-P02"]["status"] != "done" or not sa.entry_linked(AB04, BACKLOG)[0]:
        c = now.log["channels"]["pelvis_tilt"]
        assert c["publication"] == "hold" and "not active" in c["hold_reason"]
        assert _bits_equal(now.channels["pelvis_tilt"], ab04["pelvis_tilt"])
    on = _run(ab04, evidence, dataset="UM21", recording="AB04/i0", audited_path=sa.AUDITED_PATH,
              backlog_path=_activated_backlog(tmp_path))
    c = on.log["channels"]["pelvis_tilt"]
    assert c["publication"] == "publish" and c["source_correction"]["applied"]
    assert c["source_correction"]["decision"] == {"id": "D-UM21-P01-1", "answer": "C"}
    assert _bits_equal(on.channels["pelvis_tilt"], truth["pelvis_tilt"])  # rule-B pelvis, known by construction
    other = _run(chans, evidence, dataset="UM21", recording="AB01/i0", audited_path=sa.AUDITED_PATH,
                 backlog_path=_activated_backlog(tmp_path))
    assert other.log["channels"]["pelvis_tilt"]["source_correction"] is None
    assert other.log["corrections_applied"] == [] and other.log["channels"]["pelvis_tilt"]["multiplier"] == -1


def test_publication_policy_cites_josé_quote_recorded_under_um21_c01():
    assert sa.PREFERENCE_QUOTE in sa.PUBLICATION_POLICY["basis"] and sa.PREFERENCE_TASK == "UM21-C01"
    checks = BACKLOG[sa.PREFERENCE_TASK]["handoff"]["checks"]
    assert any(f'"{sa.PREFERENCE_QUOTE}"' in str(c) and "José instruction in chat, 2026-10-30" in str(c)
               for c in checks)


def test_cross_group_review_flags_mixed_storage_within_a_dataset():
    def log(group, mult, publication="publish"):
        return {"dataset": "SYNTH", "group_id": group, "leg": "right",
                "channels": {"hip_power": {"publication": publication, "multiplier": mult}}}
    assert sa.cross_group_review([log("a", -1), log("b", -1)]) == []
    items = sa.cross_group_review([log("a", -1), log("b", 1)])
    assert items and items[0]["published_signs"] == {"a right": -1, "b right": 1}
    assert sa.cross_group_review([log("a", -1), log("b", 1, "hold")])[0]["held"] == ["b right"]
