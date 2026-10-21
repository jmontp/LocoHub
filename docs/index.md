# LocoHub

Find locomotion data, understand how it was processed, and inspect the evidence for using it in your research. LocoHub standardizes files and records quality checks so researchers can work directly in Python, MATLAB, or another environment that reads Parquet.

[Find a dataset](datasets/index.md){ .md-button .md-button--primary }
[Try a small example](tutorials/index.md){ .md-button }
[Read the data contract](reference/index.md){ .md-button }

## Choose data for your question

1. **Match the study.** Check participants, tasks, assistance conditions, and whether the needed signals were measured or derived.
2. **Inspect the exact artifact.** Review its release identifier, source provenance, available signals, quality results, and documented limitations.
3. **Choose full or filtered data.** Full converted data preserves converted observations. Profile-filtered data selects observations using named rules; inspect exclusions before using it.
4. **Load the file natively.** Use pandas `read_parquet`, MATLAB `parquetread`, or your preferred Parquet reader.

!!! warning "Existing catalog entries are legacy / unreviewed"
    Historical downloads and reports remain available. They have not been approved under the current release contract. A legacy “clean” label or high pass rate does not establish data quality, population suitability, or compatibility between studies.

## Read quality results precisely

| Result | Meaning |
|--------|---------|
| Passed | The applicable check ran and its criterion was met. |
| Failed | The applicable check ran and its criterion was not met. |
| Missing | A required signal or value was unavailable. |
| Unchecked | No applicable check was run. |
| Invalid | Structural problems prevent a trustworthy observation or check. |

Structural integrity, signal availability, and conformance to a biomechanical profile answer different questions. Rules may depend on the population and protocol. A profile pass rate describes the checks that ran; it is not a score for the scientific value of a dataset.

## What is in a file?

Each row contains a sample, observation identifiers, task metadata, and available biomechanical signals. A phase observation has 150 points over 0–100%; a time export retains sampling times. Individual cycles, ensemble curves, continuous recordings, and transfers are identified explicitly.

The [reference](reference/index.md) defines identity, units, observation types, and the evidence accompanying a release. The [tutorial](tutorials/index.md) uses the same small, complete fixture in Python and MATLAB.

## Contribute and maintain

- [Contribute a dataset](contributing/index.md): convert, diagnose, document provenance, and build a reviewable release.
- [Review a release](maintainers/index.md): reconcile data, exclusions, profiles, and source evidence.
- [Former API users](api/api-index.md): move analysis to native data tools.

## Funding

This work was supported by the National Institute of Biomedical Imaging and Bioengineering of the NIH under Award Number R01EB031166. The content is solely the responsibility of the authors and does not necessarily represent the official views of the NIH.
