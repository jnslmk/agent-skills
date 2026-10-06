---
name: homelab-pihole-dns
description: Homelab DNS server operations — running a local resolver (Technitium + Unbound, or Pi-hole/AdGuard Home as alternatives), blocklists, local DNS records, encrypted upstreams, DHCP integration, and troubleshooting broken DNS resolution. Use when setting up, changing, or debugging the home network DNS server.
---

# Homelab DNS Server Operations

A local DNS resolver gives every device on the network ad/malware blocking,
local `home.arpa` names, and encrypted upstream queries — no per-device
software. This skill is about operating a home DNS server generally; the
reference stack here is **Technitium (blocking + local zones + admin UI) in
front of Unbound (recursive, DNSSEC-validating upstream)**. Pi-hole and
AdGuard Home are common alternatives and appear as examples where their
workflow differs.

## When to Use

- Installing or reconfiguring a local DNS resolver (Technitium, Unbound,
  Pi-hole, AdGuard Home).
- Adding or managing blocklists and allowlists.
- Creating local DNS records (`nas.home.arpa`, `grafana.home.arpa`).
- Setting up DNS-over-HTTPS/TLS upstreams.
- Deciding between router DHCP and resolver DHCP.
- Troubleshooting devices that lose connectivity after a resolver change.

## How It Works

```
Client → Technitium (53/udp-tcp)                    ← the network's resolver
    1. blocklist check → blocked domains get a null answer
    2. local zone check → nas.home.arpa answered authoritatively
    3. otherwise forwarded → Unbound (recursive from roots, DNSSEC) → internet
```

Alternative shapes: Pi-hole = dnsmasq + FTL blocklist (needs a separate
recursive layer, e.g. unbound, for privacy); Technitium can also recurse
itself if you want one process instead of two.

## Installation Basics

- **Static address first.** Reserve the resolver's IP in DHCP (e.g.
  `192.168.30.2`) before anything points at it. A changed IP breaks DNS for
  the whole network.
- Technitium runs as a self-contained .NET service (`install-technitium`-style
  script or Docker); admin UI on port 5381. Pi-hole is commonly deployed via
  its install script or Docker. Pin versions; DNS is infrastructure, not a
  toy — avoid `latest` tags.
- Unbound: install the distro package, listen on localhost only (e.g.
  `127.0.0.1:5335`), set `qname-minimisation: yes` and
  `auto-trust-anchor-file` for DNSSEC, then point Technitium's forwarders at
  `127.0.0.1#5335`.

## Pointing the Network at the Resolver

```
# Method 1: DHCP option (recommended) — on OpenWrt, per VLAN:
  /etc/config/dhcp:  list dhcp_option '6,192.168.30.2'
  Clients pick it up on next lease renewal (reconnect Wi-Fi or dhclient -r).

# Method 2: Per-device (testing before network-wide rollout)
  Set DNS manually on one client and verify before touching DHCP scopes.

# Method 3: Resolver as DHCP server
  Technitium and Pi-hole can serve DHCP, but if the router (OpenWrt
  dnsmasq) already does it reliably, keep it there — one fewer critical
  service on the resolver host. If you do switch: disable router DHCP
  first; two DHCP servers on one network corrupt leases.
```

Keep a fallback documented during rollout: OpenWrt's dnsmasq (the gateway IP)
as secondary DNS improves availability but lets clients bypass filtering —
use it during migration, remove it for strict blocking. Real redundancy is a
second resolver instance, not a public upstream.

## Blocklist Management

- Technitium: Zones → Blocking, add list URLs (StevenBlack hosts,
  BlocklistProject malware/tracking), schedule a reload; use Allow zones for
  false positives.
- Pi-hole: Admin → Adlists, then `pihole -g` (Update Gravity); Whitelist for
  false positives; `pihole -q example.com` shows which list blocked a domain.

