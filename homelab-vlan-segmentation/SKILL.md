---
name: homelab-vlan-segmentation
description: Segmenting home networks into VLANs for IoT, guest, trusted, and server traffic — design, switch trunk/access ports, SSID mapping, and firewall rules, with OpenWrt (uci) as the concrete example. Use when splitting a home network into IoT, guest, trusted, and server VLANs on an OpenWrt router or similar.
---

# Homelab VLAN Segmentation

How to split a home network into isolated VLANs so IoT devices, guests, and
your main PCs cannot talk to each other. The most impactful security upgrade
for a home network.

All firewall rules shown here add isolation between segments — they do not
remove existing protections. Apply changes in a maintenance window, verify
connectivity between segments after each step, and (on an Ansible-managed
gateway) make changes in the Ansible-managed config, not by hand on the
device.

## When to Use

- Setting up VLANs on a home network for the first time.
- Isolating IoT devices (smart bulbs, cameras, TVs) from trusted devices.
- Creating a guest Wi-Fi network that cannot reach home devices.
- Configuring trunk ports, access ports, and SSID-to-VLAN mapping.
- Troubleshooting inter-VLAN routing or firewall rules.

## How It Works

```
Without VLANs — flat network:
  All devices on 192.168.1.0/24
  Smart TV (potential malware) → can reach your NAS, PCs, everything

With VLANs:
  VLAN 10 — Trusted    192.168.10.0/24  (PCs, phones, laptops)
  VLAN 20 — IoT        192.168.20.0/24  (smart TV, bulbs, cameras)
  VLAN 30 — Servers    192.168.30.0/24  (NAS, DNS server, VMs)
  VLAN 40 — Guest      192.168.40.0/24  (visitor Wi-Fi)
  VLAN 99 — Management 192.168.99.0/24  (switch/AP web UIs)

  Smart TV → blocked from reaching 192.168.10.0/24 and 192.168.30.0/24
  Guests → internet only, cannot see any home devices
```

## VLAN Design Template

```
VLAN  Name        Subnet              Gateway         Purpose
10    trusted     192.168.10.0/24     192.168.10.1    PCs, phones, laptops
20    iot         192.168.20.0/24     192.168.20.1    Smart home devices
30    servers     192.168.30.0/24     192.168.30.1    NAS, DNS, self-hosted
40    guest       192.168.40.0/24     192.168.40.1    Visitor Wi-Fi
99    management  192.168.99.0/24     192.168.99.1    Network gear web UIs
```

## Example Layout

```
Scenario: OpenWrt gateway (all-in-one router with switch+radio) + managed switch + APs

VLAN 10 — Trusted    MacBook, phones, admin workstation
VLAN 20 — IoT        Thermostat, smart bulbs, cameras, TVs
VLAN 30 — Servers    NAS (192.168.30.10), Technitium+Unbound DNS (192.168.30.2)
VLAN 40 — Guest      Visitor Wi-Fi — internet only

SSID → VLAN mapping:
  "Home"  → VLAN 10 (WPA2/WPA3, strong password, trusted devices only)
  "IoT"   → VLAN 20 (separate password)
  "Guest" → VLAN 40 (shareable password)

Switch port behavior:
  Port 1   → trunk to gateway (tagged 10,20,30,40,99)
  Port 2   → trunk to APs (tagged VLANs the AP serves)
  Port 3   → access VLAN 30 (NAS — untagged)
  Port 4   → access VLAN 30 (DNS server — untagged)
  Port 5-8 → access VLAN 10 (wired workstations)

Firewall intent (all rules add isolation):
  IoT → Trusted: BLOCK
  IoT → Servers: BLOCK except 192.168.30.2:53 (DNS) and named exceptions
  Guest → any local network: BLOCK
  Trusted → everywhere: ALLOW
```

## OpenWrt Configuration

OpenWrt uses bridge VLAN filtering: the `br-lan` bridge carries tagged VLANs
to trunk ports and untags them for access ports. Check actual port names with
`ip link` / LuCI — they vary by device (e.g. `lan1`..`lan4`, `wan`).

```bash
# /etc/config/network — bridge with VLAN filtering (repeat per VLAN)

config device
    option name 'br-lan'
    option type 'bridge'
    list ports 'lan1'
    list ports 'lan2'
    list ports 'lan3'
    list ports 'lan4'

# Trunk on lan1 (to switch/APs): tagged. Access on lan2: untagged VLAN 10.
config bridge-vlan
    option device 'br-lan'
    option vlan '10'
    list ports 'lan1:t'
    list ports 'lan2:u'

config bridge-vlan
    option device 'br-lan'
    option vlan '20'
    list ports 'lan1:t'

config interface 'trusted'
    option device 'br-lan.10'
    option proto 'static'
    option ipaddr '192.168.10.1'
    option netmask '255.255.255.0'

config interface 'iot'
    option device 'br-lan.20'
    option proto 'static'
    option ipaddr '192.168.20.1'
    option netmask '255.255.255.0'
```

