---
name: nas-ops
description: Day-to-day operations loop for the lemke.dev self-hosted fleet (nas-ansible repo) — intake of alert/cron mails and Alertmanager pages, triage across nas/vps/backup-pi/routers, root-cause, fix via Ansible, deploy, smoke-test, commit. Use when the user pastes a cron mail (AIDE, SMART, systemd unit failed), an Alertmanager alert, a smoke-test or backup-status table, says a service is down/stale/unhealthy, or asks to deploy, verify, or reboot fleet hosts.
---

# NAS Ops

The recurring loop this fleet is operated with. Evidence: 541 user prompts across
161 omp sessions in `~/git-projects/nas-ansible`, the repo's git history, and its
own docs. Every procedure below was observed repeatedly; nothing here is
aspirational.

## The loop

Every ops request follows the same arc. Do not skip stages:

1. **Intake** — classify what arrived (see "Alert classes" below). Cron mails and
   Alertmanager payloads arrive in the chat as pasted text; smoke-test and
   backup-status output arrives as rendered tables (`STALE` / `NOT_CONFIGURED` /
   `OK` / `MISSING` per service and Config/DB/Data column).
2. **Triage read-only** — gather facts before touching anything (next section).
3. **Root-cause** — find the cause, not the symptom. Recurring root causes:
   monitoring rules tuned against plausible defaults instead of observed data
   (swap alerts), volatile files tripping AIDE, DNS flaps masquerading as many
   simultaneous HTTP failures, upstream bugs (LibreChat MCP cache).
4. **Fix in Ansible** — durable state changes land in the repo, never as
   hand-edits on the host.
5. **Deploy the narrowest thing** — per-host playbook, tags, or single-service
   playbook.
6. **Verify on the host** — smoke tests, backup status, semantic probes, e2e for
   auth flows.
7. **Commit and push** — "commit" always implies push here. Conventional
   Commits: `<type>(<scope>): <description>`, imperative, lowercase, no period.

## Host access preflight — always first

All SSH (`ssh nas`, `ssh vps`, routers) authenticates through the ssh-agent
backed by KeePassXC. When KeePassXC is closed or locked, every host looks
simultaneously broken — it is never a network fault then.

```bash
ssh-add -l   # exit 1/2 = no key loaded → tell the user to unlock KeePassXC, keep working on repo-only work
```

Shell notes: NAS and VPS run **zsh**; POSIX one-liners over `ssh host '…'` work.
`ssh nas 'sudo …'` hangs forever on the vault-password prompt — do privileged
work through Ansible (`become`). One passwordless exception exists exactly so
agents can verify: `ssh nas 'sudo systemctl start smoke-tests.service'`.

## Triage toolbox (read-only)

Work host by host: `nas` (Debian + ZFS + Docker), `vps` (`vps.lemke.dev`, also
`vps.internal.lemke.dev` on the tailnet), `backup` (backup-pi, Raspberry Pi +
USB disk), `routers` (openwrt-flint2), `access_points` (TP-Link EAP615).

```bash
# Service health
ssh nas 'docker ps -a --format "{{.Names}}: {{.Status}}"'
ssh nas 'docker inspect --format "{{.Name}} {{.State.Health.Status}}" <container>'
# systemd / timers (the auto-update path)
ssh vps 'systemctl --failed'
ssh nas 'systemctl list-timers --all'
# Logs
ssh nas 'docker logs --since 1h <container>'
ssh vps 'journalctl -u <unit> --since -1h'
# Storage
ssh nas 'zpool status; zfs list -o name,used,refer -r tank'
ssh nas 'df -h /; zpool status tank | grep scrub'
ssh vps 'df -h; du -xh --max-depth=2 /opt/docker 2>/dev/null | sort -rh | head -20'
# Metrics before judging an alert threshold
curl -s http://nas:9090/api/v1/query --data-urlencode 'query=<expr>' | jq .
# VPN vs service: distinguishes tunnel-broken from service-broken
tailscale status; tailscale ping <node>
# Resolver vs routing: resolver answers → DNS fine, routing is not
dig @<resolver-ip> example.com +short; dig example.com +short
```

Tailscale gotchas observed repeatedly:

- Auth keys expire (max 90 days). For headless nodes like the NAS, disable key
  expiry on the node in the admin console instead of chasing new auth keys.
- Phones losing access to LAN devices (`wischbob.lan`, WLED) is a subnet-route /
  accept-routes problem, not a service problem. MagicDNS names over literal
  100.x IPs in all configs.
- openwrt-flint2 runs old packages; updates go through `openwrt-update.yml` /
  `openwrt-network.yml`, never by hand on the device.

For network-level design (VLANs, DNS resolver layout, VPN topology) use the
generic skills instead of re-deriving: `homelab-network-readiness`,
`homelab-network-setup`, `homelab-vlan-segmentation`, `homelab-wireguard-vpn`,
`homelab-pihole-dns`. This skill covers operating the deployed result.

