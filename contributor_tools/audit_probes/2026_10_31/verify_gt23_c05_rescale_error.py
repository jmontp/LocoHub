"""Verifier recomputation of GT23-C05 classes from the committed GT23-C04 audit.

Own code; does not import the worker's probe. Reads only
docs/quality/audits/gt23-c04-trial-divisors.json (and the C05 audit for comparison).
Usage: python3 verify_gt23_c05_rescale_error.py OUT.json [--band-only]
"""
import json, math, sys, collections
import numpy as np

C04 = "docs/quality/audits/gt23-c04-trial-divisors.json"
C05 = "docs/quality/audits/gt23-c05-rescale-error.json"
BAND = 0.0488
TOL = math.log(1.005)


def classify(m, dhat, ds):
    lab = []
    for d in ds:
        orig, resc = abs(math.log(d / m)), abs(math.log(dhat / d))
        lab.append("lower" if orig - resc > TOL else "worse" if resc - orig > TOL else "same")
    s = set(lab)
    if not s:
        return "empty"
    if s == {"lower"}:
        return "lower"
    if s == {"same"}:
        return "same"
    if "lower" in s and "worse" in s:
        return "mixed"
    if "worse" in s:
        return "worse"
    return "lower_or_same"


def main(out, band_only=False):
    a = json.load(open(C04))
    R = a["rules"]; M = a["readme_masses_kg"]; table = sorted(set(M.values()))
    fam_ok = set(R["reliable_families"])
    screen = {(t["subject"], t["task"]): t for t in a["screen"]["trials"]}
    fams = {(t["subject"], t["task"]): t["family"] for t in a["trials"]}
    kfam = collections.defaultdict(float)
    for key, t in screen.items():
        if t.get("second_divisor_kg") and t.get("census_lever_kg"):
            kfam[fams[key]] = max(kfam[fams[key]], abs(math.log(t["second_divisor_kg"] / t["census_lever_kg"])))
    res = {}
    for t in a["trials"]:
        key = (t["subject"], t["task"]); c = t["census"]; m = M[t["subject"]]
        lever = c.get("lever_divisor_kg")
        if c["cls"] == "exact":
            d = c["divisor_kg"]
            res[key] = "own_mass_only" if abs(math.log(d / m)) < TOL else "lower_confident"
            continue
        if lever is None:
            res[key] = "no_estimate"; continue
        st = t.get("stances_total") or 0
        corr = (t.get("ankle") or {}).get("corr") or 0
        if t["family"] not in fam_ok or st < 10 or corr < R["reliable_min_ankle_corr"]:
            res[key] = "not_validated"; continue
        k = BAND if band_only else max(BAND, kfam.get(t["family"], 0.0))
        lo, hi = lever * math.exp(-k), lever * math.exp(k)
        sc = screen.get(key)
        if not band_only and sc and sc.get("second_divisor_kg"):
            s2 = sc["second_divisor_kg"]; lo = min(lo, s2 * math.exp(-BAND)); hi = max(hi, s2 * math.exp(BAND))
        plaus = [x for x in table if lo <= x <= hi]
        dhat = min(table, key=lambda x: abs(math.log(lever / x)))
        ct = classify(m, dhat, plaus)
        cc = classify(m, dhat, list(np.exp(np.linspace(math.log(lo), math.log(hi), 401))))
        if plaus and set(plaus) == {m}:
            res[key] = "own_mass_only"
        elif ct in ("lower", "empty") and cc == "lower":
            res[key] = "lower_confident"
        elif ct == "lower":
            res[key] = "lower_if_recorded_mass"
        elif ct == "same":
            res[key] = "no_change"
        else:
            res[key] = {"mixed": "mixed", "worse": "worse", "lower_or_same": "lower_or_same", "empty": "empty_table"}.get(ct, ct)
    w = {(t["subject"], t["task"]): (t["class"] if not band_only else t.get("narrow_band_class_T", t["class"])) for t in json.load(open(C05))["trials"]}
    diff = [(k, res[k], w.get(k)) for k in res if res[k] != w.get(k)]
    o = {"band_only": band_only, "counts": dict(collections.Counter(res.values())), "n": len(res),
         "family_k": {f: round(v, 4) for f, v in sorted(kfam.items())},
         "mismatches_vs_worker": [[k[0], k[1], r, ww] for k, r, ww in diff],
         "classes": {f"{k[0]}/{k[1]}": v for k, v in sorted(res.items())}}
    json.dump(o, open(out, "w"), indent=1)
    print(json.dumps({x: o[x] for x in ("band_only", "counts", "n", "family_k")}), "mismatches", len(diff))
    for d in diff[:15]:
        print(d)


if __name__ == "__main__":
    main(sys.argv[1], "--band-only" in sys.argv)
