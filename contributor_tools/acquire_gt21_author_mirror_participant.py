#!/usr/bin/env python3
"""GT21-S02: acquire one participant from the authors' 2024 Dropbox copy (Camargo et al.).

One participant per invocation, for one guarded-launcher job. Without --run it
only checks the bound expected listing and prints the plan (no network).
With --run, in order:

1. Refuse if the output root or the receipt directory already exists, or if
   either sits inside the other, the active 16-participant source root or the
   version 1 recovery folder. The receipt directory is created first
   (exclusive) and holds every receipt; the output root holds only the ZIP.
2. Re-list the participant folder and refuse unless every path, byte size and
   modification time, and the folder link, equal the bound expected listing.
3. Refuse unless free disk >= 15 GiB reserve + listed bytes + ZIP allowance
   and Windows free memory >= 2816 MiB.
4. Create the output root (exclusive) and stream the folder ZIP (dl=1) with a
   1 MiB buffer, a 1 MiB/s ceiling, a byte ceiling from Content-Length, and a
   SHA-256 computed while writing. Disk, STOP file and deadline are checked
   every block, Windows memory every 15 s; fsync. The bytes stay
   <subject>.zip.partial while steps 5-7 run on them.
5. Read the ZIP central directory only and require: no duplicate, unsafe,
   symlink, encrypted or unsupported members; member paths equal the listing; each
   uncompressed size equals its listed bytes; the GT21 layout (one session,
   osimxml with an .osim model, the 12 channel folders in each of the four
   modes with equal counts, ik_offset in every mode, static/ik, static/ik_offset
   and static/markers).
6. Stream every member through zipfile in 1 MiB blocks (nothing is
   extracted, nothing is decoded) and record bytes, CRC32 (recomputed and equal
   to the central directory) and SHA-256.
7. Re-list the folder again and refuse unless it still equals the bound
   listing (a same-size edit during the download changes the modification time).
8. Only then write member_manifest.json and publish <subject>.zip with a
   no-clobber link. Any failure after the download leaves the bytes as
   <subject>.zip.rejected (or .partial if that rename fails); a rejected
   archive never carries the final name.

Receipts (acquisition_started.json, then acquisition_result.json and
member_manifest.json) are written with exclusive creation; nothing is ever
overwritten. scientific_approval is always false.

    python3 contributor_tools/acquire_gt21_author_mirror_participant.py --subject AB17 \
        --expected-listing PLAN/AB17_expected_listing.json \
        --out /mnt/s/locomotion_data/gt21_author_mirror_2024/AB17 \
        --receipt-dir /mnt/s/locomotion_data/gt21_author_mirror_2024/acquisition_receipts/AB17 [--run]
"""
import argparse
import hashlib
import json
import os
import resource
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
import zipfile
import zlib
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # run as a script from the repository root
    sys.path.insert(0, str(ROOT))
from contributor_tools import review_gt21_s02_author_mirror as mirror  # noqa: E402

FORBIDDEN_ROOTS = (mirror.LOCAL_ROOT, Path("/mnt/s/locomotion_data/gt21_missing_participants_v1"))
BUFFER = 1024**2
RATE = 1024**2                       # bytes per second ceiling
RESERVE = 15 * 1024**3               # disk kept free after the archive
PER_ENTRY_ALLOWANCE = 1024           # ZIP header bytes allowed per listed file
FIXED_ALLOWANCE = 64 * 1024
DOWNLOAD_SECONDS = 2700
DEADLINE_SECONDS = 3400              # under the launcher's 3600 s timeout
STARTUP_MIB, RUNTIME_MIB = 2816, 2048
MEMORY_POLL_SECONDS = 15
ADDRESS_SPACE = 256 * 1024**2
CHANNELS = {"conditions", "emg", "fp", "gcLeft", "gcRight", "gon", "id", "ik", "ik_offset",
            "imu", "jp", "markers"}
STATIC = {"ik", "ik_offset", "markers"}
SUPPORTED_COMPRESSION = {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}


class Refused(RuntimeError):
    """A precondition or check failed; the reason is recorded in the receipt."""


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(BUFFER), b""):
            h.update(block)
    return h.hexdigest()


def write_exclusive(path, obj):
    with Path(path).open("x") as stream:
        stream.write(json.dumps(obj, indent=1) + "\n")


