# Data conformance tests

Run the small active suite from the repository root:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 python3 -m pytest -q
```

Tests exercise observation identity, numeric conversions, missingness, release
artifacts, and native data examples. They use tiny fixtures, never the full local
dataset collection. Do not run bulk conversions as part of the test suite.

Former analysis-library/tutorial tests are retained under `legacy/tests/` as
historical material and are not conformance oracles. Native MATLAB source
fixtures requiring a MATLAB installation are marked separately.
