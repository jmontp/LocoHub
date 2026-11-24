#!/usr/bin/env python3
"""Independent readback of a GT23 review bundle. Own code; imports nothing from the repo.
usage: gt23r01_readback.py BUNDLE_DIR REPO_ROOT [SUBJECTS_COMMA]
Checks: manifest.sha256, sha256 of every file, per-observation grids, full = filtered + failures (keys and rows),
column sums full vs sources (E01 minus replaced recordings, plus E02), filtered = full minus failed rows, exclusions vs raw sources,
index/preview/test_summary binding."""
import csv, glob, hashlib, json, os, resource, sys
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

pa.set_cpu_count(1); pa.set_io_thread_count(1)
B, R = sys.argv[1], sys.argv[2]
SUBJ = sys.argv[3].split(",") if len(sys.argv) > 3 else ["AB01", "AB02", "AB03", "AB05", "AB06", "AB07", "AB08", "AB09", "AB10", "AB11", "AB12", "AB13"]
RD = f"{R}/converted_datasets/reconversion_v2"
res, fails = {}, []


def check(name, ok, detail=""):
    res[name] = bool(ok)
    if not ok:
        fails.append((name, str(detail)[:400]))
    print(("PASS " if ok else "FAIL ") + name, "" if ok else str(detail)[:300], flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


man = json.load(open(f"{B}/manifest.json"))
line = open(f"{B}/manifest.sha256").read().split()
check("manifest.sha256", line[0] == sha(f"{B}/manifest.json"))
files = sorted(os.path.relpath(os.path.join(d, f), B) for d, _, fs in os.walk(B) for f in fs if os.path.relpath(os.path.join(d, f), B) not in ("manifest.json", "manifest.sha256"))
check("file list equals manifest", files == sorted(man["files"]), (files, sorted(man["files"])))
bad = [f for f in files if sha(f"{B}/{f}") != man["files"][f]["sha256"] or os.path.getsize(f"{B}/{f}") != man["files"][f]["bytes"]]
check("sha256 and bytes of every file", not bad, bad)

# raw sources
q_failed, q_all = set(), {}
for s in SUBJ:
    for l in open(f"{RD}/gt23_pl_q01v2_batch_{s}/{s}/observations.jsonl"):
        e = json.loads(l)
        k = (e["observation_id"], e["reference_side"])
        q_all[k] = (e["table"], int(e["rows"]))
        if e["overall"] == "failed":
            q_failed.add(k)
sup = {}
for s in SUBJ:
    sup[s] = set(json.load(open(f"{RD}/gt23_pl_e02_batch_{s}/e02_summary.json"))["superseded_e01_recordings"])


def opn(path):
    plain = pq.ParquetFile(path, buffer_size=0)
    cols = [f.name for f in plain.schema_arrow if pa.types.is_string(f.type) or pa.types.is_large_string(f.type)]
    return pq.ParquetFile(path, buffer_size=0, read_dictionary=cols)


def foot(p):
    return pq.ParquetFile(p).metadata.num_rows


GRID = np.arange(150) * 100.0 / 149


def scan(path, table, failed=None, label=""):
    """Per-observation rows/grid + per-column [n_finite, sum, sumabs] over all rows and over failed-observation rows."""
    pf = opn(path)
    num = [f.name for f in pf.schema_arrow if pa.types.is_floating(f.type)]
    idxn = "phase_ipsi" if table == "phase" else "time_s"
    tot = {c: [0, 0.0, 0.0] for c in num}
    fl = {c: [0, 0.0, 0.0] for c in num}
    obs, last, closed, prev = {}, {}, set(), None
    problems = 0
    for b in pf.iter_batches(batch_size=2048, use_threads=False):
        o, sd = b.column("observation_id").to_pylist(), b.column("reference_side").to_pylist()
        ix = b.column(idxn).to_numpy(zero_copy_only=False)
        i, n = 0, len(o)
        while i < n:
            k = (o[i], sd[i]); j = i + 1
            while j < n and o[j] == k[0] and sd[j] == k[1]:
                j += 1
            if k != prev:
                if k in closed:
                    problems += 1
                if prev is not None:
                    closed.add(prev)
                prev = k
            seg = ix[i:j]; c0 = obs.get(k, 0)
            if table == "phase":
                if not np.allclose(seg, GRID[c0:c0 + (j - i)], atol=1e-9, rtol=0) or c0 + (j - i) > 150:
                    problems += 1
            else:
                if not (np.all(np.diff(seg) > 0) and seg[0] > last.get(k, -np.inf)):
                    problems += 1
                last[k] = seg[-1]
            obs[k] = c0 + (j - i)
            i = j
        if failed is not None:
            m = np.fromiter(((a, s) in failed for a, s in zip(o, sd)), dtype=bool, count=n)
        for c in num:
            x = b.column(c).to_numpy(zero_copy_only=False)
            ok = np.isfinite(x)
            t = tot[c]; xv = x[ok]
            t[0] += int(ok.sum()); t[1] += float(xv.sum()); t[2] += float(np.abs(xv).sum())
            if failed is not None and m.any():
                xf = x[ok & m]; f = fl[c]
                f[0] += len(xf); f[1] += float(xf.sum()); f[2] += float(np.abs(xf).sum())
    return {"obs": obs, "tot": tot, "failed": fl, "problems": problems, "cols": pf.schema_arrow.names}


def scan_sources(table):
    tot = None
    rows = 0
    for s in SUBJ:
        for kind in ("e01", "e02"):
            pf = opn(f"{RD}/gt23_pl_{kind}_batch_{s}/{table}.parquet")
            num = [f.name for f in pf.schema_arrow if pa.types.is_floating(f.type)]
            if tot is None:
                tot = {c: [0, 0.0, 0.0] for c in num}
            for b in pf.iter_batches(batch_size=2048, use_threads=False):
                if kind == "e01":
                    rec = b.column("source_recording_id").to_pylist()
                    keep = np.fromiter((r.split("/", 1)[1] not in sup[s] for r in rec), dtype=bool, count=len(rec))
                    if not keep.any():
                        continue
                else:
                    keep = np.ones(b.num_rows, dtype=bool)
                rows += int(keep.sum())
                for c in num:
                    x = b.column(c).to_numpy(zero_copy_only=False)[keep]
                    xv = x[np.isfinite(x)]
                    t = tot[c]; t[0] += len(xv); t[1] += float(xv.sum()); t[2] += float(np.abs(xv).sum())
    return rows, tot


def close(a, b):
    return a[0] == b[0] and abs(a[1] - b[1]) <= 1e-7 * max(1.0, abs(a[1]), abs(b[1])) and abs(a[2] - b[2]) <= 1e-7 * max(1.0, a[2], b[2])


out = {}
for table in ("phase", "time"):
    full = scan(f"{B}/full_{table}.parquet", table, failed=q_failed)
    filt = scan(f"{B}/filtered_{table}.parquet", table)
    out[table] = (full, filt)
    check(f"{table}: no grid/order/contiguity problems (full, filtered)", full["problems"] == 0 and filt["problems"] == 0, (full["problems"], filt["problems"]))
    check(f"{table}: same columns in full and filtered", full["cols"] == filt["cols"])
    exp_keys = {k for k, v in q_all.items() if v[0] == table}
    check(f"{table}: full observations = assessed observations with assessed rows", set(full["obs"]) == exp_keys and all(full["obs"][k] == q_all[k][1] for k in exp_keys))
    fk, ik = set(full["obs"]), set(filt["obs"])
    fail_t = {k for k in q_failed if q_all[k][0] == table}
    check(f"{table}: full = filtered + failures (keys)", fk == ik | fail_t and not (ik & fail_t) and (fk - ik) == fail_t, (len(fk), len(ik), len(fail_t)))
    check(f"{table}: full rows = filtered rows + failed rows", sum(full["obs"].values()) == sum(filt["obs"].values()) + sum(full["obs"][k] for k in fail_t))
    # filtered column sums = full minus failed-row sums
    bad = [c for c in full["tot"] if not close(filt["tot"][c], [full["tot"][c][0] - full["failed"][c][0], full["tot"][c][1] - full["failed"][c][1], full["tot"][c][2] - full["failed"][c][2]])]
    check(f"{table}: filtered column sums = full minus failed rows (finite count, sum, sum abs)", not bad, bad[:5])
    srows, stot = scan_sources(table)
    check(f"{table}: full rows = E01 (non-replaced) + E02 rows", sum(full["obs"].values()) == srows, (sum(full["obs"].values()), srows))
    bad = [c for c in stot if not close(full["tot"][c], stot[c])]
    check(f"{table}: full column sums = sources (E01 minus replaced + E02)", not bad, bad[:5])
    print("  peak RSS MiB", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, flush=True)

nf = sum(len(out[t][0]["obs"]) for t in out); ni = sum(len(out[t][1]["obs"]) for t in out)
print("full obs", nf, "filtered obs", ni, "failed", len(q_failed))
check("full = filtered + failures overall", nf == ni + len(q_failed))
rows = {(v, t): sum(out[t][0 if v == "full" else 1]["obs"].values()) for t in out for v in ("full", "filtered")}
print({f"{v}_{t}": n for (v, t), n in rows.items()})

# exclusions vs raw
ex = list(csv.DictReader(open(f"{B}/exclusions.csv")))
cls = {}
for r in ex:
    cls[r["kind"]] = cls.get(r["kind"], 0) + 1
raw_ex = raw_aw = 0
raw_ex_ids, raw_aw_ids = set(), set()
for s in SUBJ:
    e1 = [json.loads(l) for l in open(f"{RD}/gt23_pl_e01_batch_{s}/exclusions.jsonl")]
    e2 = [json.loads(l) for l in open(f"{RD}/gt23_pl_e02_batch_{s}/exclusions.jsonl")]
    for x in [x for x in e1 if x["recording"] not in sup[s]] + e2:
        raw_ex_ids.add(x["segment_id"])
        raw_ex += 1
    a1 = [json.loads(l) for l in open(f"{RD}/gt23_pl_e01_batch_{s}/authors_windows.jsonl")]
    a2 = [json.loads(l) for l in open(f"{RD}/gt23_pl_e02_batch_{s}/authors_windows.jsonl")]
    for x in [x for x in a1 if x["recording"] not in sup[s]] + a2:
        if x["fate"] != "exported":
            raw_aw += 1
            raw_aw_ids.add(f"{x['file']}#{x['row']}")
check("exclusions.csv: export exclusions equal raw", cls.get("export_exclusion") == raw_ex and {r["exclusion_id"] for r in ex if r["kind"] == "export_exclusion"} == raw_ex_ids, (cls, raw_ex))
check("exclusions.csv: authors windows not exported equal raw", cls.get("authors_window_not_exported") == raw_aw and {r["exclusion_id"] for r in ex if r["kind"] == "authors_window_not_exported"} == raw_aw_ids, (cls, raw_aw))
check("exclusions.csv: assessment failures equal assessment", cls.get("assessment_failed") == len(q_failed) and {r["exclusion_id"] for r in ex if r["kind"] == "assessment_failed"} == {f"{a}|{b}" for a, b in q_failed})
print("exclusion counts", cls, "total", len(ex))

# binding
idx, prev, ts = (json.load(open(f"{B}/{n}")) for n in ("dataset_index.json", "phase_preview.json", "test_summary.json"))
lim = json.load(open(f"{B}/limitations.json"))
check("index, preview, tests, limitations and manifest bind the same hashes and counts", idx["binding"] == prev["binding"] == ts["binding"] == lim["binding"] == man["binding"])
akeys, afail, an = set(), set(), 0
for l in open(f"{B}/assessment.jsonl"):
    a = json.loads(l); an += 1
    akeys.add((a["observation_id"], a["reference_side"]))
    if a["status"] == "failed":
        afail.add((a["observation_id"], a["reference_side"]))
    assert a["in_filtered_variant"] == (a["status"] != "failed")
check("assessment.jsonl: one line per assessed observation, failed flags match", akeys == set(q_all) and afail == q_failed and an == len(q_all))
for n, f in (("full_phase", "full_phase.parquet"), ("full_time", "full_time.parquet"), ("filtered_phase", "filtered_phase.parquet"), ("filtered_time", "filtered_time.parquet")):
    check(f"binding hash {n} equals file", man["binding"][f] == man["files"][f]["sha256"])
b = man["binding"]["counts"]
check("binding counts equal the readback", b["full_phase_rows"] == rows[("full", "phase")] and b["full_time_rows"] == rows[("full", "time")] and b["filtered_phase_rows"] == rows[("filtered", "phase")] and b["filtered_time_rows"] == rows[("filtered", "time")] and b["observations_full"] == nf and b["observations_filtered"] == ni and b["failed_observations"] == len(q_failed) and b["exclusions_total"] == len(ex))
check("test_summary all pass", ts["all_pass"])
print("FAILED:", fails if fails else "none"); print("peak RSS MiB", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
sys.exit(1 if fails else 0)