```text
Recommended starting lists:
  https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts
  https://blocklistproject.github.io/Lists/malware.txt
  https://blocklistproject.github.io/Lists/tracking.txt

After changing lists, verify nothing critical broke:
  firmware update domains, captive portals, work VPNs, smart-home clouds.
Schedule weekly refresh — stale lists miss new domains.
```

## Local DNS Records

Make services reachable by name in the IETF-reserved `home.arpa` domain
(RFC 8375). Avoid `.local` (mDNS conflict) and ad hoc `.lan`.

```
Technitium:  Zones → forward zone "home.arpa" (or Cache-served local zone),
             A records:  nas.home.arpa      192.168.30.10
                         dns.home.arpa      192.168.30.2
                         grafana.home.arpa  192.168.30.3
             CNAMEs for aliases: portainer.home.arpa → nas.home.arpa

Pi-hole:     Local DNS → DNS Records / CNAME Records, same shapes.
```

Verify from a client: `dig nas.home.arpa @192.168.30.2` and via DHCP path.

## Encrypted Upstream (DoH/DoT)

With Unbound as a recursive resolver, queries go directly to authoritative
servers — no third-party upstream to encrypt to; recursion plus qname
minimisation is the privacy-maximizing setup. If you prefer forwarding to a
public resolver instead:

- Technitium: Settings → Forwarders → DoH/DoT URL
  (e.g. `https://cloudflare-dns.com/dns-query` or `1.1.1.1@853#cloudflare-dns.com`).
- Pi-hole: pair with `cloudflared` DoH proxy on localhost and point the
  upstream at `127.0.0.1#5053`.

## Troubleshooting

```bash
# Client has no internet at all → suspect DNS first:
dig @192.168.30.2 example.com     # resolver answers? DNS is fine, routing is not
dig example.com                   # no answer → client not using the resolver

# Blocked domain that should not be:
#   Technitium: check query logs / Dashboard → temporarily allow the domain
#   Pi-hole:    pihole -q example.com   (which list) ; pihole -w example.com

# Resolver service down:
#   Technitium: systemctl status technitium ; journalctl -u technitium
#   Pi-hole:    pihole status ; pihole restartdns

# Live query stream:
#   Technitium: Dashboard logs ; Pi-hole: pihole -t (tail)

# Unbound health:
unbound-control status            # running, no primes, anchor ok
dig @127.0.0.1 -p 5335 dnssec.works   # AD flag set = DNSSEC validation works
dig @127.0.0.1 -p 5335 dnssec-failed.org  # must SERVFAIL

# Gravity/blocklist refresh (Pi-hole):
pihole -g
```

## Anti-Patterns

```
# BAD: Single resolver with no recovery path
# If it dies, the network loses DNS. GOOD: documented gateway fallback during
# rollout; second resolver instance for strict blocking in steady state.

# BAD: Deploying without a reserved/static address
# A DHCP change orphans every client's resolver setting.

# BAD: Enabling resolver DHCP while router DHCP is still on
# Two DHCP servers fight; disable the router's first.

# BAD: Public fallback DNS as "redundancy"
# Clients happily bypass filtering. Accept it only during migration.

# BAD: Never refreshing blocklists
# Stale lists miss new ad/malware domains — schedule weekly reloads.

# BAD: Keeping config drift between devices and Ansible
# If the host is Ansible-managed, record zone/blocklist config there too.
```

## Best Practices

- Reserved IP before deployment; `home.arpa` for all local names.
- Technitium → Unbound recursion for privacy + DNSSEC; forwarders only if
  recursion is impossible.
- Weekly blocklist refresh; query-log review shows what devices actually do.
- Test one client/VLAN before repointing every DHCP scope.
- Document the fallback order: Technitium → gateway dnsmasq → (emergency)
  manual client DNS.

## See Also

- Skill: `homelab-network-readiness`
- Skill: `homelab-network-setup`
- Skill: `homelab-vlan-segmentation`
- Skill: `homelab-wireguard-vpn`
