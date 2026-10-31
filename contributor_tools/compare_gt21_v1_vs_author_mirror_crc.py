#!/usr/bin/env python3
"""GT21-S02: compare a publisher version 1 participant ZIP with its 2024 acquisition by CRC32.

Reads only the version 1 ZIP central directory (names, sizes, CRC32; no member
is read or extracted) and the member_manifest.json written by
acquire_gt21_author_mirror_participant.py. No network use, no MAT decoding.
Writes one report with exclusive creation.

Each relative path is classified as identical (size and CRC32 equal),
crc_differs (same size), size_differs, v1_only or mirror_only. Paths are then
marked expected or unexpected: 2024-only files are expected in ik_offset and
static folders; differences are expected to be possible in ramp/id, which the
authors rewrote in September 2021 (listing modification times). Everything
else is unexpected. CRC32 equality detects change; it is not a cryptographic proof.

    python3 contributor_tools/compare_gt21_v1_vs_author_mirror_crc.py --subject AB17 \
        --v1-zip /mnt/s/locomotion_data/gt21_missing_participants_v1/AB17/<sha>.zip \
        --member-manifest /mnt/s/locomotion_data/gt21_author_mirror_2024/acquisition_receipts/AB17/member_manifest.json \
        --out REPORT.json
"""
import argparse
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REWRITTEN_2021 = {("ramp", "id")}


def folder(path):
    """(mode, channel) for <subject>/<session>/<mode>/<channel>/<file>; osimxml otherwise."""
    parts = path.split("/")
    if len(parts) > 1 and parts[1] == "osimxml":
        return ("osimxml", "")
    return (parts[2], parts[3]) if len(parts) == 5 else ("other", "")


def v1_directory(zip_path, subject):
    with zipfile.ZipFile(zip_path) as z:
        rows = {}
        for info in z.infolist():
            if info.is_dir():
                continue
            name = info.filename.lstrip("/")
            if not name.startswith(subject + "/"):
                name = f"{subject}/{name}"
            if name in rows:
                raise ValueError(f"duplicate version 1 member {name}")
            rows[name] = (info.file_size, info.CRC)
    return rows


def compare(v1, mirror):
    """v1/mirror: {path: (bytes, crc32 int)} -> report body."""
    kinds, details = {}, defaultdict(list)
    for path in sorted(set(v1) | set(mirror)):
        if path not in mirror:
            kind = "v1_only"
        elif path not in v1:
            kind = "mirror_only"
        elif v1[path] == mirror[path]:
            kind = "identical"
        elif v1[path][0] == mirror[path][0]:
            kind = "crc_differs"
        else:
            kind = "size_differs"
        kinds[path] = kind
        if kind == "identical":
            continue
        mode, channel = folder(path)
        expected = ((kind == "mirror_only" and (channel == "ik_offset" or mode == "static"))
                    or (kind in ("crc_differs", "size_differs") and (mode, channel) in REWRITTEN_2021))
        row = {"path": path, "kind": kind,
               "v1": None if path not in v1 else {"bytes": v1[path][0], "crc32": f"{v1[path][1]:08x}"},
               "mirror": None if path not in mirror else {"bytes": mirror[path][0], "crc32": f"{mirror[path][1]:08x}"}}
        details["expected" if expected else "unexpected"].append(row)
    by_folder = defaultdict(Counter)
    for path, kind in kinds.items():
        by_folder["/".join(x for x in folder(path) if x)][kind] += 1
    return {"totals": dict(Counter(kinds.values())),
            "by_folder": {k: dict(v) for k, v in sorted(by_folder.items())},
            "expected_differences": details["expected"],
            "unexpected_differences": details["unexpected"],
            "unexpected_count": len(details["unexpected"])}


def run(subject, v1_zip, member_manifest, out):
    out = Path(out)
    if out.exists():
        raise FileExistsError(f"{out} exists; reports are never overwritten")
    manifest_bytes = Path(member_manifest).read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("subject") != subject:
        raise ValueError("member manifest is for another participant")
    mirror = {}
    for row in manifest["files"]:
        if row["path"] in mirror:
            raise ValueError(f"duplicate manifest path {row['path']}")
        mirror[row["path"]] = (row["bytes"], int(row["crc32"], 16))
    report = {"task_id": "GT21-S02", "subject": subject, "scientific_approval": False,
              "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "v1_zip": str(v1_zip), "v1_zip_bytes": Path(v1_zip).stat().st_size,
              "member_manifest": str(member_manifest),
              "member_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
              "mirror_zip_sha256": manifest.get("zip_sha256"),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "method": "version 1 central directory (size, CRC32) against the acquisition manifest; "
                        "no member read, no network",
              **compare(v1_directory(v1_zip, subject), mirror)}
    with out.open("x") as stream:
        stream.write(json.dumps(report, indent=1) + "\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--v1-zip", type=Path, required=True)
    parser.add_argument("--member-manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    report = run(args.subject, args.v1_zip, args.member_manifest, args.out)
    print(json.dumps({"totals": report["totals"], "unexpected_count": report["unexpected_count"]}))


if __name__ == "__main__":
    main()
