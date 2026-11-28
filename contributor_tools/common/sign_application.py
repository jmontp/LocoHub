"""Converter hook for the sagittal sign detector (CORE-11).

Design: docs/maintainers/sign-offset-detector-design.md, section "Converter hook (CORE-11)".

An adapter passes one group (one recording, or one recording sample, and one leg) of
UNTRANSFORMED source channels, plain float64 ``numpy.ndarray`` of shape ``(units, samples)``, plus
the evidence inputs the detector accepts (markers, CoP, GRF, task, ...), the dataset key and the
source recording id. Audited signs come only from the committed table audited_signs.json. The hook

1. refuses to run unless the caller declares the detector build (full lowercase sha256) and the
   detector file has exactly that hash; it executes the bytes it hashed. The documentation policy
   is also executed from the bytes it hashed, the refuted-documentation table is read once, and the
   hook's own bytes are hashed at import; together these are the bound build;
2. in ``mode="full"`` refuses unless a committed pilot record names the dataset's done pilot task
   (CORE-11-P-<dataset>), whose backlog record cites the record path and sha256 and the receipt
   sha256, and a committed guarded-launcher receipt that matches its hash, completed cleanly and
   binds the same build;
3. passes documentation statements through ``documentation_policy.split_documentation``;
4. runs ``detect_leg`` with the build's own DEFAULTS (no parameter overrides);
5. accepts a detector ``apply`` only when an independent guard, using the hook's own frozen family
   table, finds agreeing moderate/strong tests from at least two families and no dissent;
6. applies per-recording exceptions first: a ``hold`` keeps its channels out; an active ``correct``
   (its audit tasks done and citing it, its backlog decision answered as recorded) negates the stored
   channel before detection, holds that recording's derived segment-angle and velocity inputs (they
   must be recomputed from the corrected channel with ``derive_segment_angles`` and
   ``derive_angular_velocities``, or left out) and holds the channels it does not release; any
   ``*_velocity`` channel is held for every recording (velocities are never sign-applied); an inactive ``correct`` holds everything it touches. Every other channel is
   decided with ``publication_rule`` (standing preference: standardized names by default when a
   verified audit supports the sign), multiplied by that sign (exact negation or copy; a correction
   is folded into the logged net multiplier) and nothing else changes; offsets are never applied;
7. checks that the input channels and every evidence array are unchanged (by hash);
8. returns a sign-application log (enough to undo every change and verify both directions by hash)
   and a review list.

``scientific_approval`` is always false. This module reads no research data and writes files only
through ``write_json_exclusive``.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import types

import numpy as np

SCHEMA_VERSION = "sign-application/0.4"
ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = Path(__file__).resolve()
HOOK_SHA256 = hashlib.sha256(HOOK_PATH.read_bytes()).hexdigest()  # hashed at import
DETECTOR_PATH = ROOT / "contributor_tools/common/sign_offset_detector.py"
POLICY_PATH = ROOT / "contributor_tools/common/documentation_policy.py"
REFUTED_PATH = ROOT / "contributor_tools/common/refuted_documentation.json"
AUDITED_PATH = ROOT / "contributor_tools/common/audited_signs.json"
PILOT_TASK_PREFIX = "CORE-11-P-"  # the pilot task of dataset DS is CORE-11-P-DS
BACKLOG_PATH = ROOT / "docs/maintainers/backlog.json"
PILOT_RECORD_DIR = "docs/quality/audits"
SHA256_RE = re.compile(r"[0-9a-f]{64}", re.ASCII)
DATA_STRENGTHS = ("moderate", "strong")
REVIEW_VERDICTS = ("suggest", "conflict", "abstain")
EVIDENCE_KEYS = {"reference_angles", "joint_positions", "cop", "grf", "stance", "dt", "task",
                 "templates", "marker_points", "grf_unit", "body_mass_kg", "cop_registration",
                 "unit_durations_s"}
MODES = ("pilot", "full")

# The hook's own frozen copy of the detector's evidence families (failure-mode grouping) and
# plate-timed tests. A test checks it equals the detector's table, so a change to either fails
# loudly instead of letting the guard count families with the detector's own (possibly wrong) table.
FAMILY_TABLE = {
    "fine": {"reference_angle": "marker_geometry", "knee_hinge_asymmetry": "joint_anatomy",
             "derived:segment_chain": "marker_geometry", "lever_arm": "plate_geometry",
             "late_stance_plantarflexor": "plate_timing", "hip_stance_extension": "plate_timing",
             "ankle_pushoff_plantarflexion": "plate_timing", "hip_moment_timing": "plate_timing",
             "power_timing": "plate_timing", "inverse_dynamics_light": "plate_geometry",
             "derived:power_identity": "power_identity"},
    "coarse": {"reference_angle": "kinematic", "knee_hinge_asymmetry": "kinematic",
               "derived:segment_chain": "kinematic", "lever_arm": "force_plate",
               "late_stance_plantarflexor": "force_plate", "hip_stance_extension": "force_plate",
               "ankle_pushoff_plantarflexion": "force_plate", "hip_moment_timing": "force_plate",
               "power_timing": "force_plate", "inverse_dynamics_light": "force_plate",
               "derived:power_identity": "power_identity"},
}
PLATE_TIMING_TESTS = frozenset({"late_stance_plantarflexor", "hip_stance_extension",
                                "ankle_pushoff_plantarflexion", "hip_moment_timing", "power_timing"})

# Per-recording exceptions: 'hold' keeps channels out; 'correct' flips a stored channel (a source
# error proved by an audit and approved by a backlog decision) before detection and publication.
EXCEPTION_ACTIONS = ("hold", "correct")
# The hook's own frozen copy of the rule-B segment chain (a test checks it equals the detector's CHAIN
# and JOINT_CCW): distal = proximal + JOINT_CCW x joint, i.e. thigh = pelvis + hip, shank = thigh - knee,
# foot = shank + ankle. Used by derive_segment_angles on published (rule-B) channels only.
SEGMENT_CHAIN = (("thigh_angle", "pelvis_tilt", "hip_angle", 1),
                 ("shank_angle", "thigh_angle", "knee_angle", -1),
                 ("foot_angle", "shank_angle", "ankle_angle", 1))
SEGMENT_CHANNELS = tuple(d for d, _, _, _ in SEGMENT_CHAIN)
# Angular velocities are never sign-applied: a channel named <angle>_velocity passed to the hook is held
# (never given to the detector) and must be recomputed after the hook from published or derived angles
# with derive_angular_velocities, which uses the UM21 converters' differentiation (MATLAB gradient).
VELOCITY_SUFFIX = "_velocity"

# Policy application, not a new decision (D-CORE-11-1 withdrawn). Provenance: José's words recorded by
# the coordinator in docs/maintainers/backlog.json, task UM21-C01, handoff checks (a test finds them).
PREFERENCE_QUOTE = "all standardized names (thats the point of the project)"
PREFERENCE_TASK = "UM21-C01"
PREFERENCE_RECORD = ('José instruction in chat, 2026-10-30, answering D-UM21-C01-2: "' + PREFERENCE_QUOTE + '"')
PUBLICATION_POLICY = {
    "basis": (PREFERENCE_RECORD + "; recorded in docs/maintainers/backlog.json, task " + PREFERENCE_TASK
              + " handoff checks, as the standing preference: release signals under standardized LocoHub "
                "names whenever a verified audit supports the sign; 'leave out' is not a neutral default"),
    "provenance": {"quote": PREFERENCE_QUOTE, "task": PREFERENCE_TASK,
                   "location": "docs/maintainers/backlog.json, tasks[UM21-C01].handoff.checks"},
    "audited_signs": "contributor_tools/common/audited_signs.json (bound build); adapters pass only the dataset key",
    "rule": ["verified audit sign and detector applied, suggested or abstained with the same sign (or no "
             "sign): publish with the audited sign",
             "verified audit sign and detector suggests or applies the opposite sign, or reports a conflict: "
             "hold for review, do not publish",
             "no verified audit: the detector alone; publish only a guarded detector apply"],
    "verified_audit": ("an entry counts only if every audit task it lists has status done in "
                       "docs/maintainers/backlog.json and every one of those backlog records cites the entry id "
                       "explicitly; a mention of the channel name does not count"),
    "exceptions": ("per-recording exceptions in the table are applied first: a hold holds its channels; an "
                   "active correction negates the stored channel before the rule (logged with its audit tasks "
                   "and decision), holds the recording's derived segment-angle inputs for recomputation and "
                   "lists its not-released channels; an inactive correction holds"),
}


class UnboundBuildError(RuntimeError):
    """The declared build is missing, malformed, or not the code on disk."""


class PilotGateError(RuntimeError):
    """A full run was requested without a passing pilot of the same bound build."""


class UndoError(RuntimeError):
    """Arrays or log offered for undo are not the ones recorded."""


@dataclass
class SignApplication:
    channels: dict      # logical name -> signed array (float64, same shape as the input)
    log: dict           # sign-application log (JSON-serialisable)
    review: list        # review items (JSON-serialisable)
    report: dict        # the detector's full report for this group


# ---------------------------------------------------------------- hashing and loading
def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def array_sha256(a):
    """Hash of dtype, shape and C-order bytes: equal hashes mean bit-identical arrays."""
    a = np.ascontiguousarray(a)
    h = hashlib.sha256(f"{a.dtype.str}|{a.shape}|".encode())
    h.update(a.tobytes())
    return h.hexdigest()


def _check_declared(declared, what):
    if not isinstance(declared, str) or not SHA256_RE.fullmatch(declared):
        raise UnboundBuildError(f"{what}: a full lowercase sha256 (64 hex characters) must be declared; "
                                f"got {declared!r}")


def _exec_bytes(name, path, data):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module  # dataclasses resolve their module through sys.modules
    try:
        exec(compile(data, str(path), "exec"), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


_LOADED = {}


def load_bound_detector(declared_sha256, path=DETECTOR_PATH):
    """Execute the detector file only if its bytes hash to the declared build (read once, the
    executed bytes are the hashed bytes; loaded by path, not through the pandas-importing package)."""
    _check_declared(declared_sha256, "detector build")
    path = Path(path)
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != declared_sha256:
        raise UnboundBuildError(f"detector build mismatch: declared {declared_sha256[:12]}, "
                                f"file {actual[:12]} ({path.name}); pilot and bind the build first")
    key = ("detector", actual)
    if key not in _LOADED:
        _LOADED[key] = _exec_bytes(f"sign_offset_detector_{actual[:16]}", path, data)
    return _LOADED[key]


def _load_policy(path=POLICY_PATH):
    """(module, sha256 of the executed bytes)."""
    data = Path(path).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    key = ("policy", digest)
    if key not in _LOADED:
        _LOADED[key] = _exec_bytes(f"documentation_policy_{digest[:16]}", path, data)
    return _LOADED[key], digest


def _rel(path, root=ROOT):
    p = Path(path).resolve()
    root = Path(root).resolve()
    return str(p.relative_to(root)) if p.is_relative_to(root) else str(p)


def bound_build(detector_path=DETECTOR_PATH, policy_path=POLICY_PATH, refuted_path=REFUTED_PATH,
                audited_path=AUDITED_PATH):
    """Repository-relative path -> sha256 of every file whose content can change a signed output, as
    on disk now (the hook as imported). A pilot binds these as guarded-launcher `bindings`."""
    return {_rel(detector_path): file_sha256(detector_path), _rel(HOOK_PATH): HOOK_SHA256,
            _rel(policy_path): file_sha256(policy_path), _rel(refuted_path): file_sha256(refuted_path),
            _rel(audited_path): file_sha256(audited_path)}


# ---------------------------------------------------------------- audited signs
def _cites_id(record, item_id):
    """True when the backlog record cites `item_id` as a whole token (not as part of a longer id)."""
    if record is None:
        return False
    text = json.dumps(record, ensure_ascii=False)
    return re.search(r"(?<![A-Za-z0-9_-])" + re.escape(item_id) + r"(?![A-Za-z0-9_-])", text) is not None


def entry_linked(item, records):
    """(ok, reason): every audit task listed by a table item is a backlog task whose record cites the
    item's id explicitly. A mention of the channel name does not count (a negative mention would)."""
    tasks = item.get("audit_tasks")
    if not isinstance(tasks, list) or not tasks or not all(isinstance(t, str) and t.strip() for t in tasks):
        raise ValueError(f"table item {item.get('id')!r}: audit_tasks must be a non-empty list of backlog ids")
    missing = [t for t in tasks if not _cites_id(records.get(t), item["id"])]
    if missing:
        return False, f"backlog record(s) {missing} do not cite {item['id']}"
    return True, f"cited by {', '.join(tasks)}"


