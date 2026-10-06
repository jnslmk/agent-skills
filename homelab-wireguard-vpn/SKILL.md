---
name: homelab-wireguard-vpn
description: Remote access to a home network with Tailscale (WireGuard-based) — subnet routers, exit nodes, ACLs, MagicDNS, and troubleshooting. Also covers raw WireGuard concepts when a hand-rolled server is genuinely required. Use when setting up or debugging VPN access to a home network, or choosing between split and full tunnel routing.
---

# Homelab WireGuard VPN (Tailscale)

WireGuard is the modern VPN protocol — fast, small, and the right transport
for remote access to a home network. For a homelab, run **Tailscale**: it is
WireGuard with identity-based key management, NAT traversal, and a
coordination layer, so there is no server to install, no port to forward, and
no DDNS to maintain. Hand-rolled WireGuard is the fallback, not the default.

Changes here are low-risk compared to firewall work, but review ACLs and
routes before exposing VLANs to remote devices.

## When to Use

- Setting up remote access from a phone or laptop to a home network.
- Deciding between split tunnel (route only home traffic) and full tunnel
  (exit node).
- Advertising home VLANs to the tailnet with subnet routers.
- Writing or reviewing tailnet ACL policies.
- Troubleshooting tunnels that will not come up or cannot reach a subnet.
- Understanding raw WireGuard config when Tailscale does not fit (no external
  coordination server allowed, embedded device, point-to-point link).

## How It Works

```
Your phone (Tailscale client)
    |
    |  Encrypted WireGuard tunnel — direct if NAT traversal succeeds,
    |  relayed via DERP if not
Tailnet coordination (control plane only — keys and policy, not traffic)
    |
Subnet router at home (a Tailscale node advertising 192.168.0.0/16 routes)
    |
Your home VLANs (NAS, DNS server, lab hosts)
```

- Every node authenticates with an identity (SSO/Google/GitHub) and gets a
  stable 100.x.y.z address plus a MagicDNS name. Keypairs are generated and
  rotated automatically.
- Traffic is peer-to-peer WireGuard; the coordination server never sees
  payload traffic.
- No public IP, port forwarding, or DDNS needed — DERP relays handle
  hard-to-traverse NATs at some latency cost.

## Core Setup

1. Install Tailscale on one always-on home host (or the OpenWrt router —
   package available via opkg) and `tailscale up` with the operator's
   account. Enable MFA on that account; it is the new root key.
2. For LAN reach, enable a **subnet router** on that node:

```bash
# Advertise only the VLANs remote users need — not 0.0.0.0/0
sudo tailscale up --advertise-routes=192.168.10.0/24,192.168.30.0/24
# Approve the routes in the admin console (or via tailscale set --accept-routes on clients)
```

3. Approve routes in the admin console, then review the **ACL policy** so
   remote users reach only intended hosts/ports — the tailnet ACL file is the
   firewall; default posture should be least privilege.
4. Install Tailscale on client devices, sign in, done. Enable MagicDNS so
   remote sessions use `nas.home.arpa`-style names (or 100.x addresses) and
   `--accept-dns=false` on clients that must keep their own resolvers.

## Split Tunnel vs Full Tunnel

```
# Split tunnel (default with subnet routers):
  Only advertised home subnets route through the tunnel; internet stays
  direct. Best for: "reach NAS/DNS/lab from anywhere."

# Full tunnel (exit node):
  Home node advertises exit:  sudo tailscale up --advertise-exit-node
  Client opts in per session:  use exit node <name>
  All traffic rides the home upload link — fine for hotel Wi-Fi, slow for
  everyday mobile.

# Multi-subnet split tunnel (most common homelab case):
  --advertise-routes=<all your VLANs>  ; internet stays direct
```

## ACLs: The Actual Security Boundary

Tailnet ACLs replace firewall rules for remote access. Keep them explicit:

