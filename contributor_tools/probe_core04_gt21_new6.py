"""GT21-RB04 sign test on the six participants new to this project (AB12, AB15, AB17, AB19, AB23, AB28).

Runs the existing CORE-04 GT21 probe (contributor_tools/probe_core04_gt21.py, unchanged; same detector, same adapter rules, same
seed and recording-selection rule, same truth table) against the extracted 2024-copy tree instead of the local 16. Read-only
probe: one recording at a time, bounded reads, nothing written under converted_datasets/ or source folders; run under prlimit,
nice 19, ionice idle, one thread. The probe's own address-space call is replaced by the caller's prlimit. The detector reads the
authors' ik/id/jp and the plate and marker tables; it applies nothing. Undecided channels count as not passed.
"""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools import probe_core04_gt21 as probe  # noqa: E402

EXTRACTED = Path('/mnt/s/locomotion_data/gt21_author_mirror_2024_extracted')
OUT = ROOT / 'docs/quality/audits/gt21-rb04-sign-test-new6-probe.json'
NEW = {'AB12', 'AB15', 'AB17', 'AB19', 'AB23', 'AB28'}


def table(self, path):
    st = Path(path).stat()
    out = probe.read_numeric_table(path)
    st2 = Path(path).stat()
    if (st.st_size, st.st_mtime_ns) != (st2.st_size, st2.st_mtime_ns):
        raise ValueError(f'{path} changed during the read')
    self.files.append({'path': str(path), 'bytes': st.st_size, 'mtime_ns': st.st_mtime_ns})
    probe.release_memory()
    return out


probe.SRC = EXTRACTED
probe.Reader.table = table
probe.resource.setrlimit = lambda *a, **k: None
eligible = set(probe.subjects_with_modes())
if eligible != NEW or not NEW <= set(probe.masses()):
    raise SystemExit(f'eligible subjects {sorted(eligible)} are not the six new participants with weights')
os.nice(max(0, 19 - os.nice(0)))
probe.run_probe(len(NEW), str(OUT))