```bash
# /etc/config/dhcp — one pool per VLAN
config dhcp 'iot'
    option interface 'iot'
    option start '100'
    option limit '150'
    option leasetime '12h'
    list dhcp_option '6,192.168.30.2'   # hand the DNS server to clients
```

```bash
# /etc/config/wireless — map an SSID to a VLAN network
wifi-iface
    option device 'radio0'
    option mode 'ap'
    option ssid 'IoT'
    option network 'iot'        # ties the SSID to the VLAN interface
    option encryption 'psk2'
    option key '<separate-password>'
```

```bash
# /etc/config/firewall — one zone per VLAN, default-deny forwarding

config zone
    option name 'iot'
    list network 'iot'
    option input 'REJECT'
    option output 'ACCEPT'
    option forward 'REJECT'

config forwarding          # IoT may reach the internet
    option src 'iot'
    option dest 'wan'

config rule                # IoT may use the DNS server only
    option name 'IoT-to-DNS'
    option src 'iot'
    option dest 'servers'
    option dest_ip '192.168.30.2'
    option dest_port '53'
    option proto 'tcpudp'
    option target 'ACCEPT'

config rule                # named exception before the block rule
    option name 'IoT-to-HA'
    option src 'iot'
    option dest 'servers'
    option dest_ip '192.168.30.5'
    option dest_port '8123'
    option proto 'tcp'
    option target 'ACCEPT'
# No forwarding iot -> trusted/lans zone = blocked by the zone defaults.
```

Apply with `/etc/init.d/network restart` (careful: you are connected through
one of these ports) or push via Ansible. Ansible's `openwrt_init`/raw-uci
modules manage these same files over SSH — keep `/etc/config/network`,
`dhcp`, `wireless`, `firewall` in the playbook as the source of truth.

## Other Platforms (same concepts, different syntax)

- **pfSense/OPNsense**: create VLANs on the LAN NIC parent, assign
  interfaces, DHCP per interface, firewall rules per interface tab — rules
  are first-match top-down, so the DNS allow rule must precede the RFC1918
  block.
- **UniFi**: Settings → Networks per VLAN, per-SSID network selection,
  Traffic Rules for zone policy.
- **MikroTik**: bridge VLAN filtering (`/interface bridge vlan`), `pvid` for
  access ports, `/ip firewall filter` for inter-zone drops.

## Switch Trunk vs Access Ports

```
# Trunk port: carries multiple VLANs (tagged) — switch-to-switch, switch-to-router, switch-to-AP
# Access port: carries one VLAN (untagged) — connects to end devices

# Port to router/switch/AP: trunk, allowed VLANs = those it must carry
# Port to PC/camera/NAS: access port, no tagging — the device never sees VLANs
# AP uplink: trunk; the AP tags each SSID's traffic with its VLAN ID
```

## Anti-Patterns

```
# BAD: Creating VLANs without firewall rules
# Inter-VLAN routing is open by default — VLANs without rules give no isolation

# BAD: Putting the DNS server in the IoT VLAN
# GOOD: DNS in Servers VLAN with a port-53 allow rule for all VLANs

# BAD: Native (untagged) VLAN equals management VLAN
# Untagged traffic landing in management enables VLAN hopping
# GOOD: Dedicated unused native VLAN (e.g. 999); keep management tagged

# BAD: Same Wi-Fi password for IoT SSID and trusted SSID
# Anyone who learns it can put devices on the wrong segment

# BAD: Editing /etc/config/* by hand on an Ansible-managed gateway
# Next apply reverts the change — edit the playbook instead
```

## Best Practices

- Start with 4 VLANs: Trusted, IoT, Servers, Guest — add more as needed.
- DNS server in the Servers VLAN; a port-53 allow rule from every VLAN comes
  before any RFC1918 block rule.
- Test isolation after every rule change: from IoT, ping a trusted device —
  it should fail.
- Management UIs live on the management VLAN, reachable only from trusted.
- Document the design: VLAN ID, name, subnet, purpose — in the Ansible
  inventory so plan and config stay in sync.

## See Also

- Skill: `homelab-network-readiness`
- Skill: `homelab-network-setup`
- Skill: `homelab-pihole-dns`
- Skill: `homelab-wireguard-vpn`
