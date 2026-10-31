"""Independent CORE-05 verifier checks of the no-replace publication fallback.

Synthetic only: small text artifacts sealed by a manifest the way the builder
seals them, plus one two-observation synthetic export for end-to-end builds.
Each filesystem case runs on pytest's Linux tmp path and on a temporary
directory on the WSL drvfs mount that holds the repository (removed after each
test). Tests marked ``xfail(strict=True)`` pin verifier-found gaps.
"""

import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd
import pytest

from contributor_tools import build_dataset_release as release


MARKER = "RELEASE_INCOMPLETE.txt"
KNEE = "knee_flexion_angle_ipsi_rad"
REPO = Path(__file__).resolve().parents[1]


def _mount_type(path: Path) -> str:
    best, kind = "", ""
    for line in Path("/proc/mounts").read_text().splitlines():
        fields = line.split()
        mount = fields[1].replace("\\040", " ")
        if str(path).startswith(mount.rstrip("/") + "/") and len(mount) > len(best):
            best, kind = mount, f"{fields[2]} {fields[3]}"
    return kind


ON_DRVFS = "drvfs" in _mount_type(REPO)


@pytest.fixture(params=["linux", "drvfs"])
def where(request, tmp_path):
    if request.param == "linux":
        yield tmp_path
        return
    if not ON_DRVFS:
        pytest.skip("Repository is not on a drvfs mount.")
    directory = Path(tempfile.mkdtemp(prefix=".core05-verify-", dir=REPO.parent))
    try:
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sealed_stage(parent: Path) -> Path:
    stage = parent / ".bundle.staging-verify"
    stage.mkdir()
    artifacts = {"data.bin": b"synthetic data\n" * 3, "notes.txt": b"synthetic notes\n"}
    for name, data in artifacts.items():
        (stage / name).write_bytes(data)
    manifest = json.dumps({"artifacts": {n: {"sha256": _digest(d)} for n, d in artifacts.items()}}).encode()
    (stage / "manifest.json").write_bytes(manifest)
    (stage / "manifest.sha256").write_text(f"{_digest(manifest)}  manifest.json\n")
    return stage


def _bundle_verifies(bundle: Path) -> bool:
    """What a careful reader would check, ignoring the marker."""
    try:
        seal = (bundle / "manifest.sha256").read_text().split()[0]
        if release.sha256_file(bundle / "manifest.json") != seal:
            return False
        artifacts = json.loads((bundle / "manifest.json").read_text())["artifacts"]
        return all(release.sha256_file(bundle / n) == a["sha256"] for n, a in artifacts.items())
    except (OSError, ValueError, KeyError):
        return False


def _inputs(directory: Path):
    grid = np.linspace(0, 100, 150)
    data = pd.concat([pd.DataFrame({
        "subject": "V1", "source_recording_id": "r", "observation_id": name,
        "reference_side": "left", "observation_type": "individual_cycle",
        "task": "level_walking", "task_id": "lw", "task_info": '{"population": "synthetic"}',
        "phase_ipsi": grid, KNEE: np.full(150, level)}) for name, level in (("in", 0.5), ("out", 2.0))])
    source = directory / "export.parquet"
    data.to_parquet(source, index=False)
    raw = directory / "raw.bin"
    raw.write_bytes(b"synthetic")
    profile = directory / "p.yaml"
    profile.write_text("review_status: reviewed\n"
                       "review:\n  reviewer: synthetic-profile-reviewer\n  reviewed_at: '2026-01-02T00:00:00Z'\n"  # synthetic profile review record
                       "tasks:\n  level_walking:\n"
                       "    metadata:\n      applicability:\n        population: [synthetic]\n    phases:\n"
                       f"      0:\n        {KNEE}: {{min: 0, max: 1}}\n      100:\n        {KNEE}: {{min: 0, max: 1}}\n")
    provenance = directory / "prov.json"
    provenance.write_text(json.dumps({
        "dataset_id": "verify-core05", "release_id": "v1",
        "sources": [{"uri": "raw.bin", "path": "raw.bin", "sha256": release.sha256_file(raw)}],
        "converter": {"name": "verifier", "revision": "1"},
        "review": {"reviewer": "verifier", "reviewed_at": "2026-10-31T00:00:00Z"}}))
    return source, provenance, profile


# --- which path runs --------------------------------------------------------

def test_linux_filesystem_never_uses_the_fallback(tmp_path, monkeypatch):
    def forbidden(stage, destination):
        raise AssertionError("fallback used on a filesystem with RENAME_NOREPLACE")

    monkeypatch.setattr(release, "_publish_files_exclusively", forbidden)
    source, provenance, profile = _inputs(tmp_path)
    release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert not (tmp_path / "rel" / MARKER).exists()


