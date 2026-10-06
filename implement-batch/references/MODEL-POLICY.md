# Model policy

The evidence and cost analysis behind this policy live in
[`MODEL-RESEARCH.md`](MODEL-RESEARCH.md).

Use a **cheap control plane, balanced issue work, and capability-on-failure
ladder**. Every dispatch goes to a named `batch-*` agent whose definition carries
its own model chain (primary + quota fallbacks, alternating pots); the harness
applies the chain and reports the resolved model per dispatch. Dispatch by agent
name, never by raw model — that is what makes the rows enforceable. Every subagent
is spawned with no inherited conversation history so the review stays independent.
The skill enforces the dispatch table below; caller selection is advisory.

## Dispatch table

| Role | Dispatch agent | Primary model | Reasoning | Chain (fallback order) |
|---|---|---|---|---|
| Batch orchestrator (the caller; advisory) | — | `gpt-5.6-luna` recommended | `medium` | — |
| Initial issue implementer | `batch-implementer` | `muse-spark-1.3-contributor` (Go pot) | `medium` | terra → luna → zen-free → metered |
| High-consequence implementer (auth/authorization, cryptography, money, irreversible migration, concurrency, compatibility-critical public API) | `batch-implementer-hard` | `gpt-5.6-terra` | `high` | muse:xhigh → luna → zen-free → metered |
| Issue Standards reviewer | `batch-standards-reviewer` | `muse-spark-1.3-contributor` (Go pot) | `high` | luna → zen-free → metered |
| Issue Spec reviewer | `batch-spec-reviewer` | `muse-spark-1.3-contributor` (Go pot) | `xhigh` | terra:xhigh → zen-free → metered |
| Fix rounds 1-3 | resume the original implementer | unchanged | unchanged | — |
| Fix round 4 | `batch-escalator` | `gpt-5.6-sol` | `high` | muse:xhigh → terra:xhigh → zen-free → metered |
| Fix round 5 | `batch-escalator-xhigh` | `gpt-5.6-sol` | `xhigh` | muse:xhigh → terra:xhigh → zen-free → metered |
| Finding adjudicator | `batch-adjudicator` | `gpt-5.6-terra` | `high` | muse → zen-free → metered |
| Final Standards reviewer | `batch-final-standards` | `muse-spark-1.3-contributor` (Go pot) | `xhigh` | terra:xhigh → zen-free → metered |
| Final Spec/integration reviewer | `batch-final-spec` | `gpt-5.6-sol` | `high` | muse:xhigh → terra:xhigh → zen-free → metered |
| Final-review remediation, including cross-issue fixes | `batch-escalator`, then `batch-escalator-xhigh` | `gpt-5.6-sol` | `high`, then `xhigh` | as above |

A skill cannot change the model already executing it, so only the subagent
allocation is guaranteed. Luna/medium is the economical recommendation when the
user starts `/implement-batch`; do not add a second orchestrator merely to switch
models. Whatever model entered the skill remains the sole batch orchestrator.

Why these primaries: Muse Spark 1.3 Contributor leads every volume row
(implementer, both issue reviewers, final Standards) because it is the volume
lane on the dollar-metered Go pot with frontier agentic-coding scores (see
MODEL-RESEARCH) — its per-token metering makes the review-heavy loop effectively
inexhaustible, while the task-window-metered Plus pot stays a fallback and is
reserved for the high-stakes rows. Plus tiers are the first fallbacks: `terra`
for the Spec and final-Standards axes, `luna` for the Standards checklist. The
Spec axis runs muse at `xhigh` and the bounded Standards checklist at `high`,
because requirement interpretation is less mechanical than a checklist review.
Sol is reserved for evidence of difficulty (rounds 4-5), the high-consequence
implementer, and the one high-leverage integrated Spec review.

## Quota and pot semantics

Every chain alternates pots so a single exhausted pot does not take down the row.
The agent definitions carry the chains; this table is the reference:

| Pot | Meter | Exhaustion semantics |
|---|---|---|
| `opencode-go` | dollars (`$12`/5h, `$30`/wk, `$60`/mo), shared by all opencode-go models | Pot-wide: when gone, every opencode-go entry dies at once |
| `openai-codex` (ChatGPT Plus) | message windows per model (5h + weekly) plus one shared agentic pool | One model's window can die while others live; pool death kills every openai-codex entry |
| `opencode-zen` | free-tier rate limits | Best effort; unreliable under load |
| metered lanes (`openrouter`, `zai`, `minimax`) | pay-per-token | Never "exhausted"; last-resort overflow |

A reached usage limit is a closed window to wait out, not a gap to bridge:
never redeem Codex usage-limit reset coupons (banked resets) to keep a dispatch
going. omp auto-retries only short transient quota gaps (429/usage-limit:
~1-2 min envelope, honors `retry-after` up to `retry.maxDelayMs` = 5 min, and
can hop to the next chain entry mid-run). Hour-scale windows are the
orchestrator's job, not turn-level retries: quota failure on every chain entry
marks the issue `quota-paused` (see SKILL.md section 3 and ISSUE-LOOP.md); the
run resumes only once the windows replenish.

## Narrow overrides

- A high-consequence issue (authentication, authorization, cryptography, money,
  irreversible migration, concurrency, or a compatibility-critical public API)
  starts on `batch-implementer-hard` (Terra/high). If any condition is unclear,
  use the hard row.
- An adjudication involving security, data loss, or a public contract uses
  `batch-escalator` (Sol/high) instead of `batch-adjudicator`.
- Issue re-reviews keep the same axis allocation. Each fresh reviewer receives the
  current diff, its unchanged axis source pack, and only anonymized open findings
  from that same axis. It never receives the other reviewer's report.

Do not use `max` by default. It is an experiment for workloads where repository evals
show it rescues cases that Sol/xhigh does not. Do not encode `ultra` as a reasoning
effort: it is not one of the public GPT-5.6 API effort values, and the openai-codex
catalog's effort surface tops out at `max` (muse tops at `xhigh`).

## Measure the policy

Record dispatch agent, resolved model (including the fallback flag), reasoning
effort, token usage when available, elapsed time, fix rounds, confirmed and
rejected findings, and final-review escapes in the ledger. After 10-20 issues,
shadow a sample of muse Standards reviews with Luna/high and muse Spec reviews
with Sol/high. Promote a role only when the costlier setting catches materially
more true findings or saves enough retries to pay for itself.
