---
name: homelab-network-readiness
description: Readiness checklist for homelab VLAN segmentation, local DNS resolution, and Tailscale/WireGuard remote access before changing router, firewall, DHCP, DNS, or VPN configuration. Use before touching OpenWrt, firewall rules, DHCP scopes, DNS servers, or VPN settings on a home network.
---

# Homelab Network Readiness

Use this skill before changing a home or small-lab network that mixes VLANs,
a local DNS resolver (Technitium + Unbound, Pi-hole, AdGuard Home), firewall
rules, and remote VPN access.

This is a planning and review skill. Do not turn it into copy-paste router,
firewall, or VPN configuration unless the target platform, current topology,
rollback path, console access, and maintenance window are all known.

## When to Use

- Preparing to split a flat network into trusted, IoT, guest, server, or
  management VLANs.
- Moving DHCP clients to a local DNS resolver (Technitium, Unbound, Pi-hole,
  AdGuard Home).
- Adding or changing Tailscale, raw WireGuard, or another VPN overlay.
- Reviewing whether a homelab change can lock the operator out of the gateway,
  switch, access point, DNS server, or VPN coordination.
- Turning an informal home-network idea into a staged migration plan with
  validation evidence.

## Safety Rules

- Keep the first answer read-only: inventory, risks, staged plan, validation,
  and rollback.
- Do not expose gateway admin panels, DNS resolvers, SSH, NAS consoles, or
  management UIs directly to the public internet.
- Do not provide firewall, NAT, VLAN, DHCP, or VPN commands without a confirmed
  platform and a rollback procedure.
- Require out-of-band or same-room console access before changing management
  VLANs, trunk ports, firewall default policies, or DHCP/DNS settings.
- Keep a working path back to the internet before pointing the whole network at
  a new DNS resolver or VPN route.
- Treat IoT, guest, camera, and lab-server networks as different trust zones
  until the operator explicitly chooses otherwise.
- When router config is managed in Ansible (as on an OpenWrt gateway), change
  the source of truth and apply — never hand-edit the device in parallel, or
  the next apply reverts the fix silently.

## Required Inventory

Collect this before giving implementation steps:

| Area | Questions |
| --- | --- |
| Internet edge | What is the modem or ONT? Is the ISP router bridged or still routing? |
| Gateway | What routes, firewalls, handles DHCP, and terminates VPNs? (Here: OpenWrt router — which build, LuCI or uci/Ansible managed?) |
| Config management | Is gateway config in Ansible/version control? What is the apply and rollback procedure? |
| Switching | Which switch ports are uplinks, access ports, trunks, or unmanaged? |
| Wi-Fi | Which SSIDs map to which networks, and are APs wired or mesh? |
| Addressing | What subnets exist today, and which ranges conflict with VPN or tailnet addresses? |
| DNS/DHCP | Which service currently hands out leases and resolver addresses? Where do Technitium/Unbound run? |
| Management | How will the operator reach the gateway, switch, and AP after changes? |
| Recovery | What can be reverted locally if DNS, DHCP, VLANs, or VPN routes break? |

## VLAN And Trust-Zone Plan

Start with intent rather than vendor syntax.

| Zone | Typical contents | Default policy |
| --- | --- | --- |
| Trusted | Laptops, phones, admin workstations | Can reach shared services and management only when needed |
| Servers | NAS, Home Assistant, lab hosts, DNS resolver | Accepts narrow inbound flows from trusted clients |
| IoT | TVs, smart plugs, cameras, speakers | Internet access plus explicit exceptions only |
| Guest | Visitor devices | Internet-only, no LAN reachability |
| Management | Gateway, switches, APs, controllers | Reachable only from trusted admin devices |
| VPN | Tailscale / remote clients | Same or narrower access than trusted clients |

Before recommending VLAN IDs or subnets, confirm:

1. The gateway supports inter-VLAN routing and firewall rules.
2. The switch supports the required tagged and untagged port behavior.
3. The APs can map SSIDs to VLANs.
4. The operator knows which port they are connected through during the change.
5. The management network remains reachable after trunk and SSID changes.
6. New subnets do not overlap the tailnet range (100.64.0.0/10 CGNAT space by
   default) or any network remote clients travel through.

## DNS Readiness