@pytest.mark.skipif(not ON_DRVFS, reason="Repository is not on a drvfs mount.")
def test_drvfs_build_uses_fallback_and_ends_unmarked_and_sealed(monkeypatch):
    calls = []
    original = release._publish_files_exclusively
    monkeypatch.setattr(release, "_publish_files_exclusively",
                        lambda s, d: (calls.append(d), original(s, d))[1])
    directory = Path(tempfile.mkdtemp(prefix=".core05-verify-", dir=REPO.parent))
    try:
        source, provenance, profile = _inputs(directory)
        manifest = release.build_release(source, directory / "rel", provenance, ranges_path=profile)
        assert calls == [directory / "rel"]
        names = {p.name for p in (directory / "rel").iterdir()}
        assert names == set(manifest["artifacts"]) | {"manifest.json", "manifest.sha256"}
        assert _bundle_verifies(directory / "rel")
        assert [p.name for p in directory.iterdir() if p.name.startswith(".")] == []
    finally:
        shutil.rmtree(directory, ignore_errors=True)


@pytest.mark.parametrize("code", [errno.EEXIST, errno.EACCES, errno.EXDEV, errno.ENOTEMPTY])
def test_other_rename_errors_never_fall_back(where, monkeypatch, code):
    stage = _sealed_stage(where)

    def rename(stage, destination):
        raise OSError(code, os.strerror(code), str(destination))

    monkeypatch.setattr(release, "_rename_noreplace", rename)
    with pytest.raises(OSError) as raised:
        release._publish_directory(stage, where / "rel")
    assert raised.value.errno == code
    assert not (where / "rel").exists() and len(list(stage.iterdir())) == 4


# --- races and symlinks -------------------------------------------------------

def test_directory_created_between_rename_failure_and_mkdir_is_untouched(where, monkeypatch):
    stage = _sealed_stage(where)

    def rename_loses_race(stage, destination):
        destination.mkdir()
        (destination / "theirs.txt").write_text("foreign")
        raise OSError(errno.EINVAL, "simulated drvfs", str(destination))

    monkeypatch.setattr(release, "_rename_noreplace", rename_loses_race)
    with pytest.raises(FileExistsError):
        release._publish_directory(stage, where / "rel")
    assert [p.name for p in (where / "rel").iterdir()] == ["theirs.txt"]
    assert (where / "rel" / "theirs.txt").read_text() == "foreign"


@pytest.mark.parametrize("planted", ["file", "symlink"])
def test_entry_planted_at_a_later_name_is_kept_and_bundle_stays_marked(where, monkeypatch, planted):
    stage = _sealed_stage(where)
    outside = where / "outside.txt"
    outside.write_text("outside")
    destination = where / "rel"
    original = release._place_exclusively

    def place_then_race(source, target):
        original(source, target)
        if target.name == "data.bin":  # first placed; manifest files come later
            foreign = destination / "manifest.json"
            if planted == "file":
                foreign.write_text("{}")
            else:
                foreign.symlink_to(outside)

    monkeypatch.setattr(release, "_place_exclusively", place_then_race)
    with pytest.raises(FileExistsError):
        release._publish_files_exclusively(stage, destination)
    assert {p.name for p in destination.iterdir()} == {MARKER, "manifest.json"}
    assert outside.read_text() == "outside"
    assert not _bundle_verifies(destination)


def test_symlink_destination_on_build_is_refused_without_writing_through(where):
    source, provenance, profile = _inputs(where)
    target = where / "elsewhere"
    target.mkdir()
    (where / "rel").symlink_to(target)
    with pytest.raises(release.ReleaseError):
        release.build_release(source, where / "rel", provenance, ranges_path=profile)
    assert not list(target.iterdir())


# --- hard links ---------------------------------------------------------------

def test_staged_file_mutated_after_linking_is_caught_before_completion(where, monkeypatch):
    stage = _sealed_stage(where)
    destination = where / "rel"
    original = release._place_exclusively

    def place_then_mutate(source, target):
        original(source, target)
        if target.name == "data.bin":
            with open(source, "ab") as handle:  # same inode when hard-linked
                handle.write(b"tampered")

    monkeypatch.setattr(release, "_place_exclusively", place_then_mutate)
    with pytest.raises(release.ReleaseError, match="does not match"):
        release._publish_files_exclusively(stage, destination)
    assert not destination.exists() or (destination / MARKER).exists()