def _check_exception(x):
    """Shape checks for one per-recording exception (action 'hold' or 'correct')."""
    xid = x.get("id")
    if not x.get("recordings") or x.get("action") not in EXCEPTION_ACTIONS:
        raise ValueError(f"exception {xid!r}: needs recordings and action 'hold' or 'correct'")
    if x["action"] == "hold":
        if not x.get("channels"):
            raise ValueError(f"exception {xid!r}: a hold needs channels")
        return
    corr = x.get("corrections")
    if not isinstance(corr, dict) or not corr or any(type(v) is not int or v != -1 for v in corr.values()):
        raise ValueError(f"exception {xid!r}: corrections must map channels to the integer -1 (a sign flip)")
    if "channels" in x:
        raise ValueError(f"exception {xid!r}: a correction names its channels in corrections, not channels")
    dec = x.get("decision")
    if not isinstance(dec, dict) or not isinstance(dec.get("id"), str) or not isinstance(dec.get("answer"), str):
        raise ValueError(f"exception {xid!r}: a correction needs the decision id and answer that approved it")
    derived = x.get("derived_channels")
    if not isinstance(derived, list) or set(derived) - set(SEGMENT_CHANNELS) or set(derived) & set(corr):
        raise ValueError(f"exception {xid!r}: derived_channels must list segment angles ({SEGMENT_CHANNELS}) "
                         "that are not themselves corrected")
    if not isinstance(x.get("not_released", {}), dict):
        raise ValueError(f"exception {xid!r}: not_released must map channel -> reason")
    want = {c + VELOCITY_SUFFIX for c in list(corr) + derived}
    vel = x.get("derived_velocities")
    if not isinstance(vel, list) or set(vel) != want or len(vel) != len(set(vel)):
        raise ValueError(f"exception {xid!r}: derived_velocities must name the velocity of every corrected and "
                         f"derived channel ({sorted(want)}): they are recomputed after the hook or left out")
    for key in ("evidence_basis", "citation"):
        if not isinstance(x.get(key), str) or not x[key].strip():
            raise ValueError(f"exception {xid!r}: a correction needs {key}")


