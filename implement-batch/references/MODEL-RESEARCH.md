# GPT-5.6 model allocation for `/implement-batch`

Researched 2026-09-02 against official OpenAI documentation. This note proposes an
economical default for the batch orchestrator, issue implementation/review loop, fix ladder,
adjudication, and final integrated review.

## Recommendation

Use a **cheap control plane, balanced issue work, and capability-on-failure ladder**:

- Luna runs high-volume, bounded work: orchestration and Standards review.
- Terra is the normal engineering tier: initial implementation, Spec review, and adjudication.
- Sol is not the default issue model. Spend it only after ordinary issue-level review/fix loops
  have failed, and once on the integrated batch where one missed interaction could invalidate
  several otherwise-correct issues.

That allocation is an **inference for this workflow, not an OpenAI-prescribed role matrix**.
OpenAI's actual guidance is only the broader tiering: Sol for flagship capability, Terra for a
balance of intelligence and cost, and Luna for efficient high-volume workloads. OpenAI also
recommends `medium` as the balanced reasoning starting point, using `high` or `xhigh` only when
evaluations show a gain, and reserving `max` for the hardest quality-first workloads.
([model guidance](https://developers.openai.com/api/docs/guides/latest-model))

### Default role and round matrix

| Role or round | Model | Reasoning | Why this is the economical default |
| --- | --- | --- | --- |
| Batch orchestrator | `gpt-5.6-luna` | `medium` | Most work is ledger maintenance, dependency-frontier calculation, bounded Git operations, and dispatch. `medium` avoids making a long-running control plane brittle while retaining Luna's high-volume economics. The orchestrator should escalate an ambiguous technical judgement rather than silently making it. |
| Initial issue implementer | `gpt-5.6-terra` | `medium` | This is the long, output-heavy TDD role. Terra is the documented balance tier; `medium` is the documented balanced starting point. The review ladder supplies the quality signal needed before spending more. |
| Issue Standards reviewer | `gpt-5.6-luna` | `high` | The input and required output are tightly structured: inspect one materialised diff against documented rules and cite findings. High effort compensates for using the economy tier while the independent Spec axis reduces single-reviewer risk. |
| Issue Spec reviewer | `gpt-5.6-terra` | `high` | Requirement coverage and behavioural correctness demand more semantic judgement than a standards checklist. Review is shorter than implementation, so spending Terra/high here is a useful quality gate. |
| Fix rounds 1-3 | resume original `gpt-5.6-terra` implementer | remains `medium` | The agent already owns the issue context and gets concrete, cited findings. Reuse avoids paying the context/reconstruction cost of a fresh stronger model. Fresh reviewers still verify every fix. |
| Fix round 4 | fresh `gpt-5.6-sol` implementer | `high` | Three failed rounds are evidence that the balanced baseline is insufficient. Sol is now justified, but start below `xhigh`/`max` because the open findings make the task narrower than the original issue. |
| Fix round 5 | fresh `gpt-5.6-sol` implementer | `xhigh` | This is the last automated attempt, so a second fresh context and one-step reasoning escalation are warranted. Keep `max` out of the fixed default until repository-specific evals show that it rescues cases `xhigh` does not. |
| Finding adjudicator | `gpt-5.6-terra` | `high` | Adjudication is rare but must compare anonymous technical claims against code. Terra/high is a middle ground between Luna checklist work and Sol escalation. Use Sol/high only for a security, data-loss, public-contract, or repeatedly disputed ruling. |
| Final batch review, Standards axis | `gpt-5.6-terra` | `high` | The integrated diff is wider than one issue, so move the bounded Standards axis up one model tier for the one-time gate. |
| Final batch review, Spec/integration axis | `gpt-5.6-sol` | `high` | Cross-issue behaviour is the highest-leverage review in the flow. A single Sol pass here is cheaper than using Sol on every issue and targets flagship capability where integration reasoning matters most. |

The current `ir-reviewer` agent role fixes reviewer reasoning at `high`, so the review rows above
also fit that runtime constraint. This is current harness metadata, not part of the public API
model contract; verify it when implementing the skill.

Two implementation details follow from the current agent harness (the Codex
interface this research targeted; the omp port supersedes both — see the "omp
enforcement, pots, and quota" appendix at the end):

- A skill cannot change the model of the agent already executing it. To guarantee Luna/medium for
  the control plane, either invoke `/implement-batch` with that model/effort or make the entry
  agent dispatch one dedicated Luna/medium orchestrator and wait for it.
- Explicit subagent model/effort overrides require a fresh or bounded history fork. Use no
  inherited conversation for issue agents and pass only the artifacts the issue loop specifies;
  that also preserves the intended independence between implementers and reviewers.

These are runtime constraints observed in the current Codex agent interface, not claims from the
public model documentation.

### Conditional overrides

Keep the matrix deterministic by making exceptions narrow:

1. A clearly mechanical issue with a strong, deterministic test seam may start on Luna/high.
2. An issue touching authentication/authorization, irreversible data migration, concurrency,
   cryptography, money, or a compatibility-critical public API should start on Terra/high.
3. Do not jump to Sol merely because an issue is large. Escalate on evidence: three unsuccessful
   fix rounds, or a predefined high-consequence boundary.
4. `max` is an opt-in experiment for round 5 or the final Spec/integration review, not a default.
   OpenAI explicitly recommends comparing `max` with `xhigh` on representative workloads rather
   than assuming it wins. ([model guidance](https://developers.openai.com/api/docs/guides/latest-model))
5. Do not encode `ultra` as a `reasoning.effort` value. The public GPT-5.6 API contract lists
   `none`, `low`, `medium`, `high`, `xhigh`, and `max`; the same documentation refers to Codex
   ultra as a multi-agent-like mode, not an API effort level.
   ([model guidance](https://developers.openai.com/api/docs/guides/latest-model))

## Price and capability basis

Current API text-token prices per 1 million tokens are:

| Model | Intended tier | Input | Cached input | Output |
| --- | --- | ---: | ---: | ---: |
| GPT-5.6 Luna | cost-sensitive, high-volume | $0.20 | $0.02 | $1.20 |
| GPT-5.6 Terra | intelligence/cost balance | $2.00 | $0.20 | $12.00 |
| GPT-5.6 Sol | flagship complex professional work | $4.00 | $0.40 | $20.00 |

Sources: [Luna model page](https://developers.openai.com/api/docs/models/gpt-5.6-luna),
[Terra model page](https://developers.openai.com/api/docs/models/gpt-5.6-terra), and
[Sol model page](https://developers.openai.com/api/docs/models/gpt-5.6-sol). Sol's page says its
promotional pricing is available at least through 2026-11-21, so re-check prices after that date.

At equal token volumes, Terra is 10x Luna's token rate. Sol is 2x Terra for input and about 1.67x
for output. For a purely illustrative call using 100,000 uncached input tokens and 20,000 output
tokens, the listed rates produce approximately **$0.044 Luna, $0.44 Terra, and $0.80 Sol**. This
does not predict actual agent cost: reasoning level, tool results, retries, cache hits, and response
length all change token use. It does show why putting Sol on every issue and every repeated review
would be the wrong default.

All three model pages list the same API reasoning efforts: `none`, `low`, `medium` (default),
`high`, `xhigh`, and `max`, and the same 1,050,000-token context window and 128,000-token maximum
output. See the [official model comparison](https://developers.openai.com/api/docs/models/compare).
The pages also state that a prompt over 272,000 input tokens is charged at 2x input and 1.5x
output for the full request. Keeping issue agents scoped to one issue therefore protects both
context quality and cost.

These are **API token rates**, useful as a relative cost signal for the allocation. They are not a
claim about how a particular ChatGPT or Codex subscription meters interactive subagents.

## Why this is cheaper without making review ceremonial

The common path for an issue is Terra/medium implementation plus one Luna/high Standards review
and one Terra/high Spec review. Sol spend appears only if three fix rounds fail. Repeated review
remains independent and fresh, but the cheaper reviewer handles the narrower axis. The one-time
integrated review raises capability because its scope and consequence are larger.

This is intentionally asymmetric: duplicated reviewers are useful only if their axes and failure
modes differ. Making both issue reviewers Sol would multiply spend without first establishing that
Sol changes pass/fail accuracy on this repository. Conversely, making both Luna risks turning the
Spec axis into a checklist when it requires requirement interpretation. Both statements are
workflow-design inferences, not claims made by OpenAI.

## Validation before treating it as settled

OpenAI advises testing the same reasoning setting and one level lower on representative work,
because the best setting depends on the workload. ([model guidance](https://developers.openai.com/api/docs/guides/latest-model))
Apply that advice to 10-20 completed issues:

- record input, cached-input, output, and elapsed time by role;
- record important findings later confirmed, rejected, or missed;
- record fix rounds and whether Sol escalation resolved the blocker;
- shadow a sample of Luna Standards reviews with Terra/high;
- shadow a sample of Terra Spec reviews with Sol/high;
- compare Terra/medium with Terra/high on initial implementation;
- promote a costlier model/effort only when the shadow result catches materially more true issues
  or reduces total retries enough to pay for itself.

Until those repository-specific measurements exist, the role matrix above is a rational starting
hypothesis rather than an evidence-proven optimum.

## Exact official sources

- [OpenAI model guidance for GPT-5.6](https://developers.openai.com/api/docs/guides/latest-model)
- [GPT-5.6 model comparison](https://developers.openai.com/api/docs/models/compare)
- [GPT-5.6 Luna model page](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
- [GPT-5.6 Terra model page](https://developers.openai.com/api/docs/models/gpt-5.6-terra)
- [GPT-5.6 Sol model page](https://developers.openai.com/api/docs/models/gpt-5.6-sol)

## Appendix: omp enforcement, pots, and quota (2026-09-06)

This install runs the skill in the Oh My Pi (omp) harness, whose subagent model
selection differs from the Codex interface this note was researched against. The
normative dispatch table now lives in [`MODEL-POLICY.md`](MODEL-POLICY.md); this
appendix records the runtime facts the port rests on.

**Enforcement surface.** omp has no per-dispatch model argument: "task dispatch
sets only `agent`; it does not set a worker model." Model resolution at spawn is,
in order: `task.agentModelOverrides[agentName]` → the agent definition frontmatter's
prioritized `model:` list (role aliases expanded) → the parent session's active
model. Reasoning effort rides on the model selector (`:medium`, `:high`, `:xhigh`)
or an agent `thinking-level`. Enforcing a per-row model therefore means one agent
file per row, each pinned to its own chain; dispatch by that agent's name. Every
`SingleResult` reports `resolvedModel` (+ `resolvedModelIsFallback`), so the ledger
can audit which entry actually ran. Agent files live in `~/.omp/agent/agents/`
(mirrored to `~/.config/opencode/agents/` for opencode-CLI parity); omp ignores
`.codex/agents`.

**Pots.** The implementer primary moved from `gpt-5.6-terra` to
`muse-spark-1.3-contributor` on `opencode-go` — a $10/mo subscription with $60/mo
usage allowance ($12/5h rolling, $30/wk) at $0.10/$0.20 per 1M tokens (cached read
$0.002), the highest request volume of any model on the plan. On 2026-09-07 the
issue-review rows (Standards, Spec) and the final-Standards row followed the
implementer onto muse as their primaries (see MODEL-POLICY); the Plus pot now
serves fallbacks and the high-stakes rows. ChatGPT Plus
(`openai-codex`, OAuth) meters by per-model message windows per 5h (Plus
estimates: Sol 10-100, Terra 25-200, Luna 250-2,000) plus a weekly shared agentic
pool — task-counted, not token-counted. `opencode-zen` free tier and metered lanes
(openrouter/zai/minimax) complete the fallback picture. The API token rates in the
price table above are relative cost signals only; neither subscription meters
subagents by those rates.

**Quota behaviour.** omp auto-retries short transient quota gaps (429/usage-limit,
~1-2 min envelope, honors `retry-after` up to `retry.maxDelayMs` = 5 min default,
hops model chains on retry). It does not redeem banked Codex usage-limit reset
coupons — a reached limit is waited out, not bridged (2026-09-07 policy update:
no coupons; wait for replenishment). Hour-scale windows are handled at the
orchestrator level via the `quota-paused` issue state and resume flow in SKILL.md
section 3, which resumes only after the windows replenish. Idle/parked
subagents can be revived via `hub` messaging, which is how fix rounds ≥2 resume
with their context after a quota pause.