## Alert classes and their procedures

### AIDE cron mail (02:00, `aide --check` + `aide-alert.sh`)

- Read the changed-entries list. Volatile paths (Prometheus WAL/queries data,
  anything under `/opt/docker/appdata/*/data`) are the usual false positives.
- After any planned change that touches watched files (package updates,
  reboots, service data churn): update the AIDE database so the next check
  starts clean — "reboot and update aide records" is the user's stated flow.
- A *new* persistent false positive is fixed by tightening the AIDE rule for
  that path, not by ignoring mails. Changed real files get investigated.

### `systemd unit failed` mail (subject prefixed `[vps]` / `[nas]`)

- Read `/var/log/nas-ansible-auto-update.log` (last 50 lines usually name the
  failing task and host).
- Usual culprit: a container image updated by the scheduled update chain whose
  healthcheck or bootstrap task fails (e.g. Kavita library bootstrap wait).
- Fix in the role's tasks/templates, deploy, confirm the next scheduled run
  passes. Silent deploy failures are tracked in `docs/troubleshooting/`.

### Alertmanager pages

- `InstanceDown` (e.g. `node-exporter-vps` flapping hourly): find the root
  cause — historically a LAN-router DNS flap knocking out all HTTP checks and
  SSH at once, self-healing. A recurring benign alert is a bug in the *rule*.
- Threshold alerts (`HostSwapUsageHigh`): pull observed Prometheus data, tune
  the threshold/duration against what the host actually does. Never silence in
  Alertmanager to make mail stop.

### SMART / hardware mails

- SMART errors on NAS disks (`smartd` mail): check `smartctl -a /dev/disk/by-id/…`,
  correlate with `zpool status`, escalate to the user before any disk action.

### GitHub Actions failure mails

- Read the run, reproduce the failed job locally if possible, fix, push. Known
  recurring: `free-model-sync` breaking on delisted OpenRouter models and
  `setup-uv` version pins. Minutes exhausted → consider self-hosted runners /
  Forgejo migration (an open migration thread, not a default).

### Backup status tables (per service: Config / DB / Data)

- `STALE` = status file older than threshold → check the unit that produces it
  (`systemctl status` / `journalctl -u <backup unit>`) before re-running.
  `sync-immich` reporting stale despite `Result=success` was a healthcheck
  reading the wrong status-file timestamp — fix the check, not the backup.
- `NOT_CONFIGURED` = service intentionally not wired into backups; if it should
  be, that's an Ansible change (register it in the backup roles), not a bug.
- Sequential over parallel for heavy backup jobs — check Prometheus metrics
  (IO, load) to decide. Big media libraries: ZFS snapshots + rsync pull beat
  tar pushes; the NAS pulls Nextcloud from the VPS (relay-capped VPS→pi mirror
  was retired). Verify restore procedures, not just backup freshness
  (`docs/backup/restore.md`).

## Fix via Ansible (durable state rules)

- **ssh may change ephemeral state only**: `docker restart/stop/start`,
  `compose up -d --force-recreate` against the deployed file, `docker run --rm`
  probes, `/tmp` scratch. **Never over ssh**: editing anything under
  `/opt/docker/**` or `/etc/**`, unit files, cron, firewall. A hand-edit that
  fixed something is the signal to write the Ansible task.
- **Playbook per host group** — there is no combined entrypoint:

| Playbook | Host | | Playbook | Host |
|---|---|---|---|---|
| `playbook.yml` | nas | | `backup.yml` | backup |
| `vps.yml` | vps | | `local.yml` | workstation |
| `nas-services-single.yml` | nas, one service | | `vps-services-single.yml` | vps, one service |
| `openwrt-*.yml` | routers | | `openwrt-ap.yml` | access_points |

- **Narrowest deploy**: full playbook only for host-wide changes; single-service
  playbook or `--tags <role>` otherwise. Tags include `monitoring`, `tailscale`,
  `services`, `docker`, `zfs`, `service-config-backup`.
- If Tailscale DNS is broken, deploy still works:
  `ansible-playbook -i inventory.yml update.yml -e vps_update_host=lemke.dev`
  forces the public hostname — keep this escape hatch in mind before any
  change that could sever tailnet access.
- Secrets only in `group_vars/*/vault.yml` as `vault_*`, rendered through
  `templates/env/*.env.j2`. Never in `roles/*/files/env/` (committed — keys
  leaked there before), never on a command line (argv lands in journald).
  `gitleaks` pre-commit guards this; do not `--no-verify` past it.
- Technitium DNS is **add-only**: removing a record from `technitium_zones`
  stops managing it but it keeps resolving forever — declare deletions in
  `technitium_records_absent`.
