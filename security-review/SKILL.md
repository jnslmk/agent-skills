---
name: security-review
description: Security review checklist and patterns for small public-facing web apps. Use when adding authentication or auth flows, handling user input, scraping external sites, storing secrets, creating API endpoints, or handling sensitive data.
---

# Security Review

Security review for small public-facing web apps, especially those with scraping and auth flows. Focus on the vulnerabilities that actually get small apps popped: leaked secrets, injection, broken auth, and unbounded scraping endpoints.

## When to Apply

- Implementing authentication, sessions, or login/signup flows
- Handling user input, file uploads, or form submissions
- Scraping third-party sites or proxying external content
- Creating or modifying API endpoints
- Working with secrets or credentials
- Storing or displaying user data

## Checklist

### 1. Secrets

```js
// FAIL
const apiKey = "sk-proj-xxxxx"
// PASS
const apiKey = process.env.SCRAPER_API_KEY
if (!apiKey) throw new Error('SCRAPER_API_KEY not configured')
```

- [ ] No hardcoded keys, tokens, or passwords anywhere in source
- [ ] `.env*` in `.gitignore`; secrets come from env vars / hosting platform
- [ ] No secrets in git history (`git log -p | grep -i key` if unsure)
- [ ] Secrets validated at startup, not silently undefined at runtime

### 2. Input Validation

Validate at every trust boundary with a schema, whitelist-style:

```js
import { z } from 'zod'
const ScrapeRequest = z.object({
  url: z.string().url().max(2048),
  maxPages: z.number().int().min(1).max(50).default(10)
})
```

- [ ] All user inputs parsed through a schema before use
- [ ] Error messages don't leak internals (paths, stack traces, query text)
- [ ] File uploads restricted: size, MIME type, extension

### 3. Injection

```js
// FAIL — string concatenation
const q = `SELECT * FROM users WHERE email = '${email}'`
// PASS — parameterized
await db.query('SELECT * FROM users WHERE email = ?', [email])
```

- [ ] Every query parameterized (or via a query builder/ORM correctly)
- [ ] Shell commands never interpolate user input; avoid spawning shells with scraped/user data entirely
- [ ] Scraped content treated as untrusted on both ends: never passed to `eval`, templates, or queries unescaped

### 4. Authentication & Authorization

```js
// Tokens: httpOnly cookie, NOT localStorage (XSS-readable)
res.setHeader('Set-Cookie',
  `session=${token}; HttpOnly; Secure; SameSite=Strict; Max-Age=3600`)
```

- [ ] Session tokens in httpOnly, Secure, SameSite cookies
- [ ] Passwords hashed with bcrypt/argon2 — never plaintext, never MD5/SHA alone
- [ ] Authorization checked server-side on every sensitive operation (verify the requester may act on that resource — IDOR is the classic small-app hole: `/api/orders/123` must check the order belongs to the caller)
- [ ] Login/signup endpoints rate-limited and return generic errors ("invalid credentials" — never "user not found")
- [ ] Login, password reset, and signup flows have timing-safe comparisons; reset tokens are single-use and expire

### 5. XSS

- [ ] Framework default escaping relied on; `dangerouslySetInnerHTML`/`innerHTML` only with sanitized content
- [ ] User-provided HTML sanitized with a whitelist (e.g. DOMPurify with allowed tags/attrs)
- [ ] CSP header set, starting strict (`default-src 'self'; object-src 'none'; frame-ancestors 'none'`) — no `'unsafe-inline'`/`'unsafe-eval'` as a default
- [ ] Scraped third-party content never rendered as raw HTML

### 6. CSRF

- [ ] SameSite=Strict/Lax on all cookies
- [ ] CSRF token on state-changing requests (or token-bearing header pattern)
- [ ] CORS locked to known origins, no `*` with credentials

### 7. Rate Limiting & Scraping Safety

Scraping and search endpoints are expensive and abuse magnets — limit them hardest.

- [ ] Global rate limit on all API endpoints (e.g. 100 req / 15 min per IP)
- [ ] Aggressive per-endpoint limits on scraping, search, auth (e.g. 10 req / min)
- [ ] Scraping requests validated: target URL scheme limited to http(s), no internal/private addresses (block `localhost`, `127.0.0.0/8`, `10.0.0.0/8`, `169.254.x` — SSRF protection), response size and timeout capped
- [ ] User-agent and robots.txt respected toward scraped sites; concurrency capped so a single request can't open hundreds of connections

### 8. Data Exposure

```js
// FAIL
console.log('Login:', { email, password })
return NextResponse.json({ error: error.message, stack: error.stack }, { status: 500 })
// PASS
console.error('Internal error:', error)          // server logs only
return NextResponse.json({ error: 'An error occurred. Please try again.' }, { status: 500 })
```

- [ ] No passwords, tokens, card data, or secrets in logs
- [ ] Generic errors to clients; details only in server logs
- [ ] HTTPS enforced in production; security headers set (CSP, X-Frame-Options, X-Content-Type-Options)

### 9. Dependencies

- [ ] Lock file committed; installs use the locked mode (`npm ci`)
- [ ] Audit clean (`npm audit` / equivalent); Dependabot or periodic updates enabled

## Pre-Deploy Quick Pass

Secrets in env → inputs validated → queries parameterized → authz on every sensitive route → rate limits on, tightest on scrape/auth → httpOnly cookies → generic errors → HTTPS + headers → audit clean.

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP SSRF Prevention](https://owasp.org/www-community/attacks/Server_Side_Request_Forgery)
- [Web Security Academy](https://portswigger.net/web-security)
