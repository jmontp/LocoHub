"""Synthetic participant listings and ZIPs only; no network, no research archive."""
import hashlib
import io
import json
import zipfile
import zlib

import pytest

from contributor_tools import acquire_gt21_author_mirror_participant as acq
from contributor_tools import compare_gt21_v1_vs_author_mirror_crc as cmp

SUBJECT = "AB99"  # synthetic participant id, not part of the GT21 cohort
SESSION = "01_01_2000"
HREF = "https://www.dropbox.com/scl/fo/x/AAAA/AB99?rlkey=synthetic&dl=0"
GIB = 1024**3


def synthetic_files(drop=None):
    """{path: bytes} for a minimal GT21-shaped participant (one trial per mode)."""
    files = {f"{SUBJECT}/osimxml/{SUBJECT}.osim": b"synthetic model"}
    for mode in ("levelground", "ramp", "stair", "treadmill"):
        for channel in sorted(acq.CHANNELS):
            path = f"{SUBJECT}/{SESSION}/{mode}/{channel}/{mode}_01.mat"
            files[path] = f"synthetic {path}".encode()
    for channel in sorted(acq.STATIC):
        path = f"{SUBJECT}/{SESSION}/static/{channel}/static_01.mat"
        files[path] = f"synthetic {path}".encode()
    return {p: b for p, b in files.items() if not (drop and drop in p)}


def listing(files, href=HREF):
    return {"subject": SUBJECT, "folder_href": href,
            "files": [{"path": p, "bytes": len(b), "ts": 1} for p, b in sorted(files.items())]}


def make_zip(files, prefixed=False):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as z:
        for path, data in files.items():
            z.writestr(path if prefixed else path.split("/", 1)[1], data)
    return buffer.getvalue()


class Response:
    def __init__(self, body, length=None, name=f"{SUBJECT}.zip", status=200):
        self._stream, self.status = io.BytesIO(body), status
        self.headers = {"Content-Length": str(len(body) if length is None else length),
                        "Content-Disposition": f'attachment; filename="{name}"',
                        "Content-Type": "application/zip"}

    def read(self, n=-1):
        return self._stream.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def case(tmp_path):
    files = synthetic_files()
    expected = tmp_path / "plan" / "expected.json"
    expected.parent.mkdir()
    expected.write_text(json.dumps(listing(files)))
    calls = []

    def run(body=None, current=None, free=100 * GIB, opener=None, lister=None, **kw):
        body = make_zip(files) if body is None else body

        def default_opener(url):
            calls.append(url)
            return Response(body)
        return acq.acquire(SUBJECT, expected, tmp_path / "data" / SUBJECT, tmp_path / "receipts" / SUBJECT,
                           lister=lister or (lambda s: current or listing(files)),
                           opener=opener or default_opener,
                           free_bytes=lambda p: free, free_mib=lambda: 8192, rate=0, **kw)
    return {"files": files, "expected": expected, "run": run, "calls": calls,
            "out": tmp_path / "data" / SUBJECT, "receipts": tmp_path / "receipts" / SUBJECT}


def receipt(case):
    return json.loads((case["receipts"] / "acquisition_result.json").read_text())


@pytest.mark.parametrize("prefixed", [False, True])
def test_fake_zip_is_hashed_and_recorded_outside_data(case, prefixed):
    body = make_zip(case["files"], prefixed=prefixed)
    result = case["run"](body=body)
    assert result["status"] == "acquired_verified_not_extracted"
    assert sorted(p.name for p in case["out"].iterdir()) == [f"{SUBJECT}.zip"]
    assert result["zip_sha256"] == hashlib.sha256(body).hexdigest()
    assert case["calls"] == [HREF.replace("dl=0", "dl=1")]
    manifest = json.loads((case["receipts"] / "member_manifest.json").read_text())
    rows = {r["path"]: r for r in manifest["files"]}
    assert set(rows) == set(case["files"])
    for path, data in case["files"].items():
        assert rows[path]["sha256"] == hashlib.sha256(data).hexdigest()
        assert rows[path]["crc32"] == f"{zlib.crc32(data):08x}"
        assert rows[path]["bytes"] == len(data)
    assert receipt(case)["scientific_approval"] is False


