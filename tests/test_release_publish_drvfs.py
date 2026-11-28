"""No-overwrite release publication on a Linux path and on the WSL drvfs mount (CORE-05).

All data are synthetic: two 150-sample observations with constant values, and
small text files standing in for a staged bundle. No research dataset is read.
The drvfs cases use a temporary directory next to the repository, removed after
each test, and are skipped when the repository is not on a drvfs mount.
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


SIGNAL = "knee_flexion_angle_ipsi_rad"
MARKER = "RELEASE_INCOMPLETE.txt"
MANIFEST_FILES = {"manifest.json", "manifest.sha256"}


def _drvfs_parent():
    """Writable directory beside the repository when the repository is on drvfs."""
    override = os.environ.get("LOCOHUB_DRVFS_TEST_DIR")
    if override:
        return Path(override)
    try:
        lines = Path("/proc/mounts").read_text().splitlines()
    except OSError:
        return None
    for line in lines:
        fields = line.split()
        if len(fields) < 4:
            continue
        mount = Path(fields[1].replace("\\040", " "))
        if fields[2] == "drvfs" or (fields[2] == "9p" and "aname=drvfs" in fields[3]):
            if release.ROOT == mount or mount in release.ROOT.parents:
                return release.ROOT.parent
    return None


@pytest.fixture(params=["linux_tmp", "drvfs"])
def base(request, tmp_path):
    if request.param == "linux_tmp":
        yield tmp_path
        return
    parent = _drvfs_parent()
    if parent is None:
        pytest.skip("The repository is not on a WSL drvfs mount.")
    directory = Path(tempfile.mkdtemp(prefix=".locohub-core05-test-", dir=parent))
    try:
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)
        assert not directory.exists()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stage(directory: Path) -> tuple[Path, dict[str, bytes]]:
    """A small staged bundle whose manifest seals its artifacts like the builder's."""
    stage = directory / ".bundle.staging-fixture"
    stage.mkdir()
    files = {"a.txt": b"synthetic artifact a\n", "b.txt": b"synthetic artifact b\n"}
    for name, data in files.items():
        (stage / name).write_bytes(data)
    manifest = json.dumps({"artifacts": {
        name: {"sha256": _sha(data), "size_bytes": len(data)} for name, data in files.items()
    }}).encode()
    files["manifest.json"] = manifest
    files["manifest.sha256"] = f"{_sha(manifest)}  manifest.json\n".encode()
    for name in MANIFEST_FILES:
        (stage / name).write_bytes(files[name])
    return stage, files


def _inputs(directory: Path):
    data = pd.DataFrame({
        "subject": "S01", "source_recording_id": "fixture.csv",
        "observation_id": np.repeat(["pass", "fail"], 150),
        "reference_side": "left", "observation_type": "individual_cycle",
        "task": "level_walking", "task_id": "level_1_m_s", "task_info": '{"population": "synthetic"}',  # synthetic label
        "phase_ipsi": np.tile(np.linspace(0, 100, 150), 2),
        SIGNAL: np.repeat([0.5, 2.0], 150),
    })
    raw = directory / "fixture.csv"
    data.to_csv(raw, index=False)
    source = directory / "input.parquet"
    data.to_parquet(source, index=False)
    profile = directory / "ranges.yaml"
    profile.write_text(
        # Synthetic applicability and profile review record; not a real population or reviewer.
        "review_status: reviewed\n"
        "review: {reviewer: synthetic-profile-reviewer, reviewed_at: '2026-01-02T00:00:00Z'}\n"
        "tasks:\n  level_walking:\n    metadata: {applicability: {population: [synthetic]}}\n    phases:\n"
        f"      0:\n        {SIGNAL}: {{min: 0, max: 1}}\n"
        f"      100:\n        {SIGNAL}: {{min: 0, max: 1}}\n"
    )
    provenance = directory / "provenance.json"
    provenance.write_text(json.dumps({
        "dataset_id": "synthetic-core05", "release_id": "fixture-v1",
        "sources": [{"uri": "fixture.csv", "path": "fixture.csv", "sha256": release.sha256_file(raw)}],
        "converter": {"name": "synthetic-converter", "revision": "fixture-rev"},
        "review": {"reviewer": "synthetic-fixture", "reviewed_at": "2026-01-01T00:00:00Z"},
    }))
    return source, profile, provenance


def _no_residue(directory: Path, name: str = "release") -> None:
    assert not list(directory.glob(f".{name}.staging-*"))
    assert not (directory / f".{name}.release.lock").exists()


