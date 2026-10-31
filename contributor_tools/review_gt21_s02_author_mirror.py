#!/usr/bin/env python3
"""GT21-S02: list the authors' 2024 Dropbox copy of Camargo et al. (metadata only).

``fetch`` walks the public folder listing (names, byte sizes, modification
times) for the requested participants, one request per second, and writes one
listing JSON per participant. It never downloads a data file. ``summarize``
prints per-participant structure (sessions, modes, channel folders, file
counts and bytes) and, for participants held locally, compares relative paths
and byte sizes with the local tree using os.stat only (no file is opened).

    python3 contributor_tools/review_gt21_s02_author_mirror.py fetch OUT AB12 AB15 ...
    python3 contributor_tools/review_gt21_s02_author_mirror.py summarize OUT
    python3 contributor_tools/review_gt21_s02_author_mirror.py plan OUT PLAN_DIR
    python3 contributor_tools/review_gt21_s02_author_mirror.py audit AUDIT.json PLAN_DIR OUT [OUT...]
    python3 contributor_tools/review_gt21_s02_author_mirror.py v1compare V1.zip OUT/AB17.json

``plan`` writes plan-only guarded-launcher specs (never launched here) and
checks each with guarded_launcher.validate_spec in-process.
"""
import hashlib
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

EPIC_PAGE = "https://www.epic.gatech.edu/opensource-biomechanics-camargo-et-al/"
LAB_LINK = "https://www.dropbox.com/sh/lhurwcy0znonh56/AAAPmVdrxh7M6FW-UYHyPHyza?dl=0"
LINK_KEY = "i2ee8z2nxjwkf3mdocw63"
ROOT_HASH = "AEuNRES_bD2n_Yt0xYzjHQ4"
RLKEY = "eiqcgo6gyvf4bnfgduq419yyh"
LIST_URL = "https://www.dropbox.com/list_shared_link_folder_entries"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
LOCAL_ROOT = (Path(__file__).resolve().parent / "conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET")
MODES = ("levelground", "ramp", "stair", "treadmill")
HREF = re.compile(r"/scl/fo/" + LINK_KEY + r"/([A-Za-z0-9_-]+)/([^?]+)\?")
MAX_RESPONSE = 4_000_000


def _opener():
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [("User-Agent", UA)]
    with opener.open(LAB_LINK, timeout=60) as r:
        landing = r.geturl()
        r.read(MAX_RESPONSE)
    token = next(c.value for c in jar if c.name == "t")
    return opener, token, landing


def _list(opener, token, secure_hash, sub_path):
    entries, voucher, raw_hashes = [], None, []
    while True:
        form = {"is_xhr": "true", "t": token, "link_key": LINK_KEY, "link_type": "c",
                "secure_hash": secure_hash, "sub_path": sub_path, "rlkey": RLKEY}
        if voucher:
            form["voucher"] = voucher
        req = urllib.request.Request(LIST_URL, data=urllib.parse.urlencode(form).encode(),
                                     headers={"Origin": "https://www.dropbox.com",
                                              "X-Requested-With": "XMLHttpRequest"})
        with opener.open(req, timeout=60) as r:
            body = r.read(MAX_RESPONSE + 1)
        if len(body) > MAX_RESPONSE:
            raise ValueError("listing response larger than bound")
        raw_hashes.append(hashlib.sha256(body).hexdigest())
        page = json.loads(body)
        entries += page["entries"]
        time.sleep(1.0)
        if not page.get("has_more_entries"):
            return entries, page.get("total_num_entries"), raw_hashes
        voucher = page["next_request_voucher"]


