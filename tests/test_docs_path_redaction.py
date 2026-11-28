"""Published documentation must not contain local absolute paths or user names.

docs/build.py redacts text copies at build time with bracketed tokens ([repo],
[source-root], [home], [local], [scratch]) and refuses binaries with a local path;
the committed files under docs/ (hash-bound audit records) are never changed.
The synthetic case uses made-up paths and the made-up user 'someone'. The
default real-site case scans only published-candidate text files that differ
from git HEAD (changed or untracked under docs/), without copying the site. The
full real-site build (about 481 MB copied to a temporary folder, every published
text file streamed) is opt-in with --run-integration.
"""
from __future__ import annotations

import getpass
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("static_docs_redaction", ROOT / "docs/build.py")
STATIC_DOCS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STATIC_DOCS)

LEAK = re.compile(
    r"/mnt/"                                   # WSL drive mounts
    r"|(?<![\w.:/-])/(?:home|Users)/\w"        # POSIX and macOS homes
    r"|(?<![A-Za-z0-9/])[A-Za-z]:(?:\\|/(?!/))"  # Windows drive paths, raw or JSON-escaped
    r"|\\wsl(?:\$|\.localhost)"                # WSL UNC paths
    r"|/tmp/claude-"                           # agent scratch folders
)
RAW_TAG = re.compile(r"<(?:repo|source-root|home|local|scratch)>")
PAGE = """<!doctype html><html lang="en"><head><title>Example</title></head>
<body><main><p>Read <a href="record.json">the record</a> from /mnt/s/locomotion_data/Example
and /home/someone/notes, see https://github.com/someone/LocoHub.</p></main></body></html>"""


def leaks(text: str, user: str) -> list[str]:
    found = [m.group(0) for m in LEAK.finditer(text)] + [m.group(0) for m in RAW_TAG.finditer(text)]
    without_public = re.sub(rf"github\.com/{re.escape(user)}\b", "", text)
    if re.search(rf"(?<![A-Za-z0-9]){re.escape(user)}(?![A-Za-z0-9])", without_public):
        found.append(user)
    return found


def test_build_redacts_every_local_root_form_and_leaves_sources_unchanged(tmp_path):
    source, output = tmp_path / "docs", tmp_path / "site"
    source.mkdir()
    (source / "index.html").write_text(PAGE, encoding="utf-8")
    values = {
        "mnt_source": "/mnt/s/locomotion_data/Example/a.zip",
        "repo": f"{STATIC_DOCS.REPO}/tools/x.py",
        "mnt_user": "/mnt/c/Users/someone/b.csv",
        "home": "/home/someone/c.txt",
        "mac": "/Users/someone/d.txt",
        "windows_user": "C:\\Users\\someone\\e.txt",
        "windows_source": "S:\\locomotion_data\\Example",
        "windows_other": "D:/data/f.csv",
        "wsl": "\\\\wsl$\\Ubuntu\\home\\someone\\g",
        "wsl_localhost": "\\\\wsl.localhost\\Ubuntu\\srv\\h",
        "file_url": "file:///C:/Users/someone/i.txt",
        "file_mnt": "file:///mnt/s/locomotion_data/j",
        "scratch": "/tmp/claude-1000/k/probe.py",
        "public": "https://github.com/jmontp/LocoHub",
    }
    record = json.dumps(values)          # Windows separators are JSON-escaped here
    (source / "record.json").write_text(record, encoding="utf-8")
    STATIC_DOCS.build(output, source)
    published = {p.name: p.read_text(encoding="utf-8") for p in output.rglob("*") if p.is_file()}
    for name, text in published.items():
        assert not leaks(text, "someone"), (name, leaks(text, "someone"))
    result = json.loads(published["record.json"])
    assert result["mnt_source"] == "[source-root]/Example/a.zip"
    assert result["repo"] == "[repo]/tools/x.py"
    assert result["mnt_user"] == result["mac"].replace("d.txt", "b.csv") == "[home]/b.csv"
    assert result["windows_user"] == "[home]\\e.txt" and result["file_url"] == "[home]/i.txt"
    assert result["windows_source"] == "[source-root]\\Example"
    assert result["wsl"] == "[home]\\g" and result["wsl_localhost"] == "[local]\\srv\\h"
    assert result["scratch"] == "[scratch]/k/probe.py" and result["file_mnt"] == "[source-root]/j"
    assert result["public"] == values["public"]
    assert "https://github.com/someone/LocoHub" in published["index.html"]
    assert (source / "record.json").read_text(encoding="utf-8") == record


def test_build_refuses_a_binary_asset_with_a_local_path(tmp_path):
    source, output = tmp_path / "docs", tmp_path / "site"
    source.mkdir()
    (source / "index.html").write_text(PAGE.replace("record.json", "image.png"), encoding="utf-8")
    (source / "image.png").write_bytes(b"\x89PNG\r\n/home/someone/secret")
    with pytest.raises(ValueError, match="local path"):
        STATIC_DOCS.build(output, source)


def changed_docs_files() -> set[Path]:
    """Files under docs/ that differ from HEAD or are untracked (empty set if git is unavailable)."""
    try:
        names = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", "docs"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git status unavailable")
    return {(ROOT / line[3:].strip().strip('"')).resolve() for line in names if line[3:].strip()}


def test_changed_published_text_files_redact_cleanly_without_copying_the_site():
    pages, assets = STATIC_DOCS.check_site()
    candidates = (set(pages) | assets) & changed_docs_files()
    user = getpass.getuser()
    found = {}
    for path in sorted(candidates):
        if path.suffix.lower() not in STATIC_DOCS.TEXT_SUFFIXES:
            continue
        hits = leaks(STATIC_DOCS.redact_paths(path.read_text(encoding="utf-8")), user)
        if hits:
            found[path.relative_to(ROOT).as_posix()] = sorted(set(hits))[:3]
    assert not found


@pytest.mark.integration
def test_real_site_build_publishes_no_local_path_user_name_or_raw_token(tmp_path):
    output = tmp_path / "site"
    user = getpass.getuser()
    found = {}
    try:
        STATIC_DOCS.build(output)
        for path in sorted(output.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in STATIC_DOCS.TEXT_SUFFIXES:
                continue
            hits = leaks(path.read_text(encoding="utf-8"), user)
            if hits:
                found[path.relative_to(output).as_posix()] = sorted(set(hits))[:3]
    finally:
        shutil.rmtree(output, ignore_errors=True)   # the full site copy is about 0.5 GB
    assert not found