def test_zip_member_size_mismatch_is_refused_and_preserved(case):
    changed = dict(case["files"])
    path = next(p for p in changed if "/ramp/id/" in p)
    changed[path] += b"x"
    with pytest.raises(acq.Refused, match="ZIP differs from listing"):
        case["run"](body=make_zip(changed))
    rejected = case["out"] / f"{SUBJECT}.zip.rejected"
    assert receipt(case)["status"] == "failed_preserved"
    assert receipt(case)["rejected_path"] == str(rejected)
    assert sorted(p.name for p in case["out"].iterdir()) == [rejected.name]  # never the final name
    assert rejected.read_bytes() == make_zip(changed)
    assert not (case["receipts"] / "member_manifest.json").exists()


def test_unlisted_zip_member_is_refused(case):
    extra = {**case["files"], f"{SUBJECT}/osimxml/opensim.log": b"log"}
    with pytest.raises(acq.Refused, match="unlisted"):
        case["run"](body=make_zip(extra))


def test_changed_listing_refused_before_download(case):
    current = listing({**case["files"], f"{SUBJECT}/osimxml/opensim.log": b"live log"})
    with pytest.raises(acq.Refused, match="current listing differs"):
        case["run"](current=current)
    assert case["calls"] == [] and not case["out"].exists()
    assert receipt(case)["listing_differences"] == [f"only in current listing: {SUBJECT}/osimxml/opensim.log"]


def test_changed_size_or_time_in_listing_refused(case):
    current = listing(case["files"])
    current["files"][0]["ts"] = 2
    with pytest.raises(acq.Refused, match="current listing differs"):
        case["run"](current=current)
    assert case["calls"] == []


def test_same_size_change_during_download_refused_and_not_published(case):
    calls = []

    def lister(subject):
        calls.append(subject)
        current = listing(case["files"])
        if len(calls) == 2:  # second listing, after the download: one file edited, same size
            current["files"][3]["ts"] += 60
        return current
    with pytest.raises(acq.Refused, match="listing changed during the download"):
        case["run"](lister=lister)
    assert len(calls) == 2
    result = receipt(case)
    assert result["status"] == "failed_preserved"
    assert len(result["listing_differences_after_download"]) == 1
    assert sorted(p.name for p in case["out"].iterdir()) == [f"{SUBJECT}.zip.rejected"]
    assert not (case["receipts"] / "member_manifest.json").exists()


def test_success_relists_after_download(case):
    calls = []

    def lister(subject):
        calls.append(subject)
        return listing(case["files"])
    assert case["run"](lister=lister)["status"] == "acquired_verified_not_extracted"
    assert calls == [SUBJECT, SUBJECT]


def test_symlink_member_refused(case):
    body = io.BytesIO()
    with zipfile.ZipFile(body, "w") as z:
        for path, data in case["files"].items():
            info = zipfile.ZipInfo(path.split("/", 1)[1])
            if "/gon/" in path and "ramp" in path:
                info.external_attr = (0o120777 << 16)
            z.writestr(info, data)
    with pytest.raises(acq.Refused, match="symlink"):
        case["run"](body=body.getvalue())
    assert not (case["out"] / f"{SUBJECT}.zip").exists()


def test_short_disk_refused_before_output_root(case):
    with pytest.raises(acq.Refused, match="disk free"):
        case["run"](free=acq.RESERVE)
    assert case["calls"] == [] and not case["out"].exists()
    assert receipt(case)["status"] == "failed_preserved"


def test_pre_existing_output_root_untouched(case):
    case["out"].mkdir(parents=True)
    (case["out"] / "earlier.zip").write_bytes(b"earlier attempt")
    with pytest.raises(acq.Refused, match="already exists"):
        case["run"]()
    assert (case["out"] / "earlier.zip").read_bytes() == b"earlier attempt"
    assert not case["receipts"].exists() and case["calls"] == []


def test_pre_existing_receipts_never_overwritten(case):
    case["receipts"].mkdir(parents=True)
    with pytest.raises(acq.Refused, match="already exists"):
        case["run"]()
    assert list(case["receipts"].iterdir()) == [] and not case["out"].exists()


def test_receipts_inside_output_refused(case, tmp_path):
    with pytest.raises(acq.Refused, match="separate"):
        acq.acquire(SUBJECT, case["expected"], tmp_path / "d", tmp_path / "d" / "r", lister=None, opener=None)