- Multi-agent sessions: separate worktrees via `scripts/new-worktree.sh`;
  before deploying check `git diff --name-only` shows only files you touched.

## Verify (proof before commit)

```bash
# Smoke tests (21/22-passing suite; passwordless start exists for agents)
ssh nas 'sudo systemctl start smoke-tests.service'
ssh nas 'cat /opt/docker/smoke-status.json'   # or read the rendered table
```

- Every container line must show `Running`, not `Running (unhealthy)`.
- Backup status tables must show `OK`, no `STALE`.
- Scraping MCPs get **semantic probes** — call a real tool and assert usable
  results (non-empty, correct fields), not just a 200 from `/healthz`.
- Auth/SSO changes (Authelia, OAuth logins): verify e2e with Playwright; delete
  cookies for the affected domains first — stale cookies caused several false
  "still broken" rounds (`*.lemke.dev`).
- Reboots are a legitimate verification step after kernel/ZFS/package changes:
  reboot the affected host, then re-run smoke tests.

## Service-specific gotchas (recurring)

- **LibreChat** (VPS): app-level MCP tool catalogs cache for 12h — tool
  breakage after MCP updates can be this upstream cache, not your config
  (clone the LibreChat repo to confirm before patching). MongoDB sidecar is
  part of the stack. Public share links need explicit Traefik/Authelia
  exemptions.
- **LiteLLM**: config lives in `roles/vps_services/templates/litellm_config.yaml.j2`.
  Default-model and fallback chains (e.g. OpenCode-Go → ChatGPT → ZAI) are
  defined there; verify fallbacks by forcing a failure. Free-tier model catalog
  is kept fresh by the `free-model-sync` workflow; stale OpenRouter entries
  answer 429 — prune rather than leave them.
- **Karakeep**: runs near its 512 MiB memory cap on a no-swap host — an OOM is
  a kill, not a slowdown. Raise the cap via compose template when it creeps.
- **Kavita** (VPS): deploy tasks wait on a library-bootstrap healthcheck and
  trigger a library scan — deploy failures here are usually that wait timing
  out, check container logs on the VPS.
- **Immich** (NAS): external library at `/tank/pictures/library` is
  auto-imported; originals on `tank/pictures` (ZFS, snapshot coverage). The
  `thumbs/` directory dominates storage. Machine-learning container is part of
  the stack; app "can't check version" errors are usually server reachability
  via Traefik/Authelia, not Immich itself.
- **Nextcloud** (VPS): migrated from Hetzner; DNS cutover pattern was
  sync-again → flip CNAME → expect client re-login. Collabora container added
  for office docs. Watch VPS disk — the migration filled it once.
- **Home Assistant** (NAS): some integrations (WLED among them) do not support
  YAML configuration — configure via UI, remove the YAML key, restart.
  Dashboard tweaks live in the repo's HA config when possible. Healthchecks
  were added after an outage no automated check caught; every new service gets
  one.
- **Authelia**: default policy was moved to two_factor with explicit rules.
  OAuth-with-Authelia services require the provider to return an email
  ("Provider didn't provide an email") — configure the email scope/client.
  After Authelia/Traefik domain changes, stale browser cookies bounce users
  back to login; clear cookies for the domain before retesting.
- **Traefik** (NAS): routes all service traffic, ACME DNS-01 wildcard certs,
  dashboard on `:8080`. New services need router + TLS + Authelia
  middleware wiring in their compose template (`add-service` repo skill covers
  the full checklist).
- **Renovate**: keeps images current via PRs; when an update "stops
  resolving", Renovate needs the checkbox ticked on its tracking issue —
  re-offer does not happen automatically. Private images flow: lockfile update
  → image build/publish → Renovate bump → auto-deploy; an exact-version guard
  disables scraping rather than run a stale client.
- **GitHub Actions** (this repo): `mcp-automerge`, `free-model-sync`,
  verification-state updates. Failures arrive as mail; treat like any alert.
- **event-calendar** (NAS): Signal/Telegram/Instagram sources; scraping
  cadence is deliberate (rate-limit avoidance); vision fallback chains route
  extraction failures through LiteLLM default-vision.

## Repo conventions that bite

- Working in the repo itself: repo-local skills in `.claude/skills/` —
  `spec`, `ship`, `add-service`, `check-alerts`, `triage-alerts`,
  `triage-aide-alert`. Reach for them instead of re-deriving steps.
- Issues live as GitHub issues, managed via `gh` CLI. Triage labels:
  `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`.
- Long multi-round work starts with a plan in `docs/plans/`; finished
  investigations are written into `docs/troubleshooting/` or
  `docs/monitoring/` so the next session starts from the doc, not from
  re-diagnosis.
- Monitoring must be silent when everything is healthy — recurring mail about
  a known-benign condition is a bug in the rule.
