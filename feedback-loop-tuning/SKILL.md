---
name: feedback-loop-tuning
description: Use when reducing pre-commit, local test, or CI feedback latency through measured timings while preserving required checks and release safety.
---

# Feedback-loop tuning

Measure the wait, shorten the critical path, keep the proof. Tune the existing tools rather than introducing another runner.

## 1. Map the actual gates

Read repository guidance, hook configuration, test commands, CI workflows and their callers. Inspect the installed hook as well as its configuration: a wrapper can run additional commands. Resolve `core.hooksPath` and the Git hooks path, including linked-worktree behavior.

Produce a gate inventory: command, changed-file or whole-project scope, mutations, environment/prerequisites, and whether it blocks commits, merges, or publication. Distinguish linters/formatters, lightweight file checks, types, units, integration/browser tests, and image builds. Check required status names before renaming jobs; if protection settings are inaccessible, record the uncertainty and preserve existing aggregate statuses.

**Done:** every automatic gate and publication dependency has an identified command and owner. Preserve unrelated drafts; use the repository's session/worktree convention for edits.

## 2. Establish a baseline

Use hosted history for CI and real local invocations for hooks. For GitHub Actions, discover the repository and recent runs rather than assuming names or IDs:

```sh
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
gh run list --limit 10 --json databaseId,workflowName,headSha,conclusion,createdAt,url
# Set run to an observed completed run ID.
gh api --paginate "repos/$repo/actions/runs/$run/jobs" \
  --jq '.jobs[] | {name,started_at,completed_at,steps:[.steps[]|{name,started_at,completed_at,conclusion}]}'
```

- Sample about five comparable successful runs when available. Record revision, runner, cache state and setup cost; keep failures and cold starts separate. Inspect logs/duration output for the measured long pole. Report limited samples as samples, not a fabricated percentile.
- Derive step/job duration from timestamps. Measure the critical path through dependent jobs, not the sum of parallel durations. Report queue/event-to-result delay separately and keep total runner minutes visible.
- Time representative small staged-file hook workloads, including Python/JS, configuration and documentation where applicable. Use explicit existing files with the installed runner, for example `time prek run --files <paths> -v`. Test fixers in a disposable checkout: benchmark runs must not rewrite user drafts. Separate first-install, warm execution and retries after fixes.
- Exercise the real commands. An offline suite must use isolated state and authorized fixtures, not production credentials. Follow existing supervision, expiry, cleanup and workstation-lock rules for heavy checks; queue behind other owners rather than bypassing their lock.

**Done:** retain a compact timing table and commands/environment sufficient to reproduce it. Missing access is an evidence gap, not permission to estimate an observed baseline.

## 3. Set budgets and place tests

Use these as starting objectives, adjusted explicitly for measured workload—not universal SLAs or hard test assertions:

| Loop | Starting objective | Placement |
|---|---|---|
| Warm hooks, small changes | Usually ≤5 seconds; investigate a sustained >10-second tail | Staged-file lint/format and lightweight safety checks |
| Focused local tests | A few seconds where practical | Run the changed behavior while developing; affected integration/browser checks when needed |
| CI quality signal | ≤2 minutes including normal setup | Lint/format validation, configured types and lightweight checks |
| CI units | A few minutes | Complete required unit suites |
| Complete required checks | About 10 minutes or less | All required suites on the exact candidate |

If the baseline needs a transitional budget, state its evidence and the remaining goal; for example, an existing six-minute unit suite can justify an initial eight-minute lane budget. Keep safety timeouts above normal performance budgets with room for cleanup. Exclude runner queues from execution budgets but expose their developer-visible cost.

Keep full suites authoritative in CI **and** focused tests in the local development loop. Moving slow suites out of commit hooks does not mean waiting for CI to discover every behavioral mistake. Retain cheap security/file-safety checks. Leave hooks unchanged when they already meet their budget. Use available primary guidance before calling a threshold a best practice; exact project budgets are recommendations.

**Done:** write down budgets, what each loop runs, and any justified exception without silently reducing required coverage.

## 4. Change the measured bottleneck

Stop at the smallest change that addresses the long pole:

1. Remove genuinely duplicate work; reuse pinned tools and existing project commands. Keep full-project type scope explicit even when lint receives filenames.
2. Parallelize independent suites in isolated jobs when sequential execution dominates. Preserve all test selectors and install each lane's frontend, native, audio and browser prerequisites. Each lane must be able to fail the aggregate gate.
3. For slow setup, verify action defaults and actual cache/download costs before changing caching. Frozen installs still run on cache hits. Measure added runner minutes and cache transfer costs; avoid adding a cache or dependency without a demonstrated benefit.

### Candidate safety when splitting CI

- Resolve mutable branch/manual inputs **once** upstream of fan-out. Pass that immutable source SHA to every lane. A branch advancing between checkouts must not mix tested candidates.
- If releases prepare unpublished commits, preserve the existing bundle/artifact validation and check out that same final candidate in every lane. Published tags and images must refer to the checked SHA.
- Preserve required status names or explicitly migrate their consumers. Keep a stable aggregate gate that runs after failed/skipped dependencies and publishes the checked SHA only when **every required lane succeeded**. Reject failure, cancellation, and skipped work; a green quality lane is not aggregate correctness.
- Retain existing release concurrency and publication dependencies. Cancel superseded PR work only when safe for that workflow; do not apply PR cancellation policy indiscriminately to releases.

**Done:** the optimized configuration still accounts for every original required check and the exact publication candidate. Update the existing contributor/testing documentation; avoid wrappers or telemetry systems unless measurement requires them.

## 5. Prove and hand off

Validate the changed configuration with the repository's hook/schema checks and workflow linter where available. Exercise changed boundaries in disposable fixtures: branch movement after source resolution, identical candidate SHAs across lanes, and aggregate success/failure/cancelled/skipped behavior. Include unpublished release bundles if that path exists.

Run the retained affected gates on the stable candidate, using existing fixtures and resource supervision. Check setup as well as tests; correct YAML alone does not prove a runnable lane. Obtain independent review for publication/candidate or other safety-critical changes. A fixer changing inputs reopens relevant proof.

Compare hosted before/after runs once the candidate is pushed through an authorized workflow. Separate code verification from performance verification: local passing tests and a calculated parallel critical path do not establish hosted speed. If hosted evidence is unavailable, report the improvement as projected, with the exact missing measurement. Never drop coverage, mask failures, weaken required statuses, or repeatedly rerun a known failure to obtain a green sample.

**Done:** report changed gates, measured timings versus budgets, retained coverage, exercised proof, runner-cost tradeoff, and any unmeasured hosted result. Release owned temporary processes and verification resources; publish only when requested.

## Primary guidance

- [DORA: Continuous integration](https://dora.dev/capabilities/continuous-integration/) — rapid feedback, an approximate ten-minute upper bound, and parallelization of long tests.
- [Google: Where tests run](https://web.dev/learn/testing/get-started/where-tests-run) — focused local feedback plus presubmit and CI checks.
- [pre-commit documentation](https://pre-commit.com/) — filename filtering and first-run environment setup versus cached execution.
- [uv caching in CI](https://docs.astral.sh/uv/concepts/cache/#caching-in-continuous-integration) and [Playwright browser caching](https://playwright.dev/python/docs/ci#caching-browsers) — cache tradeoffs to measure, not assume.