@pytest.mark.parametrize("drop", ["/treadmill/ik_offset/", "/static/markers/"])
def test_listing_without_ik_offset_or_static_refused(tmp_path, drop):
    path = tmp_path / "expected.json"
    path.write_text(json.dumps(listing(synthetic_files(drop=drop))))
    with pytest.raises(acq.Refused, match="layout"):
        acq.load_expected(path, SUBJECT)


def test_content_length_outside_listing_bounds_refused(case):
    body = make_zip(case["files"])
    with pytest.raises(acq.Refused, match="Content-Length"):
        case["run"](opener=lambda url: Response(body, length=10))


def test_response_that_is_not_the_participant_zip_refused(case):
    body = make_zip(case["files"])
    with pytest.raises(acq.Refused, match="not the participant ZIP"):
        case["run"](opener=lambda url: Response(body, name="other.zip"))


def test_corrupted_member_bytes_fail_crc(case):
    body = bytearray(make_zip(case["files"]))
    marker = b"synthetic " + next(iter(sorted(case["files"]))).encode()
    body[body.index(marker) + 3] ^= 0xFF  # flip a stored payload byte, same length
    with pytest.raises(zipfile.BadZipFile):
        case["run"](body=bytes(body))
    assert receipt(case)["status"] == "failed_preserved"
    assert sorted(p.name for p in case["out"].iterdir()) == [f"{SUBJECT}.zip.rejected"]


def test_unsafe_member_name_refused():
    with pytest.raises(acq.Refused, match="unsafe"):
        acq.member_path("../escape.mat", SUBJECT, prefixed=False)


def test_stream_stops_on_stop_file_guard():
    def guard(_):
        raise acq.Refused("stopped by request (STOP file)")
    out = io.BytesIO()
    with pytest.raises(acq.Refused, match="STOP"):
        acq.stream_to(io.BytesIO(b"abc"), out, 3, guard, rate=0)
    assert out.getvalue() == b""


# -------------------------------------------------------- CRC comparison

def manifest_for(files, path):
    rows = [{"path": p, "bytes": len(b), "crc32": f"{zlib.crc32(b):08x}", "sha256": hashlib.sha256(b).hexdigest()}
            for p, b in sorted(files.items())]
    path.write_text(json.dumps({"subject": SUBJECT, "zip_sha256": "0" * 64, "files": rows}))
    return path


def test_crc_comparison_classifies_expected_and_unexpected(tmp_path):
    mirror = synthetic_files()
    v1 = {p: b for p, b in mirror.items() if "/ik_offset/" not in p and "/static/" not in p}
    ramp_id = next(p for p in v1 if "/ramp/id/" in p)
    gon = next(p for p in v1 if "/stair/gon/" in p)
    v1[ramp_id] = b"y" * len(v1[ramp_id])          # same size, other bytes: expected possible
    v1[gon] = v1[gon][:-1] + b"Z"                   # same size, other bytes: unexpected
    v1_zip = tmp_path / "v1.zip"
    v1_zip.write_bytes(make_zip(v1, prefixed=True))
    report = cmp.run(SUBJECT, v1_zip, manifest_for(mirror, tmp_path / "m.json"), tmp_path / "r.json")
    added = sum(1 for p in mirror if "/ik_offset/" in p or "/static/" in p)
    assert report["totals"] == {"identical": len(v1) - 2, "mirror_only": added, "crc_differs": 2}
    assert [r["path"] for r in report["unexpected_differences"]] == [gon]
    assert ramp_id in [r["path"] for r in report["expected_differences"]]
    with pytest.raises(FileExistsError):
        cmp.run(SUBJECT, v1_zip, tmp_path / "m.json", tmp_path / "r.json")


def test_crc_comparison_flags_v1_only_file(tmp_path):
    mirror = synthetic_files()
    v1 = {**{p: b for p, b in mirror.items() if "/ik_offset/" not in p and "/static/" not in p},
          f"{SUBJECT}/{SESSION}/ramp/id/removed.mat": b"gone"}
    v1_zip = tmp_path / "v1.zip"
    v1_zip.write_bytes(make_zip(v1, prefixed=True))
    report = cmp.run(SUBJECT, v1_zip, manifest_for(mirror, tmp_path / "m.json"), tmp_path / "r.json")
    assert report["totals"]["v1_only"] == 1
    assert report["unexpected_count"] == 1