def test_left_over_staging_names_cannot_change_a_published_release(where, monkeypatch):
    stage = _sealed_stage(where)
    destination = where / "rel"
    monkeypatch.setattr(release.shutil, "rmtree", lambda *args, **kwargs: None)  # cleanup fails silently
    release._publish_files_exclusively(stage, destination)
    assert stage.exists() and _bundle_verifies(destination)
    with open(stage / "data.bin", "ab") as handle:
        handle.write(b"later edit of residue")
    assert _bundle_verifies(destination)


def test_staged_symlink_is_refused_as_not_a_regular_file(where):
    stage = _sealed_stage(where)
    outside = where / "outside.bin"
    shutil.move(stage / "data.bin", outside)
    (stage / "data.bin").symlink_to(outside)
    with pytest.raises(release.ReleaseError, match="regular files"):
        release._publish_files_exclusively(stage, where / "rel")


# --- rollback, markers, locks -------------------------------------------------

def test_failing_rollback_unlink_leaves_the_marker(where, monkeypatch):
    stage = _sealed_stage(where)
    destination = where / "rel"
    original_place = release._place_exclusively
    original_unlink = Path.unlink

    def place_then_mutate(source, target):
        original_place(source, target)
        if target.name == "manifest.sha256":
            with open(source, "ab") as handle:
                handle.write(b"x")

    def unlink(self, missing_ok=False):
        if self.parent == destination and self.name == "notes.txt":
            raise PermissionError(errno.EACCES, "simulated busy file", str(self))
        return original_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(release, "_place_exclusively", place_then_mutate)
    monkeypatch.setattr(Path, "unlink", unlink)
    with pytest.raises(PermissionError):
        release._publish_files_exclusively(stage, destination)
    monkeypatch.undo()
    assert (destination / MARKER).exists()
    assert not _bundle_verifies(destination)


def test_failing_rollback_rmdir_leaves_no_usable_bundle(where, monkeypatch):
    stage = _sealed_stage(where)
    destination = where / "rel"
    original_place = release._place_exclusively

    def place_then_mutate(source, target):
        original_place(source, target)
        if target.name == "notes.txt":
            with open(source, "ab") as handle:
                handle.write(b"x")

    def rmdir(self):
        raise OSError(errno.EBUSY, "simulated busy directory", str(self))

    monkeypatch.setattr(release, "_place_exclusively", place_then_mutate)
    monkeypatch.setattr(Path, "rmdir", rmdir)
    with pytest.raises(release.ReleaseError):
        release._publish_files_exclusively(stage, destination)
    monkeypatch.undo()
    # The directory may remain, but empty: nothing a reader could load.
    assert not destination.exists() or not list(destination.iterdir())


def test_marked_directory_from_another_run_blocks_the_build(where):
    source, provenance, profile = _inputs(where)
    (where / "rel").mkdir()
    (where / "rel" / MARKER).write_text("left by an interrupted run")
    with pytest.raises(release.ReleaseError, match="overwritten"):
        release.build_release(source, where / "rel", provenance, ranges_path=profile)
    assert [p.name for p in (where / "rel").iterdir()] == [MARKER]


def test_held_lock_blocks_the_build_and_is_left_for_its_owner(where):
    source, provenance, profile = _inputs(where)
    lock = where / ".rel.release.lock"
    lock.write_text("owner")
    with pytest.raises(release.ReleaseError, match="lock"):
        release.build_release(source, where / "rel", provenance, ranges_path=profile)
    assert lock.read_text() == "owner" and not (where / "rel").exists()


def test_kill_after_all_files_placed_still_leaves_the_marker(where):
    stage = _sealed_stage(where)
    destination = where / "rel"
    script = (
        "import os, sys\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(REPO)!r})\n"
        "from contributor_tools import build_dataset_release as r\n"
        "real = r.sha256_file\n"
        "def hashed(path):\n"
        "    if Path(path).parent == Path(sys.argv[2]):\n"
        "        os._exit(9)  # killed during final verification\n"
        "    return real(path)\n"
        "r.sha256_file = hashed\n"
        "r._publish_files_exclusively(Path(sys.argv[1]), Path(sys.argv[2]))\n"
    )
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    result = subprocess.run([sys.executable, "-c", script, str(stage), str(destination)], env=env, timeout=120)
    assert result.returncode == 9
    assert (destination / MARKER).exists()
    # Every file is present and sealed, so only the marker shows the run did not finish.
    assert _bundle_verifies(destination)
