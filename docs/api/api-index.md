---
title: Former analysis API
---

# Former analysis API

LocoHub now focuses on standardized data, conversion, quality evidence, and reproducible dataset releases. The former Python, MATLAB, and R analysis libraries are retired from the supported public workflow. Their source is preserved in the repository's `legacy/` archive for reference.

Read datasets with native tools:

| Environment | Load a Parquet file |
|-------------|---------------------|
| Python / pandas | `df = pandas.read_parquet("full.parquet")` |
| MATLAB | `T = parquetread("full.parquet");` |
| R / Arrow | `df <- arrow::read_parquet("full.parquet")` |

See the [Python and MATLAB tutorial](../tutorials/index.md) for loading, checking observation boundaries, selecting complete observations, and plotting. The [data contract](../reference/index.md) describes identities and units. Contributor tooling under `contributor_tools/` remains available for conversion and release preparation.

When replacing former `get_cycles` or filtering calls, group by the complete observation identity declared in the release. Do not reshape rows into blocks of 150 without checking identities, phase order, and sample counts first.
