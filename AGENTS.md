# LocoHub contributor guidance

## Purpose

LocoHub delivers curated standardized locomotion data and clear documentation.
It does not maintain a public analysis SDK. Researchers use ordinary Parquet/CSV
readers. Historical Python/MATLAB/R libraries are retained under `legacy/` only.

## Active structure

- `contributor_tools/conversion_scripts/`: dataset-specific source adapters.
- `contributor_tools/common/`: internal schema, table, validation, transformation and plotting helpers.
- `contributor_tools/build_dataset_release.py`: immutable local release bundles.
- `contributor_tools/DATA_CONTRACT.md`: versioned observation contract and release workflow.
- `docs/`: researcher catalog, data reference, native Python/MATLAB examples.
- `tests/`: small independent data/conversion/release fixtures.
- `converted_datasets/`: local scientific artifacts; never overwrite implicitly.

## Scientific correctness

Preserve source recording, observation and anatomical reference identities.
Never invent timing, mass, clinical laterality, unavailable measurements, or source
provenance. Keep individual cycles, transfers, ensembles and continuous recordings
distinct. Inclusive phase exports have exactly 150 samples from 0 to 100 percent.

Use one structured observation assessment for filtering, reports and release
facts. Missing/unassessed signals are not evidence of passing. Reference ranges
need population/protocol context and evidence; do not tune to reach a desired
aggregate pass rate. Draft tuner profiles are not approved release profiles.

Full converted and profile-filtered variants retain their shared source lineage.
Every exclusion must be accounted for. Historical artifacts remain explicitly
legacy/unreviewed until reconverted or independently reconciled.

## Resource constraints

