# Repair limits, findings, and disputes

This is the single authority for repair counting, stagnation, harness correction,
and disputes. Read it before the first repair, not as mandatory startup material.
Use one run-level repair counter by default. Separate stages are justified only by
actual independent ownership/review boundaries; a new reviewer, renamed task, or
additional audit does not create a new budget.

## 1. Bounded repairs

Initial implementation and review are round 0. One product round is a batched repair,
focused proof, and independent closure check, normally by the retained reviewer.
Increment before repair. A subsequent source repair consumes the next round;
provider replacement continues the already reserved round. Initial reviews,
provider faults, adjudication, and harness-only repairs do not consume product rounds.

| Product round | Decision |
|---|---|
| 1–5 | Ordinary repairs, subject to the stagnation gate |
| 6–8 | Explicit evidence-based extension before each repair |
| Beyond 8 | Stop automatic product repair |

**Verified progress** is closure or meaningful reduction of an Important finding,
or new reproducible evidence materially narrowing its diagnosis. Renaming a finding,
moving code, another opinion, or an unverified claim is not progress.

- Retain the implementation owner while making verified progress.
- After an unsuccessful approach without verified progress, use a fresh appropriately
  skilled implementer, following the core skill's dispatched-agent model policy.
- Two materially distinct unsuccessful approaches without new evidence/reduction,
  or two consecutive cycles without verified progress, stop automatic repair.
- An extension needs current verified progress or a genuinely new evidence-backed
  material defect, plus a specific next repair and check. Older progress cannot fund
  every later extension. Unused budget never overrides stagnation.

Preserve counters, evidence, model escalation, and finding identity on resume or
route changes. Supply current policy to replacement agents whose embedded profiles
may still carry the older workflow.

### Harness and launch correction

A broken fixture, selector, probe, or environment invalidates that evidence; it is
not itself a product defect. Preserve the failed run and distinguish its cause.
Allow **two harness-source repair attempts total per actual task/stage**, incremented
before repair. Smoke the corrected harness minimally before repeating broader work.
A later incident does not reset this budget; a third source repair blocks that stage.

A mixed harness/product change consumes both applicable counters. The harness
exemption never permits weakened assertions, reduced acceptance, masked failures,
or production behavior changes disguised as fixture work.

A wrong command syntax, cwd, or help-only invocation may be corrected **once** using
the canonical invocation, without consuming a product or harness-source round.
Preserve the failed evidence, record the exact correction, and prove minimal execution
before a full rerun. This is not permission for repeated unchanged failures, altered
assertions, fixture edits, or production changes. A second unsuccessful correction
for the same invocation stops automatic retries.

A busy shared lock is a queue condition: wait for its owner to release it, then launch
the next job through the explicit verification queue. Do not launch competing jobs
merely to wait on the same lock or count a never-started check as product evidence.

## 2. Independent closure and finding identity

One independent complete-change review covers the integrated candidate by default.
Retain that read-only reviewer through focused repair closure. A fresh reviewer is
for unavailability, compromised independence, material scope/ownership expansion,
stagnation, or an explicit request. An extra final audit requires the justification
in the core skill; helper count alone does not require it.

Record inspection completion separately from verification readiness. A reviewer can
complete code inspection while final broad checks are pending. The main agent then
reconciles their actual results without waking the reviewer solely for an evidence
status update. Missing or invalid required proof still blocks handoff. A newly exposed
product defect or semantic code change reopens the relevant review and proof.

A finding needs file:line, a reachable trigger, concrete consumer impact, and source
or reproducible evidence. Use stable IDs, such as `R1` or `task-name-R1`. The same
root cause and failing behavior keep their ID across wording/line changes. Reopen
only for changed code/reachability or genuinely new evidence, stating the cause.

Report nits only on the initial review; repair closure concerns Important findings.
Previously missed Important defects remain eligible on unchanged lines. The retained
reviewer keeps its own findings. A fresh reviewer receives neutral pending IDs,
scenarios, and evidence—not author reasoning, inherited verdicts, or disputed rebuttals.

| Disposition | Required evidence |
|---|---|
| `fixed` | Repair and focused proof verified; independent reviewer confirms closure |
| `rejected` | Written technical evidence; independent adjudication if disputed |
| `parked` | Out-of-scope issue or surviving nit, with reason; never an in-scope blocker |
| `escalated` | Stagnation, exhausted budget, missing prerequisite/decision, or unavailable proof |

`open` is an interim state. Every finding must have a disposition at handoff; an
Important escalated finding blocks completion. A complete inspection with Important
findings is not approval to ship. Completion requires no open blockers, independent
review covering final semantic changes, and valid passing required evidence.

## 3. Disputes

An implementer may fix a finding or reject it with technical reasoning and file:line
evidence. For a genuine dispute, use a fresh independent adjudicator with the reviewer
brief's adjudicator variant. Supply finding and rebuttal as unattributed peer claims,
the actual code, and the requirement; neither claim is authoritative.

Record `FINDING STANDS`, `REBUTTAL STANDS`, or `BOTH PARTLY RIGHT`, the source evidence,
and the required action. Do not send a rebuttal back to the same reviewer as another
vote. Use at most one adjudication for unchanged finding/evidence. Changed reachability
or genuinely new evidence can reopen it, preserving the ID. Adjudication consumes
no product round and does not reset counters.

## 4. Compact session state

For small runs, keep one compact record containing:
- Original acceptance criteria, selected baseline/drafts, owner and write-set.
- Retained reviewer identity and the currently reviewed semantic snapshot.
- Product/harness/invocation counters and progress/stagnation evidence.
- Stable findings, dispositions, and any adjudication/extension decision.
- Focused checks and final check plan, actual relevant inputs/results/artifacts.
- Verification queue ownership and temporary resource expiry/cleanup.

Use `.implement-review/<short-sha>-<task-slug>/ledger.md` when a repository supports
it or a resumable multi-owner run benefits. A real multi-owner run may add a task
contract/dependency table and integration state. Do not manufacture a DAG, per-task
review stages, full report tables, or a second audit for a single-owner change.

Update on meaningful transitions: ownership/baseline selection, before each repair
or extension, after proof/closure, on a dispute, and on pause/resume or final handoff.
Preserve failed evidence and approach history instead of overwriting it with the
latest verdict. Repository-required records and safety gates take precedence.

## 5. Decision smoke cases

| Situation | Expected decision |
|---|---|
| First repair's provider fails to start | Replacement uses the reserved round; no simultaneous owner |
| Round 5 gains diagnostic evidence and a specific next repair | Round 6 only if stagnation permits; later extensions need their own gate |
| Same blocker moves lines after two distinct failed approaches | Retain ID, stop/escalate; no new budget |
| Two cycles show no verified progress, with rounds left | Stop automatic repair |
| Round 8 reveals another genuine blocker | Record and escalate; no ninth repair or false completion |
| Same disputed evidence returns with a new opinion | Keep disposition; no repeat vote |
| Two harness-source repairs succeeded; another probe breaks | Budget remains exhausted; no third source repair |
| Only final broad checks finish after a complete code review | Main reconciles proof; no evidence-only reviewer revival |
| A shared verification lock is busy | Wait for release; do not spawn a competing check |

## 6. Handoff

Respect the user's requested format. Default to concise exercised verification and
real blockers, not a mandatory table dump. Disclose every parked/escalated issue and
its reason when relevant; report incomplete integrations or missing proof honestly.
Release owned temporary resources/session ownership, preserve user changes, and
commit or mutate git state only when requested/authorized. No blocked run is complete.
