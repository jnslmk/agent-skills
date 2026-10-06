---
name: homelab-network-setup
description: Practical home and homelab network planning for gateways, switches, access points, IP ranges, DHCP reservations, DNS, cabling, and common beginner mistakes. Use when planning or fixing a home or homelab network — gateway, switch, AP, IP ranges, DHCP, DNS, or cabling.
---

# Homelab Network Setup

Use this skill to design a home or small-lab network that can grow without
needing a full rebuild.

## When to Use

- Planning a new home network or redesigning an ISP-router-only setup.
- Choosing gateway, switch, and access point roles.
- Designing IP ranges, DHCP scopes, static reservations, and DNS.
- Preparing for future VLANs, a local DNS server, NAS, lab servers, or VPN
  access.
- Troubleshooting a new network that has double NAT, unstable Wi-Fi, or
  changing server addresses.

## How It Works

Start by separating device roles:

```text
Internet
  |
Modem or ONT
  |
Gateway or router      NAT, firewall, DHCP, DNS, inter-VLAN routing
  |
Managed switch         wired clients, AP uplinks, optional VLAN trunks
  |
Access points          Wi-Fi only; ideally wired backhaul
Servers and NAS        stable addresses, DNS names, monitoring
Clients and IoT        DHCP pools, isolated later if VLANs are available
```

Pick a gateway that matches the operator, not just the feature checklist:

| Option | Best fit | Notes |
| --- | --- | --- |
| ISP router | Basic internet only | Limited control and often poor VLAN support |
| OpenWrt | Tinkerers who want config-as-code | Full control, uci files suit Ansible management |
| UniFi gateway | Managed home network | Good UI, ecosystem lock-in |
| OPNsense or pfSense | Firewall-focused homelabs | Strong VLAN, firewall, VPN, and DNS control |
| MikroTik | Advanced network users | Powerful, but easy to misconfigure |
| Linux router | Full-custom builds | Document rollback before using as primary gateway |

Keep gateway config as code where possible: for an OpenWrt gateway, the
`/etc/config/*` files belong in Ansible so every change is reviewable,
repeatable, and revertible.

## IP Plan

Avoid the most common default, `192.168.1.0/24`, when you expect to use VPNs.
It often conflicts with hotels, offices, and ISP routers. Also keep clear of
`100.64.0.0/10` — that is the CGNAT range Tailscale draws tailnet addresses
from.

```text
Example small homelab plan:

192.168.10.0/24  trusted clients
192.168.20.0/24  IoT and media devices
192.168.30.0/24  servers and NAS (DNS server lives here)
192.168.40.0/24  guest Wi-Fi
192.168.99.0/24  network management

Gateway convention: .1
Infrastructure reservations: .2 through .49
Dynamic DHCP pool: .50 through .240
Spare room: .241 through .254
```

Use `home.arpa` for local names. It is reserved for home networks and avoids
the leakage/conflict problems of ad hoc names like `home.lan`.

```text
nas.home.arpa
dns.home.arpa        (Technitium)
unbound.home.arpa
gateway.home.arpa
switch-01.home.arpa
```

## DHCP And DNS

- Use DHCP reservations for anything you SSH into, bookmark, monitor, or
  expose as a service.
- Hand out the gateway as DNS until a local resolver is intentionally
  deployed (OpenWrt's dnsmasq is the natural default).
- When deploying a resolver (Technitium + Unbound, Pi-hole, AdGuard Home),
  give it a reservation first, then point DHCP DNS options at that address.
- Keep a small static/reserved range per subnet so replacements do not collide
  with dynamic leases.

## Cabling And Wi-Fi

- Prefer wired AP backhaul over mesh when you can run Ethernet.
- Use a PoE switch for APs and cameras if the budget allows it.
- Label both ends of each cable and keep a simple port map.
- Put the gateway, switch, DNS server, and NAS on UPS power if outages are
  common.

## Examples

### Beginner Upgrade

Goal: Keep the ISP router but stabilize a small lab.

1. Set DHCP reservations for NAS, Pi, and any SSH hosts.
2. Move local names to `home.arpa`.
3. Disable duplicate DHCP servers on secondary routers or APs.
4. Wire the main AP instead of relying on wireless backhaul.

### VLAN-Ready Plan

Goal: Prepare for future segmentation without enabling it immediately.

1. Choose non-overlapping /24 ranges for trusted, IoT, servers, guest, and
   management.
2. Reserve .1 for the gateway and .2-.49 for infrastructure on every subnet.
3. Confirm the gateway and switch support VLANs and inter-VLAN firewall rules
   (OpenWrt with bridge VLAN filtering does).
4. Document which SSIDs and switch ports will eventually map to each network.

## Anti-Patterns

- Double NAT without a reason or documentation.
- Using `192.168.1.0/24` when VPN access is planned.
- Dynamic addresses for NAS, DNS server, Home Assistant, or other service
  hosts.
- Consumer routers repurposed as APs while their DHCP servers are still
  enabled.
- Flat networks with cameras, smart plugs, laptops, and servers all sharing
  the same trust boundary.
- Hand-editing an Ansible-managed gateway: the next apply overwrites it.

## See Also

- Skill: `homelab-network-readiness`
- Skill: `homelab-vlan-segmentation`
- Skill: `homelab-pihole-dns`