def correction_active(x, records, task_done, decisions):
    """(ok, reason) for a 'correct' exception: every listed audit task is done and cites the id, and the
    backlog decision it names is answered with exactly the recorded answer. Otherwise the hook holds."""
    linked, lwhy = entry_linked(x, records)
    why = [w for ok, w in (task_done(t) for t in x["audit_tasks"]) if not ok]
    if not linked:
        why.append(lwhy)
    dec = (decisions or {}).get(x["decision"]["id"])
    if dec is None:
        why.append(f"decision {x['decision']['id']} is not in the backlog")
    elif dec.get("answer") != x["decision"]["answer"]:
        why.append(f"decision {x['decision']['id']} answer is {dec.get('answer')!r}, "
                   f"not {x['decision']['answer']!r}")
    if why:
        return False, "; ".join(why)
    return True, f"{lwhy}; {x['decision']['id']} = {x['decision']['answer']}"


def load_audited_signs(dataset, table, records, task_done, decisions=None):
    """(entries by channel, exceptions, recording pattern) for one dataset key, which must be in the
    table exactly (an unknown or miscased key raises: it would skip the exceptions). An entry is
    `verified` only when every listed audit task is done and cites the entry id. A 'correct' exception
    is `active` only when it is verified the same way and its decision (from `decisions`, the backlog's
    decisions by id) carries the recorded answer; an inactive correction holds its channels."""
    datasets = table.get("datasets") or {}
    if dataset not in datasets:
        raise ValueError(f"dataset key {dataset!r} is not in the audited-sign table (keys: {sorted(datasets)}); "
                         "add the dataset, even with no entries, before converting it")
    ds = datasets[dataset]
    pattern = ds.get("recording_id_pattern")
    if not isinstance(pattern, str) or not pattern:
        raise ValueError(f"{dataset}: recording_id_pattern is required")
    entries = {}
    for e in ds.get("entries", []):
        sign = e.get("sign")
        if type(sign) is not int or sign not in (1, -1):
            raise ValueError(f"audited sign entry {e.get('id')!r}: sign must be the integer +1 or -1")
        if not isinstance(e.get("evidence_basis"), str) or not e["evidence_basis"].strip():
            raise ValueError(f"audited sign entry {e.get('id')!r}: evidence_basis is required")
        if e["channel"] in entries:
            raise ValueError(f"{dataset} {e['channel']}: more than one audited sign entry")
        linked, lwhy = entry_linked(e, records)
        done = [task_done(t) for t in e["audit_tasks"]]
        not_done = [why for ok, why in done if not ok]
        entries[e["channel"]] = {**e, "verified": linked and not not_done,
                                 "reason": "; ".join(not_done + [lwhy]) if not_done else lwhy}
    exceptions = []
    for x in ds.get("exceptions", []):
        _check_exception(x)
        linked, lwhy = entry_linked(x, records)
        item = {**x, "linked": linked, "link_reason": lwhy}  # a hold applies even if unlinked
        if x["action"] == "correct":
            item["active"], item["active_reason"] = correction_active(x, records, task_done, decisions)
        exceptions.append(item)
    return entries, exceptions, pattern


def _recording_exceptions(exceptions, recording):
    """(held: channel -> (exception, reason), corrected: channel -> active 'correct' exception,
    not_released: channel names a correction does not release) for one recording. A channel named by two
    exceptions of one recording is ambiguous and raises."""
    held, corrected, seen, not_released = {}, {}, {}, set()
    for x in exceptions:
        if recording not in x["recordings"]:
            continue
        if x["action"] == "hold":
            names = {c: f"per-recording exception {x['id']} ({', '.join(x['audit_tasks'])}"
                        + (f", pending {x['pending_decision']}" if x.get("pending_decision") else "")
                        + f"): {x['reason']}" for c in x["channels"]}
        elif not x["active"]:  # fail-safe: an unverified correction holds everything it touches
            names = {c: f"per-recording correction {x['id']} not active ({x['active_reason']}); held: {x['reason']}"
                     for c in list(x["corrections"]) + x["derived_channels"] + x["derived_velocities"]}
        else:
            names = {c: f"per-recording correction {x['id']}: derived from the uncorrected stored channels; "
                        f"recompute with derive_segment_angles from the published channels"
                     for c in x["derived_channels"]}
            names.update({c: f"per-recording correction {x['id']}: velocity of the uncorrected stored channels; "
                             f"recompute with derive_angular_velocities from the published or derived angle, "
                             f"or leave it out" for c in x["derived_velocities"]})
            corrected.update({c: x for c in x["corrections"]})
        if x["action"] == "correct":
            not_released |= set(x.get("not_released") or {})
            names.update({c: f"per-recording correction {x['id']}: not released for this recording: {why}"
                          for c, why in (x.get("not_released") or {}).items()})
        for c in list(names) + [c for c in corrected if corrected[c] is x]:
            if c in seen:
                raise ValueError(f"recording {recording}: {c} is named by exceptions {seen[c]} and {x['id']}")
            seen[c] = x["id"]
        held.update({c: (x, why) for c, why in names.items()})
    return held, corrected, not_released