def _force_fallback(monkeypatch):
    def unsupported(stage, destination):
        raise OSError(errno.EINVAL, "simulated drvfs RENAME_NOREPLACE rejection", str(destination))

    monkeypatch.setattr(release, "_rename_noreplace", unsupported)


def _spy_fallback(monkeypatch) -> list:
    calls = []
    original = release._publish_files_exclusively

    def spy(stage, destination):
        calls.append(destination)
        return original(stage, destination)

    monkeypatch.setattr(release, "_publish_files_exclusively", spy)
    return calls


# --- complete publication on each filesystem ------------------------------------

def test_release_publishes_complete_verified_bundle(base, monkeypatch):
    calls = _spy_fallback(monkeypatch)
    source, profile, provenance = _inputs(base)
    output = base / "release"
    manifest = release.build_release(source, output, provenance, ranges_path=profile)
    # G1: drvfs rejects the no-replace rename, so only drvfs uses the fallback.
    assert calls == ([output] if base.name.startswith(".locohub-core05-test-") else [])
    names = {path.name for path in output.iterdir()}
    assert names == set(manifest["artifacts"]) | MANIFEST_FILES
    for name, artifact in manifest["artifacts"].items():
        assert release.sha256_file(output / name) == artifact["sha256"]
        assert (output / name).stat().st_size == artifact["size_bytes"]
    seal = (output / "manifest.sha256").read_text().split()
    assert seal == [release.sha256_file(output / "manifest.json"), "manifest.json"]
    assert release.sha256_file(output / "full.parquet") == release.sha256_file(source)
    _no_residue(base)


def test_forced_fallback_publishes_through_the_builder(tmp_path, monkeypatch):
    _force_fallback(monkeypatch)
    calls = _spy_fallback(monkeypatch)
    source, profile, provenance = _inputs(tmp_path)
    manifest = release.build_release(source, tmp_path / "release", provenance, ranges_path=profile)
    assert calls == [tmp_path / "release"]
    assert {path.name for path in (tmp_path / "release").iterdir()} == set(manifest["artifacts"]) | MANIFEST_FILES
    _no_residue(tmp_path)


@pytest.mark.parametrize("links", ["hard_link", "exclusive_copy"])
def test_fallback_places_identical_bytes(base, monkeypatch, links):
    if links == "exclusive_copy":
        def no_links(source, target):
            raise OSError(errno.EPERM, "simulated filesystem without hard links")

        monkeypatch.setattr(release.os, "link", no_links)
    stage, files = _stage(base)
    destination = base / "bundle"
    release._publish_files_exclusively(stage, destination)
    assert {path.name: path.read_bytes() for path in destination.iterdir()} == files
    assert not stage.exists()


# --- existing destinations and races --------------------------------------------

@pytest.mark.parametrize("existing", ["empty_dir", "dir_with_file", "file"])
@pytest.mark.parametrize("publish", ["auto", "fallback"])
def test_existing_destination_is_never_touched(base, existing, publish):
    stage, files = _stage(base)
    destination = base / "bundle"
    if existing == "file":
        destination.write_text("someone else's file")
    else:
        destination.mkdir()
        if existing == "dir_with_file":
            (destination / "a.txt").write_text("someone else's release")
    before = (
        destination.read_text() if existing == "file"
        else {path.name: path.read_text() for path in destination.iterdir()}
    )
    publisher = release._publish_directory if publish == "auto" else release._publish_files_exclusively
    with pytest.raises(OSError):
        publisher(stage, destination)
    after = (
        destination.read_text() if existing == "file"
        else {path.name: path.read_text() for path in destination.iterdir()}
    )
    assert after == before
    assert {path.name: path.read_bytes() for path in stage.iterdir()} == files


def test_builder_refuses_destination_created_during_build(base, monkeypatch):
    source, profile, provenance = _inputs(base)
    output = base / "release"
    original = release._release_card

    def create_destination(*args):
        output.mkdir()
        (output / "README.md").write_text("concurrent writer")
        return original(*args)

    monkeypatch.setattr(release, "_release_card", create_destination)
    with pytest.raises(release.ReleaseError, match="already exists"):
        release.build_release(source, output, provenance, ranges_path=profile)
    assert [(path.name, path.read_text()) for path in output.iterdir()] == [("README.md", "concurrent writer")]
    _no_residue(base)