```jsonc
{
  "acls": [
    // Admin devices reach management + server VLANs over SSH/HTTPS only
    {"action": "accept", "src": ["group:admin"], "dst": ["tag:server:*"]},
    // Phones reach the NAS file ports only
    {"action": "accept", "src": ["tag:phone"], "dst": ["nas.home.arpa:445,5006"]}
  ]
}
```

- Grant to tags/groups, not individual 100.x addresses.
- Auto-approvers for routes/exit nodes are a convenience — keep them narrow.
- Review after adding any new subnet router.

## Key Management

Tailscale handles key generation, rotation, and revocation per node — delete
the node in the admin console to revoke. Two rules survive from raw WireGuard:

- One Tailscale identity/node per device — never share node logins between
  people or devices.
- Disable key expiry only for headless servers, never for user devices.

## Raw WireGuard (only when Tailscale does not fit)

```bash
# Keys: one pair per peer, private keys never leave the device
umask 077
wg genkey | tee phone_private.key | wg pubkey > phone_public.key

# Server wg0.conf — concepts that matter:
[Interface]
Address = 10.8.0.1/24
ListenPort = 51820
PrivateKey = <server-private-key>
# Scope forwarding rules to wg0, never blanket FORWARD ACCEPT
PostUp = iptables -A FORWARD -i wg0 -o eth0 -j ACCEPT; \
         iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

[Peer]  # phone
PublicKey = <phone-public-key>
AllowedIPs = 10.8.0.2/32          # routing + crypto-key ACL in one
```

Client side: `Endpoint = home.example.com:51820`,
`AllowedIPs = 192.168.10.0/24` (split) or `0.0.0.0/0` (full),
`PersistentKeepalive = 25` on NATed/mobile peers. Requires IP forwarding
(`net.ipv4.ip_forward=1`), an open UDP port, and DDNS on dynamic IPs.

## Troubleshooting

```bash
tailscale status              # Who is connected, direct or relayed?
tailscale ping <node>         # Probes the tunnel itself (via/Tailscale-level)
tailscale netcheck            # NAT type, DERP reachability, IPv6
tailscale dns status          # MagicDNS state

# Ping works but service unreachable? Check in order:
# 1. ACL policy allows src -> dst:port?
# 2. Host firewall on the target (ufw, OpenWrt zone rules)?
# 3. Route approved in admin console and advertised?
# 4. Client accepting routes for non-tailnet subnets (--accept-routes)?

# Raw WireGuard equivalents:
sudo wg show                  # latest handshake — never/old = tunnel down
cat /proc/sys/net/ipv4/ip_forward   # must be 1 on routers
dmesg | grep -i wireguard
```

## Anti-Patterns

```
# BAD: Advertising 0.0.0.0/0 as a subnet route "just in case"
# GOOD: Advertise the specific VLANs remote users need

# BAD: Shared tailnet login across a household
# GOOD: One identity per person, one device per node; revoke per node

# BAD: Blanket accept-all ACL because "it's encrypted anyway"
# GOOD: A stolen phone with tailnet access reads as that phone, not as you

# BAD: Disabling key expiry on laptops/phones
# GOOD: Only headless servers get non-expiring keys

# BAD: Exit node enabled permanently on mobile
# GOOD: Exit node opt-in for untrusted networks only

# RAW WG: Sharing one keypair across devices; blanket FORWARD ACCEPT;
#          forwarding enabled but port closed (tunnel up, no traffic);
#          AllowedIPs missing the subnet you try to reach
```

## Best Practices

- Subnet routers advertise narrowly; ACLs decide who reaches what.
- MagicDNS everywhere; fall back to 100.x addresses in docs.
- `tailscale ping` distinguishes "tunnel broken" from "service broken".
- Prune stale devices from the admin console monthly.
- Raw WireGuard only when a coordination server is unacceptable — then you
  own key distribution, DDNS, port forwarding, and rotation.

## See Also

- Skill: `homelab-network-readiness`
- Skill: `homelab-vlan-segmentation`
- Skill: `homelab-pihole-dns`