def fetch(out, subjects):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    opener, token, landing = _opener()
    root, total, raw = _list(opener, token, ROOT_HASH, "")
    root_rows = [{"name": e["filename"], "is_dir": e["is_dir"], "bytes": e.get("bytes"),
                  "ts": e.get("ts"), "href": e["href"]} for e in root]
    (out / "root.json").write_text(json.dumps({
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lab_page": EPIC_PAGE, "lab_link": LAB_LINK, "lab_link_resolves_to": landing,
        "total_num_entries": total, "raw_response_sha256": raw, "entries": root_rows}, indent=1))
    by_name = {r["name"]: r for r in root_rows}
    for subject in subjects:
        if subject not in by_name:
            (out / f"{subject}.json").write_text(json.dumps({"subject": subject, "present": False}))
            continue
        files, dirs, raws, queue = [], [], [], [by_name[subject]["href"]]
        while queue:
            m = HREF.search(queue.pop(0))
            secure_hash, path = m.group(1), urllib.parse.unquote(m.group(2))
            entries, total, raw = _list(opener, token, secure_hash, "/" + path)
            if total is not None and total != len(entries):
                raise ValueError(f"{path}: {len(entries)} entries, listing says {total}")
            raws += raw
            dirs.append({"path": path, "entries": len(entries)})
            for e in entries:
                rel = path + "/" + e["filename"]
                if e["is_dir"]:
                    queue.append(e["href"])
                else:
                    files.append({"path": rel, "bytes": e["bytes"], "ts": e["ts"],
                                  "file_id": e.get("file_id"), "revision_id": e.get("revision_id")})
        (out / f"{subject}.json").write_text(json.dumps({
            "subject": subject, "present": True,
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "folder_href": by_name[subject]["href"], "requests": len(raws),
            "raw_response_sha256": raws, "directories": dirs, "files": files}, indent=1))
        print(subject, len(dirs), "folders", len(files), "files", flush=True)


def structure(files, subject):
    """Per-participant layout from relative paths <subject>/<session>/<mode>/<channel>/<file>."""
    sessions, osim, channels, static, other = set(), [], Counter(), Counter(), []
    trials = {m: set() for m in MODES}
    for f in files:
        parts = f["path"].split("/")
        if parts[0] != subject:
            other.append(f["path"])
        elif parts[1] == "osimxml":
            osim.append("/".join(parts[2:]))
        elif len(parts) == 5 and parts[2] in MODES:
            sessions.add(parts[1]); channels[(parts[2], parts[3])] += 1
            if parts[3] == "conditions":
                trials[parts[2]].add(parts[4])
        elif len(parts) == 5 and parts[2] == "static":
            sessions.add(parts[1]); static[parts[3]] += 1
        else:
            other.append(f["path"])
    by_mode = {m: {c: n for (mm, c), n in sorted(channels.items()) if mm == m} for m in MODES}
    return {
        "files": len(files), "bytes": sum(f["bytes"] for f in files),
        "sessions": sorted(sessions), "osimxml_files": sorted(osim),
        "recordings_by_mode_conditions_files": {m: len(trials[m]) for m in MODES},
        "channel_files_by_mode": by_mode,
        "static_files_by_channel": dict(sorted(static.items())),
        "ik_offset_in_all_four_modes": all(by_mode[m].get("ik_offset", 0) ==
                                           len(trials[m]) > 0 for m in MODES),
        "every_channel_matches_conditions_count": all(
            set(by_mode[m].values()) == {len(trials[m])} for m in MODES),
        "unclassified_paths": other,
        "latest_modification_utc": datetime.fromtimestamp(
            max(f["ts"] for f in files), timezone.utc).isoformat() if files else None,
    }


def local_compare(files, subject):
    root = LOCAL_ROOT / subject
    if not root.is_dir():
        return None
    local = {}
    for dirpath, _, names in os.walk(root):
        for n in names:
            p = Path(dirpath) / n
            local[subject + "/" + p.relative_to(root).as_posix()] = p.stat().st_size
    remote = {f["path"]: f["bytes"] for f in files}
    same = sorted(set(local) & set(remote))
    return {"local_files": len(local), "mirror_files": len(remote), "common_paths": len(same),
            "size_equal": sum(local[p] == remote[p] for p in same),
            "size_differs": [p for p in same if local[p] != remote[p]],
            "local_only": sorted(set(local) - set(remote)),
            "mirror_only": sorted(set(remote) - set(local))}