def _inside(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    return path == root or root in path.parents


# ------------------------------------------------------------ listing checks

def load_expected(path, subject):
    expected = json.loads(Path(path).read_text())
    if expected.get("subject") != subject:
        raise Refused("expected listing is for another participant")
    paths = [f["path"] for f in expected["files"]]
    if len(paths) != len(set(paths)) or not paths:
        raise Refused("expected listing is empty or has duplicate paths")
    check_layout(expected["files"], subject)
    return expected


def check_layout(files, subject):
    """GT21 layout from relative paths; raises Refused with every failed item."""
    s = mirror.structure(files, subject)
    problems = []
    if len(s["sessions"]) != 1:
        problems.append(f"sessions {s['sessions']}")
    if not any(name.lower().endswith(".osim") for name in s["osimxml_files"]):
        problems.append("no .osim model in osimxml")
    for mode, channels in s["channel_files_by_mode"].items():
        if set(channels) != CHANNELS:
            problems.append(f"{mode}: channel folders {sorted(channels)}")
        if s["recordings_by_mode_conditions_files"][mode] == 0:
            problems.append(f"{mode}: no recordings")
    if not s["every_channel_matches_conditions_count"]:
        problems.append("channel file counts differ from conditions counts")
    if not s["ik_offset_in_all_four_modes"]:
        problems.append("ik_offset missing or incomplete in a mode")
    if set(s["static_files_by_channel"]) != STATIC:
        problems.append(f"static folders {sorted(s['static_files_by_channel'])}")
    if s["unclassified_paths"]:
        problems.append(f"unclassified paths {s['unclassified_paths'][:5]}")
    if problems:
        raise Refused("layout: " + "; ".join(problems))
    return s


def listing_differences(expected, current):
    """Every path, size or time difference between two listings (empty when equal)."""
    key = lambda files: {f["path"]: (f["bytes"], f["ts"]) for f in files}
    a, b = key(expected["files"]), key(current["files"])
    diffs = [f"only in saved listing: {p}" for p in sorted(set(a) - set(b))]
    diffs += [f"only in current listing: {p}" for p in sorted(set(b) - set(a))]
    diffs += [f"changed {p}: {a[p]} -> {b[p]}" for p in sorted(set(a) & set(b)) if a[p] != b[p]]
    if expected.get("folder_href") != current.get("folder_href"):
        diffs.append("participant folder link changed")
    return diffs


def relist(subject):
    """Current Dropbox listing of one participant folder (metadata only)."""
    opener, token, _ = mirror._opener()
    root, _, _ = mirror._list(opener, token, mirror.ROOT_HASH, "")
    hrefs = [e["href"] for e in root if e["filename"] == subject and e["is_dir"]]
    if len(hrefs) != 1:
        raise Refused(f"{subject} folder not found exactly once in the 2024 copy")
    files, queue = [], [hrefs[0]]
    while queue:
        m = mirror.HREF.search(queue.pop(0))
        secure_hash, path = m.group(1), urllib.parse.unquote(m.group(2))
        entries, total, _ = mirror._list(opener, token, secure_hash, "/" + path)
        if total is not None and total != len(entries):
            raise Refused(f"{path}: {len(entries)} entries, listing says {total}")
        for e in entries:
            if e["is_dir"]:
                queue.append(e["href"])
            else:
                files.append({"path": path + "/" + e["filename"], "bytes": e["bytes"], "ts": e["ts"]})
    return {"subject": subject, "folder_href": hrefs[0], "files": files}


# ------------------------------------------------------------- host checks

def disk_free(path):
    return shutil.disk_usage(path).free


def windows_free_mib():
    result = subprocess.run(["/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
                             "-NoProfile", "-NonInteractive", "-Command",
                             "[math]::Floor((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1024)"
                             " | ConvertTo-Json -Compress"],
                            capture_output=True, text=True, check=True, timeout=15)
    return int(json.loads(result.stdout))


def download_url(folder_href):
    parts = urllib.parse.urlsplit(folder_href)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k != "dl"] + [("dl", "1")]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def open_url(url):
    request = urllib.request.Request(url, headers={"User-Agent": mirror.UA, "Accept-Encoding": "identity"})
    return urllib.request.urlopen(request, timeout=60)


# ---------------------------------------------------------------- transfer

def stream_to(response, stream, ceiling, guard, rate=RATE, clock=time.monotonic, sleep=time.sleep):
    """Copy at most ``ceiling`` bytes, hashing while writing; return (count, sha256)."""
    start, count, sha = clock(), 0, hashlib.sha256()
    while True:
        guard(ceiling - count)
        if clock() - start > DOWNLOAD_SECONDS:
            raise Refused("download exceeded its time limit")
        block = response.read(min(BUFFER, ceiling - count + 1))
        if not block:
            return count, sha.hexdigest()
        count += len(block)
        if count > ceiling:
            raise Refused("download larger than its Content-Length")
        stream.write(block)
        sha.update(block)
        if rate:
            delay = count / rate - (clock() - start)
            if delay > 0:
                sleep(min(delay, 1))