A local resolver should be introduced as a dependency, not as a single point
of failure.

1. Give the resolver a reserved address before using it in DHCP options.
2. Confirm the full chain works: Technitium → Unbound → roots, plus local
   `home.arpa` names.
3. Keep the gateway resolver (OpenWrt's dnsmasq) available as a temporary
   fallback.
4. Test one client or one VLAN before changing every DHCP scope.
5. Document which networks may bypass filtering and why.
6. Check that blocking rules do not break captive portals, work VPNs, firmware
   updates, or medical/security devices.

Useful validation evidence:

```text
Client gets expected DHCP lease
Client receives expected DNS resolver
Public DNS lookup succeeds (dig @<resolver> example.com)
Local home.arpa lookup succeeds
Blocked test domain is blocked only where intended
Gateway and DNS admin interfaces are not reachable from guest or IoT networks
Tailscale reachable from trusted VLAN; MagicDNS resolves host names
```

## Remote Access Readiness

For Tailscale (WireGuard-based overlay), decide what the VPN is allowed to
reach before exposing anything.

| Mode | Use when | Risk notes |
| --- | --- | --- |
| Subnet router to selected VLANs | Remote admin for NAS or lab hosts | Keep the advertised route list narrow |
| Selected services via ACLs | Access specific apps by node or tag | Requires a reviewed tailnet ACL policy |
| Exit node (full tunnel) | Untrusted networks or travel | All client traffic rides home upload; enable per session |
| Raw WireGuard server | No coordination server acceptable | You own key distribution, DDNS, and port forwarding |

Tailscale needs no port forwarding or DDNS — but still confirm:

- The tailnet ACL policy grants remote users only the flows they need.
- Subnet routers advertise only intended VLANs, and ACLs gate them.
- Exit nodes are opt-in per client, not blanket.
- Devices are authenticated to the operator's tailnet (not shared) and stale
  devices are pruned.
- Login/identity provider compromise is the new key-compromise: MFA on the
  tailnet account matters more than firewall ports.

For raw WireGuard, additionally check that the endpoint is patched, the
forwarded port goes only to the VPN service, and peer keys can be revoked
without rebuilding the network.

## Change Sequence

Prefer small, reversible changes:

1. Snapshot the current topology, IP plan, DHCP settings, DNS settings, and
   firewall rules (commit current Ansible state first).
2. Reserve infrastructure addresses for gateway, DNS, controller, APs, NAS, and
   VPN endpoint.
3. Create the new zone or VLAN without moving critical devices.
4. Move one test client and validate DHCP, DNS, routing, internet, and block
   behavior.
5. Add narrow firewall exceptions for required flows.
6. Move one low-risk device group.
7. Add Tailscale access with the narrowest routes and ACLs that satisfy the use
   case.
8. Document final state, known exceptions, and rollback (for Ansible: the
   previous commit plus apply command).

## Review Checklist

- Each network has a reason to exist and a clear trust boundary.
- No management interface is reachable from guest, IoT, or the public internet.
- DNS failure does not take down the operator's ability to recover locally.
- DHCP scope changes were tested on one client before broad rollout.
- VPN clients receive only the routes and DNS settings they need.
- Firewall rules are default-deny between zones, with named exceptions.
- The operator can still reach gateway, switch, AP, DNS, and VPN admin surfaces.
- Rollback is documented in the same vocabulary as the chosen platform UI or
  CLI (uci/LuCI for OpenWrt).

## Anti-Patterns

- Segmenting networks before knowing which switch ports and SSIDs carry which
  VLANs.
- Moving the admin workstation off the only reachable management network.
- Pointing all DHCP scopes at a new resolver before testing fallback DNS.
- Publishing NAS, DNS, router, or hypervisor management directly to the
  internet.
- Treating tailnet access as equivalent to full trusted-LAN access without
  ACLs.
- Adding allow-all firewall rules temporarily and forgetting to remove them.
- Copying commands from another vendor or firmware version without checking
  the exact platform syntax (OpenWrt uci syntax differs from stock firmware).

## See Also

- Skill: `homelab-network-setup`
- Skill: `homelab-vlan-segmentation`
- Skill: `homelab-wireguard-vpn`
- Skill: `homelab-pihole-dns`