def summarize(out):
    out = Path(out)
    result = {}
    for p in sorted(out.glob("AB*.json")):
        d = json.loads(p.read_text())
        if not d.get("present"):
            result[d["subject"]] = {"present": False}
            continue
        result[d["subject"]] = {"present": True, "folder_href": d["folder_href"],
                                "listing_requests": d["requests"],
                                "listing_file_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                                "structure": structure(d["files"], d["subject"]),
                                "local_size_comparison": local_compare(d["files"], d["subject"])}
    print(json.dumps(result, indent=1))


ACQUIRE_SCRIPT = "contributor_tools/acquire_gt21_author_mirror_participant.py"
REVIEW_SCRIPT = "contributor_tools/review_gt21_s02_author_mirror.py"  # imported by the acquisition script
DEST = Path("/mnt/s/locomotion_data/gt21_author_mirror_2024")
RESERVE_MIB = 15 * 1024
ROOT = Path(__file__).resolve().parents[1]


def plan(listing_dir, plan_dir):
    """Write one plan-only guarded-launcher spec per present participant and validate it."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from contributor_tools.guarded_launcher import validate_spec
    listing_dir, plan_dir = Path(listing_dir), Path(plan_dir)
    plan_dir.mkdir(parents=True, exist_ok=True)
    out = {}
    for p in sorted(listing_dir.glob("AB*.json")):
        d = json.loads(p.read_text())
        if not d.get("present") or (LOCAL_ROOT / d["subject"]).is_dir():
            continue  # absent from the 2024 copy, or already held locally (comparison only)
        subject = d["subject"]
        expected = plan_dir / f"{subject}_expected_listing.json"
        expected.write_text(json.dumps({"subject": subject, "folder_href": d["folder_href"],
                                        "fetched_at_utc": d["fetched_at_utc"],
                                        "files": [{k: f[k] for k in ("path", "bytes", "ts")}
                                                  for f in d["files"]]}, indent=0))
        listing_mib = -(-sum(f["bytes"] for f in d["files"]) // 1024**2)
        spec = {
            "job_id": f"gt21-s02-author-mirror-{subject}",
            "command": ["python3", ACQUIRE_SCRIPT, "--subject", subject,
                        "--expected-listing", str(expected), "--out", str(DEST / subject),
                        "--receipt-dir", str(DEST / "acquisition_receipts" / subject), "--run"],
            "output_root": str(DEST / subject),
            "receipt_path": str(DEST / "launcher_receipts" / f"{subject}.json"),
            "bindings": {ACQUIRE_SCRIPT: _sha(ROOT / ACQUIRE_SCRIPT), REVIEW_SCRIPT: _sha(ROOT / REVIEW_SCRIPT),
                         str(expected): hashlib.sha256(expected.read_bytes()).hexdigest()},
            "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816},
            "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            # 15 GiB reserve (as in the version 1 tool) plus the archive and a later extraction of equal size.
            "disk_admission": [{"path": str(DEST.parent), "min_free_mib": RESERVE_MIB + 2 * listing_mib}],
            # Receipts go to acquisition_receipts/<subject>, outside the output root.
            "expected_output_names": [f"{subject}.zip"],
            "address_space_mib": 256,
        }
        validate_spec(spec)
        spec_path = plan_dir / f"{subject}_spec.json"
        spec_path.write_text(json.dumps(spec, indent=1) + "\n")
        out[subject] = {"spec": str(spec_path), "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
                        "expected_listing": str(expected),
                        "expected_listing_sha256": spec["bindings"][str(expected)],
                        "validate_spec": "passed in-process; script hashes bound; not launched",
                        "listing_mib": listing_mib}
    print(json.dumps(out, indent=1))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# Facts recorded by hand on 2026-10-31 from small fetches (receipts hashed here).
FACTS = {
    "sources_checked": [
        {"source": "Local README (CAMARGO_ET_AL_J_BIOMECH_DATASET/README.txt)",
         "finding": "Points to the EPIC lab page for the Dropbox copy and to Mendeley version 2 DOIs "
                    "(fcgm3chfff.2, k9kvm5tn3f.2, jj3r5f9pnf.2). Documents static and ik_offset added 4/28/2024."},
        {"source": EPIC_PAGE, "fetched_html_sha256": "3436aa140d8cfe443b0e753c2c7b883ebdcbc1f149f7a3a5b9dc1acd2a1f7a10",
         "finding": "One data link: 'a public-view Dropbox directory' (" + LAB_LINK + "); 'We recommend to "
                    "download each subject individually (~1GB per subject)'. No Box, Google Drive or SimTK link."},
        {"source": "Dropbox shared folder (the lab link redirects to it)",
         "finding": "Root folder CAMARGO_ET_AL_J_BIOMECH_DATASET, the same name as the local source root; 25 entries, "
                    "no further pages: 22 participant folders (AB06-AB30 without AB22, AB26, AB29), scripts, README.txt, SubjectInfo.mat."},
        {"source": "Mendeley Data parts 1-3", "finding": "Rechecked by GT21-S01 on 2026-10-31: only version 1 "
                    "(2021-02-26) and version 2 (2021-10-18); no 2024 version. Not re-queried here."},
        {"source": "Web search (Camargo dataset, 2024 update, static/ik_offset)",
         "finding": "No other copy found. SimTK, Box and Google Drive were not queried directly; the lab page links none."},
    ],
    "small_file_identity": {
        "README.txt": {"mirror_bytes": 5245, "mirror_modified_utc": "2024-04-29T21:53:31Z",
                       "sha256": "45282345f808b0eae6792ef728d8f1ba15f2ab5e3645123aab8c275b0831bace",
                       "equals_local": True},
        "SubjectInfo.mat": {"mirror_bytes": 1281, "mirror_modified_utc": "2020-11-21T00:59:42Z",
                            "sha256": "bc990b2c182e0cfc7b405b99fb429026585c224ce6d1ff5249734ec89cb2ce08",
                            "equals_local": True, "equals_publisher_v1_v2_record": True},
    },
    "download_channel": {
        "method": "Participant folder link with dl=1: Dropbox builds AB<nn>.zip on request.",
        "head_receipt_AB12_20261031": {"redirect": "302 to a dl.dropboxusercontent.com zip_download_get URL",
                                       "final_status": 200, "content_disposition": "attachment; filename=AB12.zip",
                                       "content_length": 1165363841,
                                       "listing_bytes": 1165001799,
                                       "difference_bytes": 362042,
                                       "note": "Survey request only; the acquisition script makes no HEAD request. About 200 bytes of ZIP header per entry, consistent with stored members; not verified. Inside the script's Content-Length rule (listed bytes + 1 KiB per file + 64 KiB = 1,878,016 bytes allowance for AB12)."},
        "publisher_checksums": "None. Dropbox lists names, byte sizes, modification times and revision ids only. "
                               "The ZIP is generated on request, so its own SHA-256 is a receipt, not a stable identity; "
                               "per-member SHA-256 and the listing are the identity LocoHub records.",
    },
    "modification_history_from_listings": {
        "finding": "In all seven listed participants (the six plus AB14) the 2024-04-08 files are exactly the ik_offset files "
                   "of the four modes plus static/ik, static/ik_offset and static/markers. Every ramp/id file was rewritten on "
                   "2021-09-23/24, after version 1 (2021-02-26) and before version 2 (2021-10-18). All other files carry 2019-2020 "
                   "dates, except AB28/osimxml/opensim.log (10,362 bytes, 2026-10-11), absent from the other participants: the "
                   "folder is a live working copy that changed this month.",
        "limit": "Dropbox modification times are metadata, not content proof.",
    },
    "ab14_equivalence_plan": {
        "plan": "converted_datasets/reconversion_v2/gt21_ab14_v1_equivalence_20261031/plan.json",
        "plan_sha256": "ecc3c2490fd9d2912523101e8c188c6ae7fee65321f83a2f156a989b54c3907e",
        "status": "superseded_not_launched",
        "why": "Its question (did the 2024 copy change version 1 trial files?) is now answered more cheaply by AB17: "
               "the version 1 AB17 archive is already local, and the 2024 AB17 folder is acquired under D-GT21-S01-1 = C anyway. "
               "A size comparison from the AB17 central directory and the 2024 listing is already done (see ab17_v1_vs_2024_sizes). "
               "The CRC32 comparison runs after the AB17 2024 download with no extra 0.96 GB fetch. Local AB14 already equals the "
               "2024 listing by path and byte size (1,722 of 1,722).",
        "keep_as": "Fallback only, if the AB17 CRC comparison shows differences outside ramp/id.",
    },
    "acquisition_script_requirements": [
        "contributor_tools/acquire_gt21_author_mirror_participant.py implements these (written 2026-10-31, awaiting review); each spec binds its hash and this script's hash, which it imports.",
        "Before download: re-list the participant folder and refuse if any path, byte size or modification time differs from the bound expected listing.",
        "Create the output root itself (the launcher refuses an existing one); never write into the active 16-participant source root.",
        "Stream the dl=1 ZIP to <subject>.zip.partial with a 1 MiB buffer and a 1 MiB/s ceiling; require Content-Length between the listed bytes and the listed bytes plus 1 KiB per listed file plus 64 KiB (no HEAD request is made); compute SHA-256 while writing; fsync.",
        "Run every check on the .partial file. Read only the ZIP central directory, then require: no symlink, encrypted or unsupported members; member paths equal the expected listing, each uncompressed size equals its listed bytes, one session folder, the listed osimxml files (3; AB28 also opensim.log, recorded but unused), 12 channel folders in each of the four modes with equal counts, ik_offset count equal to conditions count, and static/ik, static/ik_offset, static/markers.",
        "Stream each member through zipfile (CRC32 checked on read, 1 MiB blocks, no extraction, no MAT decoding) and record path, bytes, CRC32 and SHA-256.",
        "Re-list the folder after the download and refuse if it differs from the bound listing (paths, bytes, modification times, folder link); a same-size edit shows as a changed time.",
        "Only after all checks pass: write member_manifest.json and publish <subject>.zip with a no-clobber link. A rejected archive is kept as <subject>.zip.rejected (or .partial) and never carries the final name.",
        "Keep RLIMIT_AS at 256 MiB; check disk reserve (15 GiB plus remaining bytes) and Windows free memory (>= 2048 MiB) every 15 s; stop on a STOP file; preserve partial files on failure.",
        "Write acquisition_started.json, acquisition_result.json and member_manifest.json with exclusive creation into acquisition_receipts/<subject>, outside the output root, which holds only <subject>.zip; scientific_approval false.",
        "After the AB17 acquisition, contributor_tools/compare_gt21_v1_vs_author_mirror_crc.py compares the local version 1 central directory with the manifest CRC32 values (no network, no member read).",
    ],
    "acquisition_order": {
        "first": "AB17",
        "why": "Its version 1 archive is already local, so its 2024 download also settles the CRC-level version 1 versus 2024 question. "
               "Then AB15, AB12, AB23, AB28, AB19 by increasing listing bytes, one job per tool call, each after a fresh admission.",
        "coordination": "AB17 is also handled by GT21-A01 (version 1 archive; extraction blocked). The 2024 AB17 download goes to a separate root and does not touch the version 1 files.",
    },
    "jose_decision": "None drafted. All six participants are present in the 2024 copy, so D-GT21-S01-1 = C can proceed without a new choice. "
                     "The version 1 versus 2024 ramp/id differences concern only how the 2024 copy is cross-checked, not which source is used.",
    "not_checked": [
        "File bytes of the six participants (no data file downloaded); only names, sizes and modification times.",
        "Byte identity of the 15 other local participants to the 2024 listing (only AB14 compared, by size).",
        "Whether the 2021-09 ramp/id rewrite changed content in files whose size is unchanged.",
        "Why AB28 holds a 2026-10-11 opensim.log, and whether the authors plan further changes to the folder.",
    ],
    "limitations": [
        "Listing endpoint is Dropbox's web interface, not a documented API; it may change.",
        "Plan only: no job launched, no archive downloaded or extracted, no conversion.",
    ],
}


def audit(out_json, plan_dir, *listing_dirs):
    """Compose the GT21-S02 audit from listings, the plan specs and recorded small-file facts."""
    plan_dir = Path(plan_dir)
    root = json.loads((Path(listing_dirs[0]) / "root.json").read_text())
    participants, held = {}, {}
    for d in listing_dirs:
        for p in sorted(Path(d).glob("AB*.json")):
            held[p.stem] = p
    for subject in sorted(held):
        d = json.loads(held[subject].read_text())
        row = {"present_in_2024_copy": d.get("present", False), "listing_sha256": _sha(held[subject])}
        if d.get("present"):
            row.update(folder_url=d["folder_href"], listed_at_utc=d["fetched_at_utc"],
                       listing_requests=d["requests"], structure=structure(d["files"], subject),
                       local_size_comparison=local_compare(d["files"], subject))
            spec = plan_dir / f"{subject}_spec.json"
            if spec.is_file():
                row["acquisition_spec"] = {"path": str(spec), "sha256": _sha(spec),
                                           "spec": json.loads(spec.read_text())}
        participants[subject] = row
    root_rows = [{k: e[k] for k in ("name", "is_dir", "bytes", "ts")} for e in root["entries"]]
    report = {
        "task_id": "GT21-S02", "status": "review", "scientific_approval": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "builder": {"path": "contributor_tools/review_gt21_s02_author_mirror.py", "sha256": _sha(__file__)},
        "decision_context": "D-GT21-S01-1 = C (2026-10-31): acquire the six from the authors' 2024 copy and record LocoHub hashes at download.",
        "two_thousand_twenty_four_copy": {
            "lab_page": EPIC_PAGE, "lab_page_link": LAB_LINK,
            "lab_link_resolves_to": root["lab_link_resolves_to"],
            "root_folder_listed_at_utc": root["fetched_at_utc"],
            "root_total_entries": root["total_num_entries"],
            "root_entries": root_rows,
            "root_listing_raw_sha256": root["raw_response_sha256"],
        },
        **FACTS,
        "participants": participants,
    }
    cmp_path = plan_dir / "AB17_v1compare.json"
    if cmp_path.is_file():
        report["ab17_v1_vs_2024_sizes"] = {"path": str(cmp_path), "sha256": _sha(cmp_path),
                                           **json.loads(cmp_path.read_text())}
    Path(out_json).write_text(json.dumps(report, indent=1) + "\n")


def v1_compare(zip_path, listing):
    """Version 1 ZIP central directory (names, sizes) against a 2024 listing; no member is read."""
    import zipfile
    with zipfile.ZipFile(zip_path) as z:
        v1 = {i.filename: i.file_size for i in z.infolist() if not i.is_dir()}
    mirror = {f["path"]: f["bytes"] for f in json.loads(Path(listing).read_text())["files"]}

    def folder(p):
        parts = p.split("/")
        return parts[1] if parts[1] == "osimxml" else "/".join(parts[2:4])
    counts = {}
    for p in set(v1) | set(mirror):
        kind = ("mirror_only" if p not in v1 else "v1_only" if p not in mirror
                else "same_size" if v1[p] == mirror[p] else "size_differs")
        counts.setdefault(folder(p), Counter())[kind] += 1
    differs = sorted(p for p in v1 if p in mirror and v1[p] != mirror[p])
    print(json.dumps({"zip_sha256_name": Path(zip_path).name, "listing_sha256": _sha(listing),
                      "v1_files": len(v1), "mirror_files": len(mirror), "v1_bytes": sum(v1.values()),
                      "totals": dict(sum(counts.values(), Counter())),
                      "by_folder": {k: dict(v) for k, v in sorted(counts.items())},
                      "size_differs": [{"path": p, "v1_bytes": v1[p], "mirror_bytes": mirror[p]}
                                       for p in differs]}, indent=1))


if __name__ == "__main__":
    if sys.argv[1:2] == ["v1compare"]:
        v1_compare(sys.argv[2], sys.argv[3])
        sys.exit(0)
    if sys.argv[1:2] == ["audit"]:
        audit(*sys.argv[2:])
        sys.exit(0)
    if sys.argv[1:2] == ["fetch"]:
        fetch(sys.argv[2], sys.argv[3:])
    elif sys.argv[1:2] == ["summarize"]:
        summarize(sys.argv[2])
    elif sys.argv[1:2] == ["plan"]:
        plan(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
