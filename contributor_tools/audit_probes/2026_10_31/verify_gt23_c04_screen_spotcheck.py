"""Verifier spot-check of the GT23-C04 screen's second estimator (round 2).

Uses the verifier's own estimators from verify_gt23_c04_trial_divisors.py (e2 =
talus point fitted with the mass, all loaded samples, both sides pooled; bias
1.0035 from the 8 exact trials). Read-only probe exception; output JSON path on
the command line.
"""
import json, resource, sys, time
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import verify_gt23_c04_trial_divisors as v

TRIALS = [("AB05", "dynamic_walk_1"), ("AB06", "meander_1"), ("AB07", "tire_run_1"), ("AB09", "obstacle_walk_1"),
          ("AB01", "side_shuffle_1"), ("AB07", "normal_walk_1"), ("AB01", "tire_run_1"), ("AB03", "cutting_1")]
BIAS_E2 = 1.0035

def main(out):
    t0 = time.time()
    res = []
    for s, t in TRIALS:
        r = v.estimators(s, t)
        r.update({"subject": s, "task": t, "e2_bias_corrected_kg": round(r["e2"]["divisor_kg"] / BIAS_E2, 2) if "e2" in r else None})
        res.append(r)
        print(s, t, r.get("e2_bias_corrected_kg"), flush=True)
    json.dump({"trials": res, "files_read": v.reads, "elapsed_s": round(time.time() - t0, 1),
               "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)}, open(out, "w"), indent=1)

if __name__ == "__main__":
    main(sys.argv[1])
