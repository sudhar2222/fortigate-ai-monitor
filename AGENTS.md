# Agent Behavior Reference

This document describes how the root agent decides which tools to invoke for each alert type.

---

## Alert Patterns and Tool Dispatch

### `wan down`
```
<adom> / <device> / wan down
```
Tools: `check_vpn_status` → `check_bgp_status`

The agent checks VPN tunnel health first, then BGP. BGP session status is the final verdict on site health.

---

### `BGP neighbor down`
```
<adom> / <device> / BGP neighbor <ip> down
```
Tools: `check_bgp_status`

BGP-only check. No VPN or underlay check is triggered.

---

### `host down`
```
<adom> / <device> / host down
```
Tools: `external_ping` → `check_bgp_status`

The agent pings the WAN gateway (resolved from `site_inventory.xlsx`) and checks BGP. Even if the ping fails, a healthy BGP session means the site is UP.

---

### `host down power issue`
```
<adom> / <device> / host down power issue
```
Tools: `check_bgp_status`

No underlay ping — power issues make the ping unreliable. BGP is the sole health indicator.

---

### `overall health`
```
<adom> / <device> / overall health
```
Tools: `external_ping` → `check_vpn_status` → `check_bgp_status`

Full stack check. If underlay ping fails or WAN gateway cannot be resolved, execution stops and no further checks run.

---

## Health Verdict Logic

| BGP Sessions | Verdict |
|---|---|
| All Established | Site is **UP** |
| Any session down | Site is **DEGRADED / DOWN** |

The agent never infers health for components that were not checked.

---

## Statelessness

Each request is treated as fully independent. The agent does not carry context between sessions. All decisions are based only on the current tool outputs.

---

## FortiManager Script Execution Flow

```
Tool called
  └─► session_manager.get_session()     # Login or reuse cached token
  └─► POST /dvmdb/adom/{adom}/script/execute
        data: { script: "checkbgp"|"checkvpn", scope: [{name, vdom}] }
  └─► sleep(10)                          # Wait for script to run on device
  └─► GET /dvmdb/adom/{adom}/script/log/latest/device/{device}
  └─► Validate: log_id and script_name match
  └─► Return raw CLI output to root agent
```