def member_path(name, subject, prefixed):
    """Normalized <subject>/... path of a ZIP member; refuses unsafe names."""
    clean = name[1:] if name.startswith("/") else name
    parts = PurePosixPath(clean).parts
    if "\\" in name or not parts or any(p in ("", ".", "..") for p in parts) or clean.startswith("/"):
        raise Refused(f"unsafe member name {name!r}")
    return clean if prefixed else f"{subject}/{clean}"


def check_zip(zf, expected, subject):
    """Central-directory checks; returns [(info, normalized path)] for file members."""
    infos = [i for i in zf.infolist() if not i.is_dir()]
    names = [i.filename for i in zf.infolist()]
    if len(names) != len(set(names)):
        raise Refused("duplicate member names")
    stripped = [i.filename.lstrip("/") for i in infos]
    prefixed = [n.startswith(subject + "/") for n in stripped]
    if any(prefixed) and not all(prefixed):
        raise Refused("members mix participant-prefixed and unprefixed paths")
    members = [(i, member_path(i.filename, subject, all(prefixed))) for i in infos]
    for info, _ in members:
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            raise Refused(f"symlink member {info.filename}")
        if info.flag_bits & 0x1:
            raise Refused(f"encrypted member {info.filename}")
        if info.compress_type not in SUPPORTED_COMPRESSION:
            raise Refused(f"unsupported compression in {info.filename}")
    got = {path: info.file_size for info, path in members}
    if len(got) != len(members):
        raise Refused("two members normalize to one path")
    want = {f["path"]: f["bytes"] for f in expected["files"]}
    problems = [f"missing {p}" for p in sorted(set(want) - set(got))]
    problems += [f"unlisted {p}" for p in sorted(set(got) - set(want))]
    problems += [f"size {p}: {got[p]} != {want[p]}" for p in sorted(set(got) & set(want)) if got[p] != want[p]]
    if problems:
        raise Refused(f"ZIP differs from listing ({len(problems)}): " + "; ".join(problems[:10]))
    check_layout([{"path": p, "bytes": i.file_size, "ts": 0} for i, p in members], subject)
    return members


def hash_members(zf, members, guard):
    """Stream each member (no extraction); bytes, CRC32 and SHA-256 per file."""
    rows = []
    for info, path in sorted(members, key=lambda m: m[1]):
        guard(0)
        sha, crc, count = hashlib.sha256(), 0, 0
        with zf.open(info) as stream:  # zipfile also raises on a CRC mismatch at EOF
            for block in iter(lambda: stream.read(BUFFER), b""):
                sha.update(block)
                crc = zlib.crc32(block, crc)
                count += len(block)
        if count != info.file_size or crc != info.CRC:
            raise Refused(f"member {path} read back {count} bytes, CRC {crc:08x}; directory says "
                          f"{info.file_size}, {info.CRC:08x}")
        rows.append({"path": path, "zip_name": info.filename, "bytes": count,
                     "crc32": f"{crc:08x}", "sha256": sha.hexdigest()})
    return rows


# ------------------------------------------------------------------- run