# ---------------------------------------------------------------- pilot gate
def _git_blob_id(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _committed_blob(path, repo_root):
    rel = _rel(path, repo_root)
    try:
        out = subprocess.run(["git", "-C", str(repo_root), "ls-tree", "HEAD", "--", rel],
                             capture_output=True, text=True, timeout=30, check=True).stdout.split()
    except subprocess.CalledProcessError:
        return None  # no commit (or not a repository): nothing is committed
    except (OSError, subprocess.SubprocessError) as exc:
        raise PilotGateError(f"cannot read the committed pilot record: {exc}") from exc
    return out[2] if len(out) >= 4 and out[1] == "blob" else None


def check_pilot_record(record_path, dataset, build, task_done, records, repo_root=ROOT):
    """Return (record, facts) for a full run, or raise PilotGateError.

    The record must be a committed file under docs/quality/audits whose bytes equal HEAD. Its pilot
    task must be CORE-11-P-<dataset>, done in the backlog (`task_done`), with backlog dataset equal to
    this dataset, and its backlog record must cite the pilot record path, the record sha256 and the
    receipt sha256. The guarded-launcher receipt must be committed too (bytes equal HEAD), hash to the
    recorded sha256, have completed cleanly, and bind exactly the record's bindings, which must include
    every file of this run's bound build at the same hash (a pilot also binds its adapter and probe).
    """
    if record_path is None:
        raise PilotGateError("full run refused: no pilot record of the bound build")
    repo_root = Path(repo_root).resolve()
    record_path = Path(record_path)
    record_path = (record_path if record_path.is_absolute() else repo_root / record_path).resolve()
    if not record_path.is_relative_to(repo_root / PILOT_RECORD_DIR):
        raise PilotGateError(f"full run refused: pilot record must be under {PILOT_RECORD_DIR}")
    data = record_path.read_bytes()
    if _committed_blob(record_path, repo_root) != _git_blob_id(data):
        raise PilotGateError("full run refused: pilot record is not committed as is (differs from HEAD)")
    rec = json.loads(data)
    problems = []
    if rec.get("dataset") != dataset:
        problems.append(f"pilot dataset {rec.get('dataset')!r} is not {dataset!r}")
    if rec.get("outcome") != "passed":
        problems.append(f"pilot outcome {rec.get('outcome')!r} is not 'passed'")
    task = rec.get("pilot_task")
    record_sha = hashlib.sha256(data).hexdigest()
    record_rel = _rel(record_path, repo_root)
    receipt = rec.get("launcher_receipt") or {}
    rpath, rsha = receipt.get("path"), receipt.get("sha256")
    if task != PILOT_TASK_PREFIX + dataset:
        problems.append(f"pilot task {task!r} is not {PILOT_TASK_PREFIX + dataset!r}")
    else:
        ok, why = task_done(task)
        if not ok:
            problems.append(f"pilot task not verified: {why}")
        brec = records.get(task) or {}
        if str(brec.get("dataset", "")).upper() != dataset:
            problems.append(f"pilot task backlog dataset {brec.get('dataset')!r} is not {dataset!r}")
        text = json.dumps(brec, ensure_ascii=False)
        missing = [name for name, value in (("pilot record path", record_rel), ("pilot record sha256", record_sha),
                                            ("receipt sha256", rsha)) if not isinstance(value, str) or value not in text]
        if missing:
            problems.append(f"pilot task backlog record does not cite the {', '.join(missing)}")
    bindings = rec.get("bindings")
    if not isinstance(bindings, dict) or any(bindings.get(k) != v for k, v in build.items()):
        problems.append("pilot bindings do not include this run's bound build: "
                        + ", ".join(f"{k}: pilot {str((bindings or {}).get(k))[:12]}, run {v[:12]}"
                                    for k, v in build.items() if (bindings or {}).get(k) != v))
    facts = {"record": record_rel, "record_sha256": record_sha}
    if not isinstance(rpath, str) or not isinstance(rsha, str) or not SHA256_RE.fullmatch(rsha):
        problems.append("pilot record has no launcher receipt path and sha256")
    else:
        rp = (Path(rpath) if Path(rpath).is_absolute() else repo_root / rpath).resolve()
        try:
            rdata = rp.read_bytes()
        except OSError as exc:
            problems.append(f"launcher receipt unreadable: {type(exc).__name__}")
            rdata = None
        if rdata is not None:
            if not rp.is_relative_to(repo_root) or _committed_blob(rp, repo_root) != _git_blob_id(rdata):
                problems.append("launcher receipt is not committed as is in this repository")
            if hashlib.sha256(rdata).hexdigest() != rsha:
                problems.append("launcher receipt does not match its recorded sha256")
            else:
                r = json.loads(rdata)
                spec = r.get("spec") or {}
                if r.get("status") != "completed" or r.get("clean_success") is not True:
                    problems.append("launcher receipt is not a clean completed run")
                if Path(str(spec.get("cwd"))).resolve() != repo_root:
                    problems.append("launcher receipt bindings are not relative to this repository")
                if spec.get("bindings") != bindings:
                    problems.append("launcher receipt binds different files or hashes than the pilot record")
                before = r.get("bindings_before") or {}
                after = r.get("bindings_after") or {}
                if set(before) != set(bindings or {}) or not all(v.get("matches") for v in before.values()) \
                        or set(after) != set(bindings or {}) or not all(v.get("matches") for v in after.values()):
                    problems.append("launcher receipt does not show every binding matching before and after")
                facts["receipt_sha256"] = rsha
    if problems:
        raise PilotGateError("full run refused: " + "; ".join(problems))
    return rec, facts


# ---------------------------------------------------------------- guard and publication rule
def _family_of(e, grouping, merged):
    test = e["test"]
    if merged and ((e.get("stats") or {}).get("half_cycle_ambiguous") or test in PLATE_TIMING_TESTS):
        return "fixed_timing_shape"
    key = test if test.startswith("derived:") else test.split(":")[0]
    return FAMILY_TABLE[grouping].get(key)


def guard_apply(channel_report, min_families, grouping):
    """Independent re-check of an `apply` verdict from its stored evidence, using the hook's own
    family table. Returns (ok, reason)."""
    sign = channel_report.get("sign")
    if type(sign) is not int or sign not in (1, -1):
        return False, f"sign {sign!r} is not +1 or -1"
    if min_families < 2:
        return False, f"min_families {min_families} < 2"
    if grouping not in FAMILY_TABLE:
        return False, f"unknown family grouping {grouping!r}"
    ev = channel_report.get("evidence") or []
    data = [e for e in ev if e.get("sign") is not None and e.get("strength") in DATA_STRENGTHS]
    if any(e["sign"] != sign for e in data):
        return False, "a moderate or strong test dissents"
    if any(e.get("sign") not in (None, sign) for e in ev if e.get("strength") == "documentation"):
        return False, "a documentation statement dissents"
    merged = any((e.get("stats") or {}).get("half_cycle_ambiguous") for e in data)
    support = {f for f in (_family_of(e, grouping, merged) for e in data) if f}
    claimed = set(channel_report.get("families") or [])
    if len(claimed) < 2 or not claimed <= support:
        return False, f"families {sorted(claimed)} not backed by agreeing tests from {sorted(support)}"
    if len(support) < min_families:
        return False, f"agreeing tests come from {len(support)} famil{'y' if len(support) == 1 else 'ies'}"
    return True, f"agreeing tests from {', '.join(sorted(support))}"


def publication_rule(verdict, detector_sign, detector_applied, audit_sign):
    """(multiplier, basis, publication, hold_reason) for one channel; see PUBLICATION_POLICY.
    detector_applied: a detector apply that passed the guard. audit_sign: +1/-1 from a verified
    audit, or None."""
    if audit_sign is not None:
        if detector_applied and detector_sign == audit_sign:
            return audit_sign, "audit_and_detector", "publish", None
        if detector_applied:
            return 1, "none", "hold", "detector applied the opposite of the verified audit sign"
        if verdict == "conflict":
            return 1, "none", "hold", "detector reports a conflict"
        if detector_sign is not None and detector_sign != audit_sign:
            return 1, "none", "hold", "detector suggests the opposite of the verified audit sign"
        return audit_sign, "audit", "publish", None
    if detector_applied:
        return detector_sign, "detector", "publish", None
    return 1, "none", "hold", "no verified audit sign and no guarded detector apply"


# ---------------------------------------------------------------- run
def _finite(x):
    if isinstance(x, float) and not math.isfinite(x):
        return None
    if isinstance(x, dict):
        return {k: _finite(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_finite(v) for v in x]
    return x


def _evidence_hashes(evidence):
    """sha256 of every array in the evidence (top level and one dict level), for the unchanged check."""
    out = {}
    for k, v in evidence.items():
        items = v.items() if isinstance(v, dict) else [(None, v)]
        for sub, x in items:
            if isinstance(x, np.ndarray):
                out[k if sub is None else f"{k}.{sub}"] = array_sha256(np.asarray(x))
    return out


def _vote(e, grouping):
    return {"test": e["test"], "family": _family_of(e, grouping, False), "strength": e["strength"],
            "sign": e.get("sign"), "units": e.get("units"), "units_voting": e.get("units_voting"),
            "units_agreeing": e.get("units_agreeing"),
            "half_cycle": ((e.get("stats") or {}).get("half_cycle") or {}).get("result"),
            "reason": e.get("reason") or ""}


def _documentation_log(items, policy_log):
    out = []
    for channel, sign, citation, cid in items:
        hit = next((e for e in policy_log if (e["channel"], e["sign"], e["citation_id"]) == (channel, sign, cid)),
                   None)
        out.append({"channel": channel, "sign": sign, "citation": citation, "citation_id": cid,
                    "action": hit["action"] if hit else "kept",
                    "refuted_by_task": hit.get("refuted_by_task") if hit else None,
                    "reason": hit["summary"] if hit else "kept: no refutation entry for this citation"})
    return out


def run_sign_application(*, dataset, leg, group_id, recording, unit_ids, channels, detector_sha256,
                         source_columns=None, documentation=(), evidence=None,
                         mode="pilot", pilot_record_path=None, repo_root=ROOT,
                         detector_path=DETECTOR_PATH, policy_path=POLICY_PATH, refuted_path=REFUTED_PATH,
                         audited_path=AUDITED_PATH, backlog_path=BACKLOG_PATH):
    """Run the bound detector on one group and apply the publication rule.

    dataset: the dataset key (e.g. "GT24") used by the documentation policy and the audited-sign table;
    adapters never pass signs. recording: the source recording id (must match the table's
    recording_id_pattern for the dataset; per-recording exceptions match it exactly).
    group_id: the adapter's identity of the group; unit_ids: one identity per unit (row), in order.
    channels: logical detector name -> untransformed plain float64 numpy array (units, samples).
    documentation: (channel, sign, citation, citation_id). evidence: detect_leg keyword arguments.
    mode "full" needs a committed pilot record (pilot_record_path) of a done CORE-11-P-<dataset> task.
    """
    det = load_bound_detector(detector_sha256, detector_path)  # refuses an undeclared or unknown build
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    policy, policy_sha = _load_policy(policy_path)
    table_bytes = Path(refuted_path).read_bytes()  # the one read of the refuted table
    audited_bytes = Path(audited_path).read_bytes()  # the one read of the audited-sign table
    backlog_bytes = Path(backlog_path).read_bytes()  # the one read of the backlog (not in the build)
    build = {_rel(detector_path): detector_sha256, _rel(HOOK_PATH): HOOK_SHA256,
             _rel(policy_path): policy_sha, _rel(refuted_path): hashlib.sha256(table_bytes).hexdigest(),
             _rel(audited_path): hashlib.sha256(audited_bytes).hexdigest()}
    backlog = json.loads(backlog_bytes)
    records = {t.get("id"): t for t in backlog.get("tasks", [])}
    decisions = {d.get("id"): d for d in backlog.get("decisions", [])}
    with tempfile.TemporaryDirectory() as tmp:  # the policy reads our single copies
        tmp = Path(tmp)
        (tmp / "refuted_documentation.json").write_bytes(table_bytes)
        (tmp / "backlog.json").write_bytes(backlog_bytes)
        task_done = lambda task: policy.task_done(task, tmp / "backlog.json")
        pilot = None
        if mode == "full":
            rec, facts = check_pilot_record(pilot_record_path, dataset, build, task_done, records, repo_root)
            pilot = {**facts, "pilot_task": rec["pilot_task"]}
        audits, exceptions, pattern = load_audited_signs(dataset, json.loads(audited_bytes), records, task_done,
                                                         decisions)
        items = [tuple(i) for i in documentation]
        kept, policy_log = policy.split_documentation(dataset, items, path=tmp / "refuted_documentation.json",
                                                      backlog_path=tmp / "backlog.json")
    if not isinstance(recording, str) or not re.fullmatch(pattern, recording):
        raise ValueError(f"recording {recording!r} does not match the {dataset} recording id pattern {pattern!r}")
    evidence = dict(evidence or {})
    bad = sorted(set(evidence) - EVIDENCE_KEYS)
    if bad:
        raise ValueError(f"evidence keys not accepted: {bad} (parameters are the bound build's DEFAULTS; "
                         "documentation goes through the documentation argument)")
    unit_ids = [str(u) for u in unit_ids]
    if not unit_ids or len(set(unit_ids)) != len(unit_ids):
        raise ValueError("unit_ids must be non-empty and distinct")
    src = {}
    for k, a in channels.items():
        if type(a) is not np.ndarray:  # masked arrays, matrices and other subclasses carry state np.asarray drops
            raise ValueError(f"{k}: need a plain numpy.ndarray, got {type(a).__name__} (unmask explicitly: "
                             "missing samples are NaN)")
        if a.dtype != np.dtype("<f8") or a.ndim != 2 or a.shape[0] != len(unit_ids):
            raise ValueError(f"{k}: need a little-endian float64 (units, samples) array with {len(unit_ids)} "
                             f"units (do not downcast); got {a.dtype} {a.shape}")
        src[k] = a
    in_hash = {k: array_sha256(a) for k, a in src.items()}
    ev_hash = _evidence_hashes(evidence)
    held_by, corrected, not_released = _recording_exceptions(exceptions, recording)
    # An active correction fixes a proved source error first (exact negation): the detector, the guard
    # and the publication rule then see the channel as every other recording stores it.
    # Velocities and channels an exception does not release are never sign-applied: held, not detected.
    for k in src:
        if k.endswith(VELOCITY_SUFFIX) and k not in held_by:
            held_by[k] = (None, "angular velocities are not sign-applied by the hook; recompute after the hook "
                                "with derive_angular_velocities from the published or derived angle")
    not_detected = {k for k in src if k.endswith(VELOCITY_SUFFIX) or k in not_released}
    det_src = {k: (np.negative(a) if k in corrected else a) for k, a in src.items() if k not in not_detected}

    report = det.detect_leg(f"{dataset} {group_id}", leg, det_src, documentation=kept,
                            source_columns=source_columns, **evidence)
    params = report["parameters"]
    min_families, grouping = params["min_families"], params["family_grouping"]

    out, log_channels, review = {}, {}, []
    for k, a in src.items():
        c = report["channels"][k] if k not in not_detected else {
            "verdict": "not_run", "sign": None, "confidence": None, "families": [], "evidence": [],
            "reason": "held before detection (velocity or not-released channel)"}
        detector_applied, guard = False, None
        if c["verdict"] == "apply":
            detector_applied, guard = guard_apply(c, min_families, grouping)
            if not detector_applied:
                review.append({"kind": "guard_refused", "channel": k, "detector_sign": c["sign"],
                               "reason": f"detector said apply; hook guard refused: {guard}"})
        entry = audits.get(k)
        audit = ({x: entry.get(x) for x in ("id", "sign", "audit_tasks", "evidence_basis", "citation", "verified",
                                            "reason")}
                 if entry else None)
        audit_sign = entry["sign"] if entry and entry["verified"] else None
        correction = None
        if k in held_by:  # per-recording exception: applied before any sign
            mult, basis, publication, hold = 1, "none", "hold", held_by[k][1]
        else:
            mult, basis, publication, hold = publication_rule(c["verdict"], c.get("sign"), detector_applied,
                                                              audit_sign)
        sign_vs_corrected = mult  # the sign relative to the (corrected) source, comparable across recordings
        if k in corrected:
            x = corrected[k]
            factor = x["corrections"][k]
            applied = publication == "publish"
            if applied:
                mult = mult * factor  # net multiplier on the stored array; still exactly +1 or -1
            else:
                sign_vs_corrected = 1  # a held channel is returned as stored, uncorrected
            correction = {"id": x["id"], "factor": factor, "applied": applied,
                          "decision": x["decision"], "audit_tasks": x["audit_tasks"],
                          "evidence_basis": x["evidence_basis"], "citation": x["citation"],
                          "active_reason": x["active_reason"], "derived_channels": x["derived_channels"]}
            if applied:
                review.append({"kind": "correction", "channel": k, "exception": x["id"], "factor": factor,
                               "decision": x["decision"], "net_multiplier": mult,
                               "recompute": x["derived_channels"]})
        out[k] = np.negative(a) if mult == -1 else a.copy()  # exact; each its own inverse
        off = c.get("offset") or {}
        log_channels[k] = {
            "source_column": (source_columns or {}).get(k), "dtype": a.dtype.str, "shape": list(a.shape),
            "verdict": c["verdict"], "detector_sign": c.get("sign"), "confidence": c.get("confidence"),
            "reason": c.get("reason"), "families": c.get("families") or [], "weak_hint": c.get("weak_hint"),
            "detector_applied": detector_applied, "guard": guard, "audit": audit,
            "multiplier": mult, "sign_basis": basis, "publication": publication, "hold_reason": hold,
            "source_correction": correction, "sign_vs_corrected_source": sign_vs_corrected,
            "votes": [_vote(e, grouping) for e in c["evidence"]],
            "offset": {"estimate": off.get("estimate"), "ci95": off.get("ci95"),
                       "flag_for_review": bool(off.get("flag_for_review")), "applied": False,
                       "reference": off.get("reference") or off.get("reason")},
            "input_sha256": in_hash[k], "output_sha256": array_sha256(out[k])}
        if publication == "hold":
            review.append({"kind": "hold", "channel": k, "source_column": log_channels[k]["source_column"],
                           "reason": hold, "audit_sign": audit_sign, "detector_sign": c.get("sign"),
                           "verdict": c["verdict"]})
        if c["verdict"] in REVIEW_VERDICTS:
            review.append({"kind": c["verdict"], "channel": k, "source_column": log_channels[k]["source_column"],
                           "detector_sign": c.get("sign"), "confidence": c.get("confidence"),
                           "families": c.get("families") or [], "weak_hint": c.get("weak_hint"),
                           "reason": c.get("reason"),
                           "decided_tests": [f"{e['test']} {e['sign']:+d}" for e in c["evidence"]
                                             if e.get("sign") is not None]})
        if off.get("estimate") is not None:
            review.append({"kind": "offset", "channel": k, "estimate_rad": off.get("estimate"),
                           "ci95": off.get("ci95"), "flag_for_review": bool(off.get("flag_for_review")),
                           "reference": off.get("reference"), "applied": False})
    if {k: array_sha256(a) for k, a in src.items()} != in_hash:
        raise RuntimeError("an input channel changed during sign application")
    if _evidence_hashes(evidence) != ev_hash:
        raise RuntimeError("an evidence array changed during sign application")

    chans = log_channels.values()
    log = {
        "schema_version": SCHEMA_VERSION, "task": "CORE-11", "scientific_approval": False, "mode": mode,
        "dataset": dataset, "leg": leg, "group_id": group_id, "recording": recording, "unit_ids": unit_ids,
        "target_rule": report["target_convention"]["rule_id"],
        "detector": {"path": _rel(detector_path), "sha256": detector_sha256,
                     "schema_version": report["schema_version"], "parameters": params},
        "bound_build": build, "pilot": pilot,
        "rules": {"detector_apply": "verdict apply and the hook guard (own family table): agreeing "
                                    "moderate/strong tests from >= 2 families, no moderate/strong or "
                                    "documentation dissent",
                  "publication": PUBLICATION_POLICY,
                  "offsets": "never applied; listed for review",
                  "documentation": "never applies a sign; statements refuted by a done task are withheld",
                  "other_changes": "none: output = multiplier x input, exactly",
                  "held_channels": "returned in the source convention; never written under a rule-B name",
                  "corrections": "an active per-recording correction (audit tasks done and citing it, decision "
                                 "answered as recorded) negates the stored channel before detection; the "
                                 "multiplier is the net sign on the stored array; derived segment angles of that "
                                 "recording are held as inputs and recomputed by derive_segment_angles; their "
                                 "velocities and the corrected channel's velocity are held and recomputed by "
                                 "derive_angular_velocities (or left out); not-released channels are held",
                  "velocities": "any <angle>_velocity input is held and not detected; recompute after the hook"},
        "documentation": _documentation_log(items, policy_log),
        "exceptions_applied": [{x: (held_by[c][0] or {}).get(x) for x in ("id", "action", "audit_tasks", "pending_decision",
                                                                     "linked")}
                               | {"channel": c, "reason": held_by[c][1]} for c in sorted(held_by)
                               if c in src and held_by[c][0] is not None],
        "corrections_applied": [{"id": log_channels[c]["source_correction"]["id"], "channel": c,
                                 "factor": log_channels[c]["source_correction"]["factor"],
                                 "decision": log_channels[c]["source_correction"]["decision"],
                                 "audit_tasks": log_channels[c]["source_correction"]["audit_tasks"],
                                 "net_multiplier": log_channels[c]["multiplier"]}
                                for c in sorted(corrected) if c in src
                                and log_channels[c]["source_correction"]["applied"]],
        "recording_exceptions": [{"id": x["id"], "action": x["action"],
                                  "active": x.get("active"), "active_reason": x.get("active_reason"),
                                  "derived_channels": x.get("derived_channels"),
                                  "derived_velocities": x.get("derived_velocities"),
                                  "not_released": x.get("not_released")}
                                 for x in exceptions if recording in x["recordings"]],
        "checks": {k: report.get(k) for k in ("marker_checks", "plate_frame_check", "grf_unit_check",
                                              "leg_assignment_check", "cop_registration")},
        "evidence_sha256": ev_hash,
        "relations": [{x: r.get(x) for x in ("test", "channels", "product", "units_voting", "units_agreeing")}
                      for r in report["relations"]],
        "channels": log_channels,
        "counts": {**{v: sum(c["verdict"] == v for c in chans) for v in ("apply", "suggest", "conflict", "abstain")},
                   "detector_applied": sum(c["detector_applied"] for c in chans),
                   "corrected": sum(bool((c["source_correction"] or {}).get("applied")) for c in chans),
                   "guard_refused": sum(i["kind"] == "guard_refused" for i in review),
                   "published": sum(c["publication"] == "publish" for c in chans),
                   "held": sum(c["publication"] == "hold" for c in chans),
                   **{f"basis_{b}": sum(c["sign_basis"] == b for c in chans)
                      for b in ("audit_and_detector", "audit", "detector")}},
        "undo": "multiply each channel by its multiplier (+1 or -1, each its own inverse); the log's sha256 "
                "(from the manifest) authenticates the log, output_sha256 must match before undo and "
                "input_sha256 after; a per-recording correction is part of the multiplier, so undo "
                "returns the stored (uncorrected) array",
    }
    return SignApplication(out, _finite(log), _finite(review), report)


# ---------------------------------------------------------------- undo, consistency, files
def undo_sign_application(channels, log, expected_log_sha256=None):
    """Restore the untransformed input from signed arrays and their log, verifying both hashes.

    log: the log dict, or the path of the written log. With expected_log_sha256 (from the manifest),
    log must be a path and its bytes must hash to that value; a consistently edited log is refused.
    """
    if expected_log_sha256 is not None:
        if not isinstance(log, (str, Path)):
            raise UndoError("expected_log_sha256 needs the log file path, not a parsed dict")
        data = Path(log).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected_log_sha256:
            raise UndoError("log file does not match the sha256 recorded in the manifest")
        log = json.loads(data)
    elif isinstance(log, (str, Path)):
        log = json.loads(Path(log).read_bytes())
    restored = {}
    for k, c in log["channels"].items():
        if k not in channels:
            raise UndoError(f"{k}: missing from the arrays offered for undo")
        a = np.asarray(channels[k])
        if array_sha256(a) != c["output_sha256"]:
            raise UndoError(f"{k}: array is not the logged output (hash mismatch)")
        if c["multiplier"] not in (1, -1):
            raise UndoError(f"{k}: multiplier {c['multiplier']!r} is not +1 or -1")
        r = np.negative(a) if c["multiplier"] == -1 else a.copy()
        if array_sha256(r) != c["input_sha256"]:
            raise UndoError(f"{k}: undo did not reproduce the logged input")
        restored[k] = r
    return restored


def cross_group_review(logs):
    """Review items for channels whose published sign differs between groups of one dataset (mixed
    storage, e.g. UM21 power layouts or a reversed pelvis in one recording), or that are published in
    some groups and held in others."""
    seen = {}
    for lg in logs:
        for k, c in lg["channels"].items():
            seen.setdefault((lg["dataset"], k), []).append((lg["group_id"], lg["leg"], c))
    items = []
    for (ds, k), rows in sorted(seen.items()):
        # compare signs against the corrected source: a logged per-recording correction is not mixed storage
        signs = sorted({c.get("sign_vs_corrected_source", c["multiplier"]) for _, _, c in rows
                        if c["publication"] == "publish"})
        held = [f"{g} {leg}" for g, leg, c in rows if c["publication"] == "hold"]
        if len(signs) > 1 or (signs and held):
            items.append({"kind": "inconsistent_across_groups", "dataset": ds, "channel": k,
                          "published_signs": {f"{g} {leg}": c["multiplier"] for g, leg, c in rows
                                              if c["publication"] == "publish"},
                          "held": held})
    return items


def derive_segment_angles(application):
    """Rule-B segment angles from the published channels of one SignApplication, along the hook's
    SEGMENT_CHAIN (thigh = pelvis + hip, shank = thigh - knee, foot = shank + ankle).

    Use this for datasets whose segment angles are derived (UM21) so that a per-recording correction of
    the pelvis reaches thigh, shank and foot: the inputs are the hook's outputs, never the stored arrays.
    A segment is derived only when its proximal segment and joint are both available (published, or
    derived here); otherwise it is left out with the reason. Returns (segments, log); the log records the
    formula and the output_sha256 of every input, so it can be checked against the sign-application log.
    """
    chans, log_ch = application.channels, application.log["channels"]
    # segment angles passed to the hook are never used: every segment comes from the chain
    available = {k: chans[k] for k, c in log_ch.items() if c["publication"] == "publish" and k not in SEGMENT_CHANNELS}
    out, derivation, missing = {}, {}, {}
    for distal, proximal, joint, ccw in SEGMENT_CHAIN:
        absent = [n for n in (proximal, joint) if n not in available]
        if absent:
            def why(n):
                if n in SEGMENT_CHANNELS:
                    return f"{n} (not derived)"
                return f"{n} ({log_ch[n]['publication']})" if n in log_ch else f"{n} (not passed)"
            missing[distal] = "unavailable: " + ", ".join(why(n) for n in absent)
            continue
        q, j = available[proximal], available[joint]
        out[distal] = q + j if ccw == 1 else q - j
        available[distal] = out[distal]
        derivation[distal] = {"formula": f"{distal} = {proximal} {'+' if ccw == 1 else '-'} {joint}",
                              "inputs_sha256": {n: array_sha256(available[n]) for n in (proximal, joint)},
                              "output_sha256": array_sha256(out[distal])}
    corrections = [{"id": c["source_correction"]["id"], "channel": k}
                   for k, c in log_ch.items() if (c.get("source_correction") or {}).get("applied")]
    return out, {"rule": "B segment chain (SEGMENT_CHAIN)", "recording": application.log["recording"],
                 "leg": application.log["leg"], "group_id": application.log["group_id"],
                 "derived": derivation, "not_derived": missing, "from_corrected_channels": corrections}


VELOCITY_METHOD = ("per unit (row): numpy.gradient(angle, spacing_s, edge_order=1), i.e. central differences "
                   "(a[i+1] - a[i-1]) / (2 h) inside and one-sided differences (a[1] - a[0]) / h, "
                   "(a[-1] - a[-2]) / h at the ends, as MATLAB gradient(angle, h) in the UM21 converters "
                   "(convert_umich_time_to_parquet.m: h = 1 / sampling_rate_hz; convert_umich_phase_to_parquet.m: "
                   "gradient(angle) * effective_Hz with effective_Hz = (150 - 1) / stride_duration_s, i.e. "
                   "h = stride_duration_s / 149 per stride); equal to MATLAB up to floating-point rounding; NaN "
                   "samples propagate to their neighbours")


def derive_angular_velocities(angles, spacing_s):
    """Angular velocities of published or derived angles, recomputed after the hook (VELOCITY_METHOD).

    angles: name -> float64 (units, samples) array, taken from SignApplication.channels of published
    channels or from derive_segment_angles; never the stored arrays. spacing_s: the sample spacing in
    seconds, one positive number (time series) or one per unit (phase-normalized strides,
    stride_duration_s / 149). Returns ({name + '_velocity': array}, log).
    """
    out, log = {}, {}
    for name, a in angles.items():
        if type(a) is not np.ndarray or a.dtype != np.dtype("<f8") or a.ndim != 2 or a.shape[1] < 2:
            raise ValueError(f"{name}: need a float64 (units, samples) array with at least 2 samples")
        h = np.broadcast_to(np.asarray(spacing_s, dtype=float), (a.shape[0],))
        if not np.all(np.isfinite(h)) or np.any(h <= 0):
            raise ValueError(f"{name}: spacing_s must be positive and finite (one value, or one per unit)")
        v = np.stack([np.gradient(a[u], h[u], edge_order=1) for u in range(a.shape[0])])
        out[name + VELOCITY_SUFFIX] = v
        log[name + VELOCITY_SUFFIX] = {"from": name, "input_sha256": array_sha256(a),
                                       "output_sha256": array_sha256(v)}
    return out, {"method": VELOCITY_METHOD, "spacing_s": np.asarray(spacing_s, dtype=float).tolist(),
                 "derived": log}


def write_json_exclusive(path, obj):
    """Write JSON to a new file; never overwrite an existing log. Returns its sha256 for the manifest."""
    with Path(path).open("x", encoding="utf-8") as f:
        f.write(json.dumps(obj, indent=1, allow_nan=False) + "\n")
    return file_sha256(path)
