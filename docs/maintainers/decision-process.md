# Human decisions and agent handoffs

How agents bring José decisions with the least cognitive load, and the evidence
behind each rule. The operative rules are in `AGENTS.md` ("Decisions and
handoffs"); this file records why. Evidence strength is as reported by two
literature reviews on 2026-10-27, with citations checked against Crossref or
OpenAlex. Items marked *unverified* were not checked against full text.

## Division of labour

| Who | Decides |
|-----|---------|
| José | Scientific judgments (conventions, signs/frames, exclusions, reference ranges), scope and priority, releases/publishing |
| Agents | Everything else, logged: verification, guarded single-job launches, routine fixes |
| Second agent | Verification review (`review` → `done`) |

Basis: performance and situation awareness when automation fails decline most
sharply once automation moves from *analysing and recommending* to *selecting
the action* (strong; Onnasch et al. 2014, doi:10.1177/0018720813501549;
framework Parasuraman, Sheridan & Wickens 2000, doi:10.1109/3468.844354).
Agents therefore analyse and recommend; José selects for judgment calls.

## Decision format

Each open decision in `backlog.json` renders under "Needs José" in `backlog.html`.

| Field | Rule | Evidence |
|-------|------|----------|
| Options | 2-3, comparable on the same attributes | Choice overload depends on complexity, difficulty, preference uncertainty and effort-minimizing goals (moderate; Chernev et al. 2015, doi:10.1016/j.jcps.2014.08.002; overall effect near zero without moderators, Scheibehenne et al. 2010, doi:10.1086/651235) |
| Consequence per option | What changes, cost, reversibility | Decision aids that state options and outcomes improve knowledge and reduce conflict (strong; Stacey et al. 2024 Cochrane, doi:10.1002/14651858.CD001431.pub6) |
| Defer | Always available, with stated cost of waiting | Deferral is chosen more when options conflict (moderate; Dhar 1997, doi:10.1086/209506) |
| Recommendation + confidence | Shown, with low/medium/high confidence | Defaults are strong partly because they read as endorsement (strong; Jachimowicz et al. 2019, d=0.68, doi:10.1017/bpp.2018.43). Confidence display aided trust calibration (moderate; Zhang, Liao & Bellamy 2020, doi:10.1145/3351095.3372852) |
| Quick check | One fact José can verify in under a minute | Explanations raised acceptance of AI advice whether right or wrong (Bansal et al. 2021, doi:10.1145/3411764.3445717); they help only when they make verification cheaper (Vasconcelos et al. 2023, doi:10.1145/3579605) |
| Commit first | For high-stakes convention/release items only, recommendation hidden until José chooses | Cognitive forcing reduced over-reliance but was least liked (moderate; Buçinca, Malaya & Gajos 2021, doi:10.1145/3449287). Automation bias persists in experts and under load (strong; Parasuraman & Manzey 2010, doi:10.1177/0018720810376055) |
| Context first, small items | Question first; evidence links in the task | Prior context aids comprehension (moderate; Bransford & Johnson 1972, doi:10.1016/S0022-5371(72)80006-9). Review effectiveness falls with change size and rate (moderate, correlational; Kemerer & Paulk 2009, doi:10.1109/TSE.2009.27; Bosu et al. 2015, doi:10.1109/MSR.2015.21) |
| Order | Hardest first, at most three open | Precaution only: session-order effects in the field are confounded (weak-moderate; Linder et al. 2014, doi:10.1001/jamainternmed.2014.5225; "hungry judges" contested). Ego depletion did not replicate (Hagger et al. 2016, doi:10.1177/1745691616652873; Vohs et al. 2021, doi:10.1177/0956797621989733) and is not a basis for these rules |

## Review sheets

José validates by looking, not reading: one local HTML page per item
(`review_sheets/<task-id>/`) with chips for machine checks, 1-3 falsifiable
figures from a recorded random seed, a known-bad contrast, and the decision
card. Basis: the quick check must make verification cheaper than trusting the
agent (Vasconcelos et al. 2023, doi:10.1145/3579605); random rather than
chosen examples support calibrated trust (Lee & See 2004). The specific layout
is a design choice, locked on 2026-10-27 after two independent UI/UX review rounds;
it is not itself a research finding.

## When an agent asks instead of acting

Ask when the choice sets a scientific convention, excludes data, changes scope,
is irreversible or outward-facing, or leaves more than one acceptable option.
Otherwise act on the conservative option and log it. Basis: expected-utility
ask/act framing (weak-moderate; Horvitz 1999, doi:10.1145/302979.303030); agents
rarely ask unprompted but improve when they do (moderate, one benchmark;
Vijayvargiya et al., arXiv:2502.13069).

## Delivery

Chosen by José (2026-10-27): **session start only, no push.** Each agent session
opens by listing open decisions (hardest first) before other work; the backlog
inbox is the record. Evidence considered: interruptions at task breakpoints cost
less frustration (moderate-strong; Adamczyk & Bailey 2004,
doi:10.1145/985692.985727; Iqbal & Bailey 2008, doi:10.1145/1357054.1357070),
which a session start is. Batched push about three times a day improved
well-being while removing notifications raised anxiety (moderate; Fitz et al.
2019, doi:10.1016/j.chb.2019.07.016, effect sizes *unverified*). Revisit if
decisions sit unanswered long enough to block work.

## Keeping trust calibrated

- Weekly spot audit (chosen 2026-10-27): five randomly selected agent-completed
  `done` tasks, each with one quick check, logged in `spot-audits.md`. Zero problems in *n* checks bounds the problem rate at about 3/*n*
  (95%), e.g. 0/10 gives about 30%, 0/30 about 10% (rule of three; Hanley &
  Lippman-Hand 1983, doi:10.1001/jama.1983.03330370053031).
- The verifying agent may include one known-answer item in the sample (a
  synthetic, labeled case, never altered research data). Experiencing
  automation errors reduces complacency (moderate; Bahner, Hüper & Manzey 2008,
  doi:10.1016/j.ijhcs.2008.06.001); trust should match demonstrated capability
  (strong; Lee & See 2004, doi:10.1518/hfes.46.1.50.30392).
- Track how often José accepts the recommendation. Near 100% means either
  rubber-stamping or that the decision type should be delegated.

## Handoffs

Agent-to-agent handoffs keep a fixed structure (status, checks, open items,
next action, receiver confirms). Structured handoff programs reduced errors in
hospitals (strong but bundled intervention; Starmer et al. 2014 I-PASS,
doi:10.1056/NEJMsa1405556, effect sizes *unverified*).

## Not supported by evidence found

Reversibility labels and BLUF as such, commander's intent, architecture decision
records, and the "23 minutes to resume after interruption" figure. Treat these
as practice, not evidence.