def acquire(subject, expected_path, out, receipt_dir, *, lister=relist, opener=open_url,
            free_bytes=disk_free, free_mib=windows_free_mib, clock=time.monotonic,
            sleep=time.sleep, rate=RATE):
    """Run one acquisition; returns the result receipt. Raises Refused after recording it."""
    out, receipt_dir = Path(out), Path(receipt_dir)
    for path in (out, receipt_dir):
        if path.exists() or path.is_symlink():
            raise Refused(f"{path} already exists; earlier attempts are preserved")
        if any(_inside(path, root) for root in FORBIDDEN_ROOTS):
            raise Refused(f"{path} is inside a protected source root")
    if _inside(out, receipt_dir) or _inside(receipt_dir, out):
        raise Refused("receipt directory and output root must be separate")
    expected = load_expected(expected_path, subject)
    receipt_dir.mkdir(parents=True, exist_ok=False)
    out.parent.mkdir(parents=True, exist_ok=True)  # shared container; the root itself stays exclusive
    started = clock()
    result = {"task_id": "GT21-S02", "subject": subject, "scientific_approval": False,
              "source": "authors' 2024 Dropbox copy", "expected_listing": str(expected_path),
              "expected_listing_sha256": sha256_file(expected_path),
              "script_sha256": sha256_file(__file__), "started_at_utc": utcnow(),
              "output_root": str(out), "receipt_dir": str(receipt_dir)}
    write_exclusive(receipt_dir / "acquisition_started.json", result)
    last_memory = [None]

    def guard(remaining):
        if (receipt_dir / "STOP").exists():
            raise Refused("stopped by request (STOP file)")
        if clock() - started > DEADLINE_SECONDS:
            raise Refused("deadline reached")
        if free_bytes(out.parent) < RESERVE + remaining:
            raise Refused("disk free below the 15 GiB reserve plus remaining bytes")
        if last_memory[0] is None or clock() - last_memory[0] >= MEMORY_POLL_SECONDS:
            if free_mib() < RUNTIME_MIB:
                raise Refused("Windows free memory below 2048 MiB")
            last_memory[0] = clock()

    final = out / f"{subject}.zip"
    partial = out / f"{subject}.zip.partial"
    try:
        current = lister(subject)
        diffs = listing_differences(expected, current)
        result["relisted_at_utc"] = utcnow()
        if diffs:
            result["listing_differences"] = diffs[:50]
            raise Refused(f"current listing differs from the saved listing ({len(diffs)} items)")
        listed = sum(f["bytes"] for f in expected["files"])
        ceiling_allowed = listed + PER_ENTRY_ALLOWANCE * len(expected["files"]) + FIXED_ALLOWANCE
        if free_bytes(out.parent) < RESERVE + ceiling_allowed:
            raise Refused("disk free below the 15 GiB reserve plus the archive")
        if free_mib() < STARTUP_MIB:
            raise Refused("Windows free memory below 2816 MiB at start")
        out.mkdir(parents=False, exist_ok=False)
        url = download_url(expected["folder_href"])
        with opener(url) as response:
            headers = {k: response.headers.get(k) for k in ("Content-Length", "Content-Disposition",
                                                            "Content-Type")}
            result["http"] = {"status": response.status, "headers": headers}
            if response.status != 200:
                raise Refused(f"HTTP status {response.status}")
            if f"{subject}.zip" not in (headers["Content-Disposition"] or ""):
                raise Refused("response is not the participant ZIP")
            length = int(headers["Content-Length"] or -1)
            if not listed <= length <= ceiling_allowed:
                raise Refused(f"Content-Length {length} outside [{listed}, {ceiling_allowed}]")
            with partial.open("xb") as stream:
                count, digest = stream_to(response, stream, length, guard, rate, clock, sleep)
                stream.flush()
                os.fsync(stream.fileno())
        if count != length:
            raise Refused(f"received {count} of {length} bytes")
        result.update(zip_bytes=count, zip_sha256=digest)
        with zipfile.ZipFile(partial) as zf:  # every check runs on the unpublished bytes
            members = check_zip(zf, expected, subject)
            result["central_directory_checks"] = "passed: paths and sizes equal the listing; layout passed"
            rows = hash_members(zf, members, guard)
        after = lister(subject)
        diffs = listing_differences(expected, after)
        result["relisted_after_download_at_utc"] = utcnow()
        if diffs:
            result["listing_differences_after_download"] = diffs[:50]
            raise Refused(f"listing changed during the download ({len(diffs)} items)")
        if clock() - started > DEADLINE_SECONDS:
            raise Refused("deadline reached")
        manifest = {"subject": subject, "zip_sha256": digest, "zip_bytes": count,
                    "members": len(rows), "member_bytes": sum(r["bytes"] for r in rows), "files": rows}
        write_exclusive(receipt_dir / "member_manifest.json", manifest)
        os.link(partial, final)  # no-clobber publication, only after every check passed
        partial.unlink()
        result.update(status="acquired_verified_not_extracted", zip_path=str(final), members=len(rows),
                      member_bytes=manifest["member_bytes"],
                      member_manifest_sha256=sha256_file(receipt_dir / "member_manifest.json"))
    except BaseException as error:
        result.update(status="failed_preserved", reason=f"{type(error).__name__}: {error}")
        if partial.exists() and not final.exists():
            rejected = out / f"{subject}.zip.rejected"
            try:
                os.link(partial, rejected)
                partial.unlink()
                result["rejected_path"] = str(rejected)
            except OSError:
                result["rejected_path"] = str(partial)
        raise
    finally:
        result["finished_at_utc"] = utcnow()
        write_exclusive(receipt_dir / "acquisition_result.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--expected-listing", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--receipt-dir", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    if not args.run:
        expected = load_expected(args.expected_listing, args.subject)
        print(json.dumps({"status": "plan_only", "subject": args.subject,
                          "files": len(expected["files"]),
                          "bytes": sum(f["bytes"] for f in expected["files"]),
                          "download_url": download_url(expected["folder_href"]),
                          "out": str(args.out), "receipt_dir": str(args.receipt_dir)}))
        return 0
    resource.setrlimit(resource.RLIMIT_AS, (ADDRESS_SPACE, ADDRESS_SPACE))
    os.nice(max(0, 19 - os.nice(0)))
    try:
        result = acquire(args.subject, args.expected_listing, args.out, args.receipt_dir)
    except Refused as error:
        print(json.dumps({"status": "refused", "reason": str(error)}))
        return 2
    print(json.dumps({k: result[k] for k in ("status", "zip_sha256", "members")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
