---
title: Review and maintain releases
---

# Review and maintain releases

LocoHub maintains data contracts, conversion tooling, quality evidence, and dataset releases. Researchers use native data readers. Former analysis libraries are preserved in `legacy/`; maintaining or publishing an analysis SDK is outside the supported workflow.

## Review a prepared release

1. **Verify provenance.** Match original study/source identifiers, local source hashes where available, converter revision, citation, data terms, and actual contributor review. Remote source declarations are not verification that the source was retrieved.
2. **Check identity and representation.** Recording IDs, observation IDs, reference side, and observation type must be recoverable from the source. Separate ensemble curves, transfers, continuous recordings, and individual cycles. Confirm related bilateral views remain related.
3. **Review conversion decisions.** Inspect a representative pilot against source traces. Check units, signs, frames, event timing, filtering, derivatives, normalizations, and force-plate/limb assignments.
4. **Review quality coverage.** Read structural issues, required/optional signal coverage, and passed/failed/missing/unchecked/invalid states. A high aggregate pass rate is insufficient evidence.
5. **Review the profile.** Confirm applicability to the population, tasks, and observation types. Require a rationale for thresholds and changes; identify empirical or provisional rules honestly.
6. **Reconcile artifacts.** Full converted data, profile-filtered data, quality results, exclusions, profile snapshot, hashes, and manifest counts must agree. Filter whole observations and examine exclusions by participant and task.
7. **Record the decision.** Document approval or unresolved limitations with the actual reviewer and exact artifact identity. A successful build records checks and contributor review; it does not create independent scientific approval.

## Acceptance and limitations

Structural failures and unreviewed identities block release preparation. Missing or unchecked biomechanical evidence must remain visible; it cannot be converted into a passing result. Filtering never repairs source units, event detection, or missing channels.

Review scientific limitations even when the structural contract passes. Current rule checks do not prove correct coordinate transforms, force-plate assignment, event detection, or validity of the original measurements. Avoid a universal quality score and do not rank studies by incomparable rule profiles.

Legacy downloads remain **legacy / unreviewed** until the corresponding source mapping and artifacts are reprocessed and reviewed. Preserve historical counts without presenting them as a new release validation. Changing a label or regenerating documentation is not approval.

## Immutability and updates

Use `contributor_tools/build_dataset_release.py` to create a new release directory. Existing output directories are rejected. Changes to source data, conversion, profile, or provenance require a new release identifier and new evidence. Keep prior releases traceable.

The manifest identifies produced artifacts; verify hashes when moving or distributing a bundle. Review any change in retained subjects, tasks, and signal coverage before linking a replacement download. Keep original study citation and data license distinct from the repository's code license.

## Work within the resource budget

Run a small representative pilot before scaling. Release admission defaults to 256 MB of estimated decoded input and 500,000 rows. Processing is bounded in-memory, not streaming; actual process memory also includes interpreter and computation overhead. Plan larger shards deliberately and avoid concurrent full-dataset reads on a shared workstation.

Tests for contracts, release integrity, and public examples should use small deterministic fixtures. Full dataset conversion and review are explicit jobs, not incidental documentation or CI tasks.

## Implementation boundaries

| Area | Location |
|------|----------|
| Dataset converters | `contributor_tools/conversion_scripts/` |
| Contract and quality implementation | `contributor_tools/common/data_contract.py` |
| Internal table/schema/task helpers | `contributor_tools/common/` |
| Release entrypoint | `contributor_tools/build_dataset_release.py` |
| Rule profiles | `contributor_tools/validation_ranges/` |
| Dataset metadata and legacy reports | `docs/datasets/` |
| Former analysis implementations | `legacy/` |

Keep validation decisions in the shared contract implementation. CLI summaries, filtering, release manifests, and documentation must consume the same result, rather than independently reconstructing counts. Contributor utilities are internal implementation, not a new public SDK.

## Documentation checks

The public site should let a researcher identify the population, available signals, artifact variant, limitations, and quality evidence before downloading. Preserve native Python and MATLAB examples that run on the complete synthetic fixture.

```bash
python -m pytest tests/test_data_documentation.py
python docs/build.py --check
```

Review the generated site under the `/LocoHub/` base path. Check links, download labels, keyboard interaction, mobile layout, and dark mode. Do not publish legacy reports as current evidence or describe manually tuned thresholds as literature norms without traceable support.

See the [contributor workflow](../contributing/index.md), [data contract](../reference/index.md), and [former API notice](../api/api-index.md).

The published website is authored HTML under `docs/`. This Markdown remains an internal reference. The legacy documentation generator does not publish or update the HTML site.
