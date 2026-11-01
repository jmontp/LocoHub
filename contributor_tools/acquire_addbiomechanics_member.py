#!/usr/bin/env python3
"""HIST-05: acquire, convert and delete one AddBiomechanics B3D (Falisse, Tan running, Tan walking).

One participant per invocation, for one guarded-launcher job. Without --run it
only checks the bound expected-member file (no network). With --run, in order:

1. Refuse a dropped participant (Falisse subject_1, subject_7, subject_8; D-HIST-04-2 = A)
   before anything else.
2. Refuse if the output root or receipt directory exists, if either is inside
   the other, if the output root is outside the transient root, or if any
   *.b3d / *.b3d.partial / *.b3d.rejected exists anywhere under the transient
   root: one expanded B3D on disk at a time (peak 2.22 GB, Tan running s3).
3. Admission: free disk >= 15 GiB + 2 x expanded size; Windows free memory >= 2816 MiB.
4. Read the member's local header by HTTP range (If-Match on the pinned ETag;
   exact 206, Content-Range and Content-Length) and require name, flags, method,
   CRC32 and sizes to equal the archive central directory.
5. Stream the compressed payload (2 MiB/s ceiling), inflate straight to
   source/<subject>.b3d.partial; no compressed copy is kept. SHA-256 of the
   compressed and expanded streams and CRC32 of the expanded stream; refuse on
   any size or CRC mismatch. fsync, then re-read the file and re-check SHA-256.
6. Header checks: when a Drive header SHA-256 was bound (HIST-04), the expanded
   header must equal it; the layout arithmetic must equal the file size.
7. Publish the B3D with a no-clobber link, convert it (one row per frame from
   the dynamics pass, chosen by name), re-check the outputs, then delete the B3D.
   The pilot (--keep-source-for-comparison) keeps its B3D for a nimblephysics
   readFrames comparison; while that receipt has no comparison_release.json,
   every later job refuses. ``release-pilot RECEIPT_DIR NEW_OUT_DIR`` reads the
   retained B3D with nimblephysics readFrames itself, compares every written
   frame and signal column of frames.parquet exactly, records counts, version
   and hashes, and deletes the B3D only when everything is equal. A release
   record counts only if it holds such a complete comparison.
   With --run, the transient root and receipt root are fixed to DEST; run()
   also always checks DEST for pending pilots and leftover B3Ds.
   Each run also re-checks its expected entry against the hash-checked central
   directory before any network call.
8. Receipts (acquisition_started.json, acquisition_result.json) go to the
   receipt directory, outside the data folder, with exclusive creation. On any
   failure the expanded bytes are kept as <subject>.b3d.rejected, which blocks
   the next acquisition until a person reviews it.

STOP file in the receipt directory, deadline, disk reserve every block, Windows
memory every 15 s. scientific_approval is always false.

    python3 contributor_tools/acquire_addbiomechanics_member.py --expected PLAN/x_expected.json \
        --out DEST/fa16/subject_0 --receipt-dir DEST/acquisition_receipts/fa16_subject_0 --transient-root DEST [--run]
    python3 contributor_tools/acquire_addbiomechanics_member.py plan HEADERS_DIR PLAN_DIR
    python3 contributor_tools/acquire_addbiomechanics_member.py release-pilot RECEIPT_DIR NEW_OUT_DIR
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import resource
import shutil
import struct
import subprocess
import sys
import time
import urllib.request
import zlib
from datetime import datetime, timezone
from pathlib import Path

for _k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "ARROW_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from contributor_tools.acquire_addbiomechanics_zip_member import header_identity, stream_member  # noqa: E402

CONVERTER_PATH = ROOT / "contributor_tools/conversion_scripts/AddBiomechanics/convert_addbiomechanics_dynamics_frames.py"
_spec = importlib.util.spec_from_file_location("adb_dynamics_frames", CONVERTER_PATH)
conv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(conv)

ARCHIVE = {"url": "http://archive.simtk.org/addbiomechanics/addbiomechanics.zip", "bytes": 417665422113,
           "etag": '"613ecc9321-631d01550d044"', "last_modified": "Wed, 02 Apr 2025 18:47:20 GMT"}
CD_PATH = ROOT / "converted_datasets/reconversion_v2/swarm_backlog_20261021/adb_official_release_metadata_20261021/central_directory.bin"
CD_SHA256 = "88d494ccf3b1026ded8c37b9fcbf093e5f76adf0f1bda3d2956b19d3f508ce09"
DEST = Path("/mnt/s/locomotion_data/addbiomechanics_hist04")
RESERVE = 15 * 1024 ** 3
RATE = 2 * 1024 ** 2
DEADLINE_SECONDS = 3400
STARTUP_MIB, RUNTIME_MIB, MEMORY_POLL_SECONDS = 2816, 2048, 15
ADDRESS_SPACE = 768 * 1024 ** 2
TRANSIENT_PATTERNS = ("*.b3d", "*.b3d.partial", "*.b3d.rejected")
OUTPUTS = ["frames.parquet", "conversion.json", "dynamics_model.osim"]
RETAINED = "converted_source_retained_for_comparison"


class Refused(RuntimeError):
    """A precondition or check failed; the reason is recorded in the receipt."""


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path, guard=lambda: None):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            guard()
            h.update(block)
    return h.hexdigest()


def write_exclusive(path, obj):
    with Path(path).open("x") as stream:
        stream.write(json.dumps(obj, indent=1) + "\n")


def _inside(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    return path == root or root in path.parents


CD_KEYS = ("flags", "method", "crc32", "compressed_bytes", "expanded_bytes", "local_header_offset")


def load_expected(path):
    e = json.loads(Path(path).read_text())
    slug, subject = conv.check_member(e["member"])  # dropped participants refused here
    keys = CD_KEYS
    if any(not isinstance(e.get(k), int) for k in keys) or e["method"] != 8 or min(e["compressed_bytes"], e["expanded_bytes"]) <= 0:
        raise Refused("expected member lacks a nonempty DEFLATE central-directory record")
    if e.get("archive") != ARCHIVE:
        raise Refused("expected member is bound to another archive version")
    return e, slug, subject


def pending_comparisons(receipts_root):
    """Receipts of a retained pilot B3D whose nimblephysics comparison is not yet recorded and released."""
    root = Path(receipts_root)
    if not root.exists():
        return []
    out = []
    for r in sorted(root.glob("*/acquisition_result.json")):
        result = json.loads(r.read_text())
        if result.get("status") == RETAINED and not release_is_valid(r.parent, result):
            out.append(str(r.parent))
    return out


def release_is_valid(receipt_dir, result):
    """A release counts only if it records a complete, exact comparison of this pilot and its B3D is gone."""
    path = Path(receipt_dir) / "comparison_release.json"
    if not path.exists():
        return False
    try:
        rel = json.loads(path.read_text())
        c = rel["comparison"]
        return (c["status"] == "agree" and c["mismatches"] == 0 and c["frames_compared"] == result["rows"] > 0
                and c["values_compared"] > 0 and c["b3d_sha256"] == result["b3d_sha256"]
                and c["frames_parquet_sha256"] == result["frames_parquet_sha256"]
                and bool(c["nimblephysics_version"]) and bool(rel["script_sha256"])
                and not Path(result["b3d_retained_path"]).exists())
    except (KeyError, TypeError, ValueError):
        return False


def transient_files(root):
    root = Path(root)
    return sorted(str(p) for pat in TRANSIENT_PATTERNS for p in root.rglob(pat)) if root.exists() else []


# ----------------------------------------------------------------- network --

def open_range(start, length, archive=ARCHIVE):
    req = urllib.request.Request(archive["url"], headers={"Range": f"bytes={start}-{start + length - 1}",
                                                          "If-Match": archive["etag"], "Accept-Encoding": "identity"})
    return urllib.request.urlopen(req, timeout=60)


def checked_range(opener, start, length, archive=ARCHIVE):
    """Open a range and require exact 206 metadata for the pinned archive version."""
    r = opener(start, length)
    try:
        h = r.headers
        if (r.status != 206 or h.get("Content-Range") != f"bytes {start}-{start + length - 1}/{archive['bytes']}"
                or h.get("Content-Length") != str(length) or h.get("ETag") != archive["etag"]
                or h.get("Content-Encoding", "identity") != "identity"):
            raise Refused(f"range {start}+{length}: response is not the exact pinned 206 range")
    except BaseException:
        r.close()
        raise
    return r


def local_header(opener, e):
    with checked_range(opener, e["local_header_offset"], 30) as r:
        fixed = r.read(31)
    if len(fixed) != 30 or fixed[:4] != b"PK\x03\x04":
        raise Refused("local header signature or length differs")
    n, x = struct.unpack_from("<HH", fixed, 26)
    with checked_range(opener, e["local_header_offset"], 30 + n + x) as r:
        full = r.read(30 + n + x + 1)
    member = {"name": e["member"], "flags": e["flags"], "compression_method": e["method"], "crc32": e["crc32"],
              "compressed_bytes": e["compressed_bytes"], "expanded_bytes": e["expanded_bytes"]}
    try:
        header_identity(full, member)
    except ValueError as error:
        raise Refused(f"local header differs from the central directory: {error}") from error
    return e["local_header_offset"] + 30 + n + x, member


# ------------------------------------------------------------- host checks --

def disk_free(path):
    return shutil.disk_usage(path).free


def windows_free_mib():
    result = subprocess.run(["/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe", "-NoProfile",
                             "-NonInteractive", "-Command",
                             "[math]::Floor((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1024) | ConvertTo-Json -Compress"],
                            capture_output=True, text=True, check=True, timeout=15)
    return int(json.loads(result.stdout))


class _Discard:
    def write(self, b):
        return len(b)


# --------------------------------------------------------------------- run --

def run(expected_path, out, receipt_dir, transient_root, *, keep_source=False, central=None, opener=open_range,
        free_bytes=disk_free, free_mib=windows_free_mib, clock=time.monotonic, sleep=time.sleep, rate=RATE,
        fixed_root=DEST):
    e, slug, subject = load_expected(expected_path)
    cd = (central or central_directory)()
    if cd.get(e["member"]) != {k: e[k] for k in CD_KEYS}:
        raise Refused("expected member differs from the hash-checked archive central directory")
    out, receipt_dir, transient_root = Path(out), Path(receipt_dir), Path(transient_root)
    fixed_root = Path(fixed_root)
    # Checked under the passed roots and always under the fixed destination, whatever paths were passed.
    pending = pending_comparisons(receipt_dir.parent) + pending_comparisons(fixed_root / "acquisition_receipts")
    if pending:
        raise Refused(f"a retained pilot B3D still awaits its recorded comparison and deletion: {sorted(set(pending))}")
    for path in (out, receipt_dir):
        if path.exists() or path.is_symlink():
            raise Refused(f"{path} already exists; earlier attempts are preserved")
    if _inside(out, receipt_dir) or _inside(receipt_dir, out):
        raise Refused("receipt directory and output root must be separate")
    if not _inside(out, transient_root) or out.resolve() == transient_root.resolve():
        raise Refused("output root must be inside the transient root")
    held = sorted(set(transient_files(transient_root) + transient_files(fixed_root)))
    if held:
        raise Refused(f"another B3D is on disk under the transient root: {held[:3]}")
    receipt_dir.mkdir(parents=True, exist_ok=False)
    started = clock()
    result = {"task_id": "HIST-05", "member": e["member"], "dataset": slug, "subject": subject,
              "scientific_approval": False, "expected": str(expected_path), "expected_sha256": sha256_file(expected_path),
              "script_sha256": sha256_file(__file__), "converter_sha256": sha256_file(CONVERTER_PATH),
              "started_at_utc": utcnow(), "output_root": str(out), "receipt_dir": str(receipt_dir)}
    write_exclusive(receipt_dir / "acquisition_started.json", result)
    last_memory = [None]
    need = [e["expanded_bytes"]]

    def guard():
        if (receipt_dir / "STOP").exists():
            raise Refused("stopped by request (STOP file)")
        if clock() - started > DEADLINE_SECONDS:
            raise Refused("deadline reached")
        if free_bytes(transient_root) < RESERVE + need[0]:
            raise Refused("disk free below the 15 GiB reserve plus remaining bytes")
        if last_memory[0] is None or clock() - last_memory[0] >= MEMORY_POLL_SECONDS:
            if free_mib() < RUNTIME_MIB:
                raise Refused("Windows free memory below 2048 MiB")
            last_memory[0] = clock()

    final = out / "source" / f"{subject}.b3d"
    partial = final.with_name(final.name + ".partial")
    try:
        if free_bytes(transient_root) < RESERVE + 2 * e["expanded_bytes"]:
            raise Refused("disk free below the 15 GiB reserve plus twice the expanded B3D")
        if free_mib() < STARTUP_MIB:
            raise Refused("Windows free memory below 2816 MiB at start")
        payload, member = local_header(opener, e)
        out.mkdir(parents=True, exist_ok=False)
        final.parent.mkdir()
        with checked_range(opener, payload, e["compressed_bytes"]) as response, partial.open("xb") as stream:
            try:
                got = stream_member(response, _Discard(), stream, member, guard, rate, clock, sleep)
            except (ValueError, zlib.error) as error:
                raise Refused(f"stream check failed: {error}") from error
            stream.flush()
            os.fsync(stream.fileno())
        result.update(compressed_sha256=got["compressed_sha256"], b3d_sha256=got["source_b3d_sha256"],
                      compressed_bytes=got["compressed_bytes"], expanded_bytes=got["expanded_bytes"], crc32=got["crc32"])
        if sha256_file(partial, guard) != got["source_b3d_sha256"] or partial.stat().st_size != e["expanded_bytes"]:
            raise Refused("persisted B3D differs from the streamed bytes")
        raw = conv.read_header(partial)
        result["header_sha256"] = hashlib.sha256(raw).hexdigest()
        if e.get("drive_header_sha256") and result["header_sha256"] != e["drive_header_sha256"]:
            raise Refused("B3D header differs from the Drive copy read in HIST-04")
        h = conv.parse_header(raw)
        if conv.layout(h, len(raw))[1] != e["expanded_bytes"]:
            raise Refused("B3D layout arithmetic differs from the file size")
        result["pass_orders"] = sorted({",".join(p["type"] for p in t["passes"]) for t in h["trials"]})
        os.link(partial, final)
        partial.unlink()
        need[0] = e["expanded_bytes"]  # outputs are at most of the order of the source
        summary = conv.convert(final, e["member"], got["source_b3d_sha256"], out, guard)
        if sha256_file(out / "frames.parquet") != summary["frames_parquet_sha256"] or sorted(
                p.name for p in out.iterdir() if p.is_file()) != sorted(OUTPUTS):
            raise Refused("conversion outputs differ from the conversion summary")
        if sha256_file(final, guard) != got["source_b3d_sha256"]:
            raise Refused("B3D changed during conversion")
        result.update(rows=summary["rows"], frames_excluded=summary["frames_excluded"],
                      frames_parquet_sha256=summary["frames_parquet_sha256"])
        if keep_source:
            # Pilot: the B3D stays for the nimblephysics readFrames comparison; it blocks every
            # later job until release_pilot records the comparison and deletes it.
            result.update(status=RETAINED, b3d_deleted=False, b3d_retained_path=str(final))
        else:
            final.unlink()
            final.parent.rmdir()
            result.update(status="converted_source_deleted_unreviewed", b3d_deleted=True, b3d_deleted_at_utc=utcnow())
    except BaseException as error:
        result.update(status="failed_preserved", reason=f"{type(error).__name__}: {error}")
        for src in (partial, final):
            if src.exists():
                rejected = final.with_name(final.name + ".rejected")
                try:
                    os.link(src, rejected)
                    src.unlink()
                    result["rejected_path"] = str(rejected)
                except OSError:
                    result["rejected_path"] = str(src)
                break
        raise
    finally:
        result["finished_at_utc"] = utcnow()
        write_exclusive(receipt_dir / "acquisition_result.json", result)
    return result


SIGNAL_GROUPS = (("pos", "pos"), ("vel", "vel"), ("acc", "acc"), ("tau", "tau"))


def _is_dynamics(pass_type):
    return getattr(pass_type, "name", str(pass_type)).upper().endswith("DYNAMICS")


def nimble_subject(b3d):
    import nimblephysics
    return nimblephysics.biomechanics.SubjectOnDisk(str(b3d))


def nimble_version():
    import importlib.metadata
    return importlib.metadata.version("nimblephysics")


def compare_with_reader(b3d, parquet, conversion, subject):
    """Every written frame and signal column of frames.parquet against the record the reader labels dynamics.
    Exact equality (NaN equals NaN only where both are NaN). Returns counts; no tolerance."""
    import pyarrow.parquet as pq
    table = pq.read_table(parquet)
    cols = table.column_names
    data = {c: table.column(c).to_pylist() for c in cols}
    n_dofs = sum(1 for c in cols if c.endswith("_pos") and c.startswith("dof"))
    bodies = conversion["contact_bodies"]
    expected_cols = conv.columns(n_dofs, bodies)
    if [c for c in cols if c in expected_cols] != expected_cols:
        raise Refused("frames.parquet signal columns differ from the converter's column list")
    rows_by_trial = {}
    for i, ti in enumerate(data["source_trial_index"]):
        rows_by_trial.setdefault(ti, []).append(i)
    written = {r["trial_index"]: r for r in conversion["trials"] if r["status"] == "written"}
    if set(rows_by_trial) != set(written):
        raise Refused("trials in frames.parquet differ from the trials the conversion says it wrote")
    frames = values = 0
    mismatches = []
    for ti, idx in sorted(rows_by_trial.items()):
        if len(idx) != written[ti]["rows"]:
            raise Refused(f"trial {ti}: {len(idx)} rows, conversion says {written[ti]['rows']}")
        fl = subject.readFrames(ti, 0, len(idx), includeSensorData=False, includeProcessingPasses=True)
        if len(fl) != len(idx):
            raise Refused(f"trial {ti}: reader returned {len(fl)} of {len(idx)} frames")
        for i in idx:
            f = data["source_frame_index"][i]
            fr = fl[f]
            dyn = [k for k, p in enumerate(fr.processingPasses) if _is_dynamics(p.type)]
            if dyn != [data["source_pass_index_in_trial"][i]]:
                mismatches.append(f"trial {ti} frame {f}: reader dynamics index {dyn}")
                continue
            p = fr.processingPasses[dyn[0]]
            ref = []
            for _, attr in SIGNAL_GROUPS:
                ref += list(getattr(p, attr))
            force, cop, torque = list(p.groundContactForce), list(p.groundContactCenterOfPressure), list(p.groundContactTorque)
            for b in range(len(bodies)):
                ref += force[3 * b:3 * b + 3] + cop[3 * b:3 * b + 3] + torque[3 * b:3 * b + 3]
            ref += list(p.comPos) + list(p.comVel) + list(p.comAcc) + list(p.residualWrenchInRootFrame)
            if len(ref) != len(expected_cols):
                mismatches.append(f"trial {ti} frame {f}: reader gave {len(ref)} values for {len(expected_cols)} columns")
                continue
            for c, r in zip(expected_cols, ref):
                v = data[c][i]
                same = (v == r) or (v is not None and math.isnan(v) and math.isnan(r))
                values += 1
                if not same:
                    mismatches.append(f"trial {ti} frame {f} {c}: parquet {v!r} reader {r!r}")
            frames += 1
    return {"frames_compared": frames, "values_compared": values, "rows_in_parquet": table.num_rows,
            "trials_compared": len(rows_by_trial), "mismatches": len(mismatches), "mismatch_examples": mismatches[:20],
            "tolerance": "exact equality"}


def release_pilot(receipt_dir, out_dir, *, subject_reader=nimble_subject, version=nimble_version):
    """Compare the retained pilot B3D with nimblephysics readFrames on every written frame and
    signal column; delete the B3D only when all of it is exactly equal."""
    receipt_dir, out_dir = Path(receipt_dir), Path(out_dir)
    result = json.loads((receipt_dir / "acquisition_result.json").read_text())
    if result.get("status") != RETAINED:
        raise Refused("receipt is not a retained pilot")
    if out_dir.exists() or _inside(out_dir, receipt_dir):
        raise Refused("comparison output must be a new folder outside the receipt directory")
    final = Path(result["b3d_retained_path"])
    data_root = Path(result["output_root"])
    parquet, conversion_path = data_root / "frames.parquet", data_root / "conversion.json"
    b3d_sha, parquet_sha = sha256_file(final), sha256_file(parquet)
    if b3d_sha != result["b3d_sha256"] or parquet_sha != result["frames_parquet_sha256"]:
        raise Refused("retained B3D or frames.parquet changed since the pilot")
    conversion = json.loads(conversion_path.read_text())
    comparison = compare_with_reader(final, parquet, conversion, subject_reader(final))
    comparison.update(b3d_sha256=b3d_sha, frames_parquet_sha256=parquet_sha, conversion_sha256=sha256_file(conversion_path),
                      nimblephysics_version=version(), script_sha256=sha256_file(__file__),
                      converter_sha256=sha256_file(CONVERTER_PATH), compared_at_utc=utcnow())
    ok = (comparison["mismatches"] == 0 and comparison["frames_compared"] == result["rows"] == comparison["rows_in_parquet"]
          and comparison["values_compared"] > 0)
    comparison["status"] = "agree" if ok else "disagree"
    out_dir.mkdir(parents=True, exist_ok=False)
    write_exclusive(out_dir / "comparison.json", comparison)
    if not ok:
        write_exclusive(receipt_dir / "comparison_record.json", {"comparison": comparison, "b3d_kept": str(final)})
        raise Refused(f"nimblephysics comparison did not agree ({comparison['mismatches']} mismatches); "
                      "the B3D is kept and later jobs stay blocked")
    if sha256_file(final) != b3d_sha:
        raise Refused("retained B3D changed during the comparison")
    final.unlink()
    final.parent.rmdir()
    release = {"comparison": comparison, "comparison_path": str(out_dir / "comparison.json"),
               "b3d_deleted": str(final), "released_at_utc": utcnow(), "script_sha256": sha256_file(__file__)}
    write_exclusive(receipt_dir / "comparison_release.json", release)
    return release


# -------------------------------------------------------------------- plan --

def central_directory(path=CD_PATH):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != CD_SHA256:
        raise Refused("central directory differs from the HIST-01/HIST-03 record")
    out, i = {}, 0
    while i + 46 <= len(raw) and raw[i:i + 4] == b"PK\x01\x02":
        (_, _, _, flags, method, _, _, crc, csize, usize, nlen, elen, clen, _, _, _, off) = struct.unpack("<IHHHHHHIIIHHHHHII", raw[i:i + 46])
        name = raw[i + 46:i + 46 + nlen].decode("utf8")
        extra, j = raw[i + 46 + nlen:i + 46 + nlen + elen], 0
        while j + 4 <= len(extra):
            hid, hlen = struct.unpack("<HH", extra[j:j + 4])
            body, k = extra[j + 4:j + 4 + hlen], 0
            if hid == 1:
                if usize == 0xFFFFFFFF: usize = struct.unpack("<Q", body[k:k + 8])[0]; k += 8
                if csize == 0xFFFFFFFF: csize = struct.unpack("<Q", body[k:k + 8])[0]; k += 8
                if off == 0xFFFFFFFF: off = struct.unpack("<Q", body[k:k + 8])[0]; k += 8
            j += 4 + hlen
        if name.endswith(".b3d") and "/No_Arm/" in name and any(f"/{f}/" in name for f in conv.FOLDERS.values()):
            out[name] = {"flags": flags, "method": method, "crc32": crc, "compressed_bytes": csize,
                         "expanded_bytes": usize, "local_header_offset": off}
        i += 46 + nlen + elen + clen
    return out


def plan(headers_dir, plan_dir):
    from contributor_tools.guarded_launcher import validate_spec
    from contributor_tools.review_hist04_addbiomechanics_metadata import DRIVE_IDS
    cd = central_directory()
    if len(cd) != 36:
        raise Refused(f"expected 36 members, found {len(cd)}")
    receipts = {}
    for p in Path(headers_dir).glob("*.fetch.json"):
        r = json.loads(p.read_text())
        receipts[r["member"]] = r
    plan_dir = Path(plan_dir)
    plan_dir.mkdir(parents=True, exist_ok=False)
    kept = sorted((m for m in cd if m not in conv.DROPPED),
                  key=lambda m: ({"fa16": 0, "ta22": 1, "ta21": 2}[conv.study_of(m)], cd[m]["expanded_bytes"]))
    rel = lambda q: str(Path(q).resolve().relative_to(ROOT))
    script, converter = "contributor_tools/acquire_addbiomechanics_member.py", rel(CONVERTER_PATH)
    zip_module = "contributor_tools/acquire_addbiomechanics_zip_member.py"
    hashes = {q: sha256_file(ROOT / q) for q in (script, converter, zip_module)}
    out = []
    for n, m in enumerate(kept, 1):
        slug, subject = conv.check_member(m)
        exp = {"member": m, **cd[m], "archive": ARCHIVE, "central_directory_sha256": CD_SHA256,
               "drive_file_id": DRIVE_IDS[m],
               "drive_header_sha256": receipts[m]["header_sha256"] if m in receipts else None}
        ep = plan_dir / f"{slug}_{subject}_expected.json"
        ep.write_text(json.dumps(exp, indent=1) + "\n")
        root = DEST / slug / subject
        exp_mib = math.ceil(cd[m]["expanded_bytes"] / 1024 ** 2)
        pilot = n == 1
        spec = {"job_id": f"hist05-adb-{slug}-{subject}",
                "command": ["python3", script, "--expected", rel(ep), "--out", str(root),
                            "--receipt-dir", str(DEST / "acquisition_receipts" / f"{slug}_{subject}"),
                            "--transient-root", str(DEST), *(["--keep-source-for-comparison"] if pilot else []), "--run"],
                "output_root": str(root), "receipt_path": str(DEST / "launcher_receipts" / f"{slug}_{subject}.json"),
                "bindings": {**hashes, rel(ep): sha256_file(ep)},
                "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
                "startup_memory_mib": {"linux": 3584, "windows": 2816}, "runtime_memory_mib": {"linux": 2048, "windows": 2048},
                "disk_admission": [{"path": str(DEST.parent), "min_free_mib": RESERVE // 1024 ** 2 + 2 * exp_mib}],
                "expected_output_names": OUTPUTS + ([f"{subject}.b3d"] if pilot else []), "address_space_mib": 768}
        validate_spec(spec)
        sp = plan_dir / f"{n:02d}_{slug}_{subject}_spec.json"
        sp.write_text(json.dumps(spec, indent=1) + "\n")
        out.append({"order": n, "member": m, "pilot_keeps_b3d": pilot, "spec": rel(sp), "spec_sha256": sha256_file(sp),
                    "expected_sha256": sha256_file(ep), "transfer_bytes": cd[m]["compressed_bytes"],
                    "transient_b3d_bytes": cd[m]["expanded_bytes"], "validate_spec": "passed in-process; not launched"})
    first = out[0]
    p_slug, p_subject = conv.check_member(first["member"])
    rel_root = DEST / "pilot_comparison" / f"{p_slug}_{p_subject}"
    rspec = {"job_id": f"hist05-adb-release-pilot-{p_slug}-{p_subject}",
             "command": ["python3", script, "release-pilot", str(DEST / "acquisition_receipts" / f"{p_slug}_{p_subject}"), str(rel_root)],
             "output_root": str(rel_root), "receipt_path": str(DEST / "launcher_receipts" / f"release_{p_slug}_{p_subject}.json"),
             "bindings": dict(hashes), "timeout_seconds": 1800, "kill_after_seconds": 30, "poll_seconds": 15,
             "startup_memory_mib": {"linux": 3584, "windows": 2816}, "runtime_memory_mib": {"linux": 2048, "windows": 2048},
             "disk_admission": [{"path": str(DEST.parent), "min_free_mib": RESERVE // 1024 ** 2}],
             "expected_output_names": ["comparison.json"]}
    # No address_space_mib: nimblephysics (libtorch) cannot map under the 768 MiB PM-01 cap; runtime memory polling still applies.
    validate_spec(rspec)
    rp = plan_dir / f"{1:02d}b_release_pilot_{p_slug}_{p_subject}_spec.json"
    rp.write_text(json.dumps(rspec, indent=1) + "\n")
    index = {"task_id": "HIST-05", "kept": len(out),
             "pilot_release_spec": {"spec": rel(rp), "spec_sha256": sha256_file(rp), "validate_spec": "passed in-process; not launched",
                                    "runs_after": first["spec"], "before": out[1]["spec"]}, "dropped": sorted(conv.DROPPED), "bound_hashes": hashes, "specs": out}
    (plan_dir / "index.json").write_text(json.dumps(index, indent=1) + "\n")
    return index


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["plan"]:
        idx = plan(argv[1], argv[2])
        print(json.dumps({"kept": idx["kept"], "bound_hashes": idx["bound_hashes"]}))
        return 0
    if argv[:1] == ["release-pilot"]:
        if len(argv) != 3:
            raise SystemExit("usage: release-pilot RECEIPT_DIR NEW_OUT_DIR (the comparison is computed, never read from a file)")
        try:
            r = release_pilot(argv[1], argv[2])
        except Refused as error:
            print(json.dumps({"status": "refused", "reason": str(error)}))
            return 2
        print(json.dumps({k: r["comparison"][k] for k in ("status", "frames_compared", "values_compared", "mismatches")}))
        return 0
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--expected", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--receipt-dir", type=Path, required=True)
    p.add_argument("--transient-root", type=Path, required=True)
    p.add_argument("--keep-source-for-comparison", action="store_true")
    p.add_argument("--run", action="store_true")
    a = p.parse_args(argv)
    if not a.run:
        e, slug, subject = load_expected(a.expected)
        print(json.dumps({"status": "plan_only", "member": e["member"], "compressed_bytes": e["compressed_bytes"],
                          "expanded_bytes": e["expanded_bytes"], "out": str(a.out)}))
        return 0
    if (a.transient_root.resolve() != DEST.resolve() or a.receipt_dir.resolve().parent != (DEST / "acquisition_receipts").resolve()
            or not _inside(a.out, DEST)):
        print(json.dumps({"status": "refused", "reason": f"--run requires the fixed roots under {DEST}"}))
        return 2
    resource.setrlimit(resource.RLIMIT_AS, (ADDRESS_SPACE, ADDRESS_SPACE))
    os.nice(max(0, 19 - os.nice(0)))
    try:
        r = run(a.expected, a.out, a.receipt_dir, a.transient_root, keep_source=a.keep_source_for_comparison)
    except (Refused, conv.Refused) as error:
        print(json.dumps({"status": "refused", "reason": str(error)}))
        return 2
    print(json.dumps({k: r[k] for k in ("status", "rows", "b3d_sha256")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
