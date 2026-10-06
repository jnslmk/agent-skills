---
name: canary-watch
description: Post-deploy verification for deployed sites and services. Checks HTTP status/latency, SSE liveness, static-asset 200s, console errors, and TTFB/page-weight regressions against GitHub Pages sites, VPS services behind Traefik/Authelia, and local preview servers before push. Use after deploys, risky merges, or dependency upgrades, and when the user says "verify the deploy", "canary check", or "is it live".
---

# Canary Watch — Post-Deploy Verification

## When to Use

- After deploying to GitHub Pages or the VPS (vps.lemke.dev)
- After merging a risky change or upgrading a dependency
- When verifying a fix actually fixed it
- Before pushing: run the full sweep against the local preview server first
- Sustained monitoring during a launch window

## Targets

Map every check to the target type — they fail differently.

### GitHub Pages sites

- HTML returns 200 over https at the custom domain; http redirects to https
- **The classic Pages failure is not a 5xx — it's a mismatch:** fresh HTML referencing old hashed assets (or stale-cached HTML referencing assets from the previous deploy). Extract every JS/CSS/font URL from the HTML and confirm each returns 200. A single 404 on a hashed asset means a broken deploy even though the page "loads".
- After adding/removing a custom domain, check for regressions to the `*.github.io` URL and CNAME behavior.

### VPS services behind Traefik/Authelia

- **An auth wall is not an outage.** `302`/`401` redirecting to Authelia login (e.g. `/auth/login` or an `abs`-protected host) means the service is up but locked. Report it as HEALTHY-LOCKED, not DOWN.
- Prefer unauthenticated health endpoints for liveness:
  - Traefik: `https://<traefik-host>/api/ping` → body `OK`
  - Authelia: `https://auth.<domain>/api/health` → JSON `"status":"OK"`
- For authenticated page checks, reuse a logged-in browser session (omp relay tab) or pass an exported session cookie (`curl --cookie`). Never put credentials in command lines or logs.
- Behind Traefik, also confirm the router resolves: a 404 with Traefik's default backend page means the router/service entry is gone — distinct from the app's own 404.

### Local preview servers (before push)

- Run the full sweep against `http://localhost:<port>` before pushing anything.
- In diff mode, compare local preview vs the production URL — catch regressions before they deploy.

## Checks

1. **HTTP status + latency** — `curl` timing breakdown (DNS/connect/TTFB/total):

   ```bash
   curl -sS -o /dev/null -w '%{http_code} ttfb=%{time_starttransfer}s total=%{time_total}s\n' https://site.example/
   ```

2. **SSE liveness** — connect and require an initial event or heartbeat within the timeout:

   ```bash
   curl -sN -m 5 -H 'Accept: text/event-stream' https://site.example/events | head -5
   ```

   Output within 5s = alive; timeout with zero bytes = dead stream. In the browser, `new EventSource(url)` and assert `onopen`/first `onmessage`.

3. **Static assets** — pull asset URLs from the HTML, check each returns 2xx/3xx with the expected content type:

   ```bash
   grep -oE '(src|href)="[^"]+\.(js|css|woff2?|png|svg|webp)"' page.html \
     | cut -d'"' -f2 | sort -u | while read -r u; do
       curl -s -o /dev/null -w "%{http_code} %{content_type} $u\n" "$u"
     done | grep -v '^2\|^3' && echo "ASSET FAILURES ^^^" || echo "all assets OK"
   ```

4. **Console errors** — via the omp browser (headless Chromium): open the URL in a tab, then collect console messages and page errors with `tab.run` (attach `console`/`pageerror` listeners before navigation). Count errors not present at baseline. Also scan for failed network requests (4xx/5xx) in the same pass.
5. **Perf sanity** — TTFB from check 1 (warm < ~800ms is a sane bar for a static/edge site); page weight = sum of transfer sizes for HTML + assets (Chromium network report or `curl -w '%{size_download}'` per asset). Flag TTFB >2x baseline or a large weight jump (unminified asset shipped, new third-party script).

## Watch Modes

- **Quick check** (default): single pass over all checks, report results.
- **Sustained watch**: re-run every N minutes for M hours (loop in a background job); compare each pass against the first.
- **Diff mode**: two URLs, side by side — local preview vs prod, or staging vs prod.

## Alert Thresholds

```yaml
critical:  # immediate alert
  - HTTP status >= 500 or connection refused
  - Static asset returns 4xx/5xx
  - SSE endpoint cannot connect or sends nothing before timeout
  - Console error count > 5 (new errors only)
  - TTFB > 4s

warning:   # flag in report
  - TTFB or total time > 2x baseline
  - New console warnings
  - Page weight > 1.5x baseline
  - Static asset content type changed unexpectedly
  - SSE heartbeat latency > 2x baseline
  - Auth wall where the page was previously public (or vice versa)

info:      # log only
  - Minor latency variance
  - New third-party requests
```

On critical: `notify-send "canary-watch" "..."` (Linux desktop), and append to `~/.local/state/canary-watch.log`.

## Output

```markdown
## Canary Report — site.example — 2026-03-23 03:15 UTC

### Status: HEALTHY

| Check | Result | Baseline | Delta |
|-------|--------|----------|-------|
| HTTP | 200 (ttfb 180ms) | 200 / 160ms | +20ms |
| Console errors | 0 | 0 | — |
| Static assets | 42/42 | 42/42 | — |
| SSE /events | heartbeat 210ms | 190ms | +20ms |
| Page weight | 1.2 MB | 1.1 MB | +9% |

### No regressions detected. Deploy is clean.
```

For auth-walled services, the HTTP row reads `302 -> /auth/login (HEALTHY-LOCKED)` and liveness comes from the health endpoint row.

## Integration

- GitHub Actions: run the quick check as a post-deploy step for Pages sites.
- VPS: after an Ansible deploy, run the quick check against health endpoints first, authenticated pages second.
