#!/usr/bin/env bash
# Preserve original archive paths and metadata. Inspect first; --run extracts.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$script_dir/extract_source_archive.py" "$@"
