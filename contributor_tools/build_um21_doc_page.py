#!/usr/bin/env python3
"""Build docs/datasets/um21/index.html (kept so the old command still works).

This is now one call to the general builder, build_dataset_review_page.py, with the
UMich 2021 spec. UM21-R01 is still in `review`, so the gate is relaxed with --allow-review.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dataset_review_page as general  # noqa: E402

if __name__ == "__main__":
    spec = Path(__file__).resolve().parent / "page_specs/um21.json"
    sys.exit(general.main([str(spec), "--allow-review"] + sys.argv[1:]))