This is low-priority work on a shared WSL host. Use one numerical worker, low
process/I/O priority, small fixtures and bounded reads. Do not load full research
datasets in ad-hoc scripts. Numerical and MATLAB jobs run one at a time through the
reviewed guarded launcher (`python3 -m contributor_tools.guarded_launcher run SPEC.json`,
dry run first; Linux jobs only, as MATLAB/native jobs need a reviewed native extension),
and a full-dataset run requires a passing pilot of the same bound code. Exception: a
read-only probe may run without the launcher if it reads one recording or channel at a time,
writes nothing under `converted_datasets/` or source folders, stays under 300 MiB peak RSS
(record it), and runs alone at nice 19 / ionice idle. Conversions, MATLAB and anything
that writes data still need the launcher. Default release/review
loads have a 256 MiB admission estimate. Do not raise it to bypass a rejection.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLBACKEND=Agg nice -n 19 ionice -c 3 python3 -m pytest -q
```

Full-data integration tests are opt-in with `--run-integration`. MATLAB R2023b
is installed in the Windows default location, accessed from WSL. Coordinate any
native MATLAB run because it has a larger startup memory footprint.

## Working conventions

### Decisions and handoffs

José decides only three kinds of things: scientific judgments (conventions,
signs/frames, exclusions, reference ranges), scope and priority (what is next,
what a release contains), and releases or publishing. Agents decide and log
everything else, including verification and single guarded job launches.

- Put each José decision in `decisions` in `docs/maintainers/backlog.json`. It
  renders under "Needs José" at the top of `backlog.html`. Fields: question,
  2-3 options each with a one-line consequence (what changes, cost, reversible?),
  `cost_of_waiting` (defer is always allowed), `recommended`, `confidence`
  (low/medium/high), `why`, and `check`: one fact José can verify in under a
  minute. Set `decide_before_recommendation` for high-stakes convention or
  release items so the recommendation stays hidden until he chooses.
- No hashes, PIDs or file paths in the question. At most three open decisions,
  hardest first. Ask only when the choice sets a convention, excludes data,
  changes scope, is irreversible or outward-facing, or has more than one
  acceptable option; otherwise act conservatively and log it.
- Review sheets: José validates by looking. Build each sheet with
  `contributor_tools/common/review_sheet.py` (fixed order and budgets) from a
  committed script, into `review_sheets/<id>/` (gitignored). One verification
  sheet per task; a separate sheet per decision when it needs its own figures.
  - Order: ask strip, headline claim with scope, chips, figures, decision,
    "Not shown by this sheet", reply line, folded details. At most 60 words of
    prose, 8 chips, 3 figures, 3 not-shown items.
  - Chips have three states: pass, failed, not checked. Any unexplained anomaly
    is a "not checked" chip, never hidden behind green chips.
  - Each figure is titled as the question it answers and must make its claimed
    failure visible. Its contrast matches that specific failure: a labeled
    made-up example, a source overlay, or a cited reference band. Examples come
    from a recorded random seed, never hand-picked. One panel per image, saved
    at most 4.5 in wide with fonts of at least 10 pt.
  - Decisions: an options table with fixed columns, "left out" first, plus
    defer and its cost. The recommendation stays in a click-to-reveal fold, and
    nothing else on the page (chips, reply hint) may leak it. Order options
    by a neutral attribute, such as size, and say so in the builder.
  - Plain words: no hashes, PIDs, paths or task IDs outside the folded details.
  - Render the sheet at wide and phone width before presenting it.
- Delivery is session start only: open each session with the open decisions
  (hardest first), then work. No push notifications.
- Weekly spot audit: in the first session at least 7 days after the last entry in
  `docs/maintainers/spot-audits.md`, offer five randomly selected `done` tasks,
  each with one quick check. Log the date, tasks, result and José's
  recommendation-acceptance rate there.
- Copy decisions into `backlog.json` only from a verified handoff, and re-copy
  them on every later merge. A decision whose option letters differ from its
  sheet would record José's answer with the wrong meaning.
- José answers in chat (e.g. `D-3: A` or `D-3: defer`). The agent records
  `answer` and `answered_at_utc`. An open decision blocks only its own task.
- `review` means verification by a second, independent agent, not José. That
  agent checks acceptance criteria against evidence and moves the task to `done`
  or back with reasons. José is never asked to read JSON or audit receipts.
- Agent-to-agent handoffs stay structured in the task `handoff` and audit JSON.
- Reports to José are short: what changed, open decisions, what runs next.
  Readable pages are local files, never published externally.
- Evidence and rationale: `docs/maintainers/decision-process.md`.

### Work backlog and agent handoffs

- Start with `docs/maintainers/backlog.json` and run
  `python3 contributor_tools/build_backlog_page.py --next` to read the next ready task.
  The HTML view is `docs/maintainers/backlog.html`; edit the JSON and regenerate it.
- Work on one ready task at a time. Record its ID before making changes. Check its
  prerequisites and current evidence; a saved job plan is not a running worker.
- Before numerical or native work, verify current process ownership and resource
  headroom. Never restart a stopped job only because its prior wait expired.
- At handoff, update the task with changed files, exact checks and their coverage,
  remaining questions, evidence paths, and the next action. Leave blocked work
  explicitly blocked with the condition needed to proceed.
- Move a task to `review` when its deliverables are ready. A second agent marks it
  `done` only after its acceptance criteria and exact supporting evidence check out.
  Task completion does not confer scientific approval on an entire dataset.
- Check backlog consistency with
  `python3 contributor_tools/build_backlog_page.py --check` before handing off.
  Keep unrelated source and conversion artifacts unchanged during planning work.

Human-managed, focused development. Preserve pre-existing edits. Keep source
adapters and reviewer tools simple; add tests against independently known values
rather than mirroring implementation. Use synthetic fixtures honestly labeled as
synthetic. Do not claim scientific dataset regeneration from fixture tests.

Do not publish or push releases without the requested destination/workflow.
If committing, stage specific files (never `git add -A`) and include:

Co-authored-by: José A. Montes Pérez <jmontp@umich.edu>