@pytest.mark.parametrize("links", ["hard_link", "exclusive_copy"])
def test_file_created_by_another_writer_is_not_replaced(base, monkeypatch, links):
    if links == "exclusive_copy":
        def no_links(source, target):
            raise OSError(errno.EPERM, "simulated filesystem without hard links")

        monkeypatch.setattr(release.os, "link", no_links)
    stage, _ = _stage(base)
    destination = base / "bundle"
    original = release._place_exclusively

    def race(source, target):
        if target.name == "b.txt":
            target.write_text("written by another process")
        return original(source, target)

    monkeypatch.setattr(release, "_place_exclusively", race)
    with pytest.raises(FileExistsError):
        release._publish_files_exclusively(stage, destination)
    # The foreign file survives, our placed file is removed, and the marker stays
    # because the directory now holds content this builder did not write.
    assert {path.name: path.read_text() for path in destination.iterdir()} == {
        "b.txt": "written by another process",
        MARKER: (destination / MARKER).read_text(),
    }
    assert "incomplete" in (destination / MARKER).read_text()


def test_unexpected_entry_blocks_completion(base, monkeypatch):
    stage, _ = _stage(base)
    destination = base / "bundle"
    original = release._place_exclusively

    def intrude(source, target):
        original(source, target)
        if target.name == "manifest.sha256":
            (destination / "extra.txt").write_text("foreign")

    monkeypatch.setattr(release, "_place_exclusively", intrude)
    with pytest.raises(release.ReleaseError, match="Unexpected entries"):
        release._publish_files_exclusively(stage, destination)
    assert sorted(path.name for path in destination.iterdir()) == sorted([MARKER, "extra.txt"])


# --- verification and interruption ------------------------------------------------

def test_staged_file_that_disagrees_with_manifest_is_not_published(base):
    stage, _ = _stage(base)
    (stage / "a.txt").write_bytes(b"changed after the manifest was sealed\n")
    with pytest.raises(release.ReleaseError, match="do not match their manifest"):
        release._publish_files_exclusively(stage, base / "bundle")
    assert not (base / "bundle").exists()


def test_published_hash_mismatch_rolls_back(base, monkeypatch):
    stage, _ = _stage(base)
    destination = base / "bundle"
    original = release._place_exclusively

    def corrupt(source, target):
        original(source, target)
        if target.name == "a.txt":
            # Break the hard link first so the staged copy keeps its bytes.
            data = target.read_bytes()
            target.unlink()
            target.write_bytes(data + b"corrupted")

    monkeypatch.setattr(release, "_place_exclusively", corrupt)
    with pytest.raises(release.ReleaseError, match="does not match"):
        release._publish_files_exclusively(stage, destination)
    assert not destination.exists()


def test_interrupted_fallback_build_leaves_nothing(base, monkeypatch):
    _force_fallback(monkeypatch)
    source, profile, provenance = _inputs(base)
    output = base / "release"
    original = release._place_exclusively
    placed = []

    def interrupt(source_file, target):
        if len(placed) == 3:
            raise KeyboardInterrupt
        original(source_file, target)
        placed.append(target.name)

    monkeypatch.setattr(release, "_place_exclusively", interrupt)
    with pytest.raises(KeyboardInterrupt):
        release.build_release(source, output, provenance, ranges_path=profile)
    assert len(placed) == 3
    assert not output.exists()
    _no_residue(base)


_HARD_KILL = """
import errno, os, sys
from pathlib import Path
from contributor_tools import build_dataset_release as release
if sys.argv[3] == "force":
    def unsupported(stage, destination):
        raise OSError(errno.EINVAL, "simulated", str(destination))
    release._rename_noreplace = unsupported
original = release._place_exclusively
count = []
def place_then_die(source, target):
    original(source, target)
    count.append(target)
    if len(count) == 2:
        os._exit(9)  # No cleanup runs, as after SIGKILL or power loss.
release._place_exclusively = place_then_die
release._publish_directory(Path(sys.argv[1]), Path(sys.argv[2]))
"""


def test_hard_interruption_leaves_a_marked_incomplete_bundle(base):
    stage, _ = _stage(base)
    destination = base / "bundle"
    force = "native" if base.name.startswith(".locohub-core05-test-") else "force"
    env = {**os.environ, "PYTHONPATH": str(release.ROOT), "OMP_NUM_THREADS": "1",
           "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    result = subprocess.run(
        [sys.executable, "-c", _HARD_KILL, str(stage), str(destination), force],
        env=env, cwd=release.ROOT, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 9, result.stderr
    names = {path.name for path in destination.iterdir()}
    assert names == {MARKER, "a.txt", "b.txt"}
    assert MANIFEST_FILES.isdisjoint(names)
    assert "Do not use it" in (destination / MARKER).read_text()
