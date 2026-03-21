# FortiManager Network Health Agents

An AI-powered network health monitoring system built with **Google ADK (Agent Development Kit)** and **Gemini 2.0 Flash**. It automates FortiGate site health checks — VPN, BGP, and underlay connectivity — by orchestrating FortiManager API calls through a multi-agent architecture.

---

## Overview

When a network alert comes in (WAN down, host down, BGP neighbor down), instead of logging into FortiManager manually and running scripts one by one, you describe the alert in natural language and the root agent decides which checks to run, delegates to the appropriate tools, and produces a final health summary.

```
User: "dev_adom / fgt-spoke / host down power issue"
  └─► Root Agent (Gemini 2.0 Flash)
        └─► BGP Health Check  ──► FortiManager API ──► FortiGate CLI output
              └─► Summary: "Site is UP. BGP sessions are Established."
```

---

## Architecture

```
app.py                  ← ADK Web entrypoint (Runner + SessionService)
root_agent.py           ← Orchestrator: decides which tools to call
├── checkbgp_agent.py   ← Tool: runs BGP check script via FortiManager
├── checkvpn_agent.py   ← Tool: runs VPN check script via FortiManager
├── externalping_agent.py ← Tool: pings WAN gateway via Geekflare API
├── config_resolver.py  ← Resolves WAN gateway IP from site_inventory.xlsx
└── session_manager.py  ← FortiManager session with TTL-based reuse
```

### Agent Decision Logic

| Alert Pattern | Checks Triggered |
|---|---|
| `<adom> / <device> / wan down` | VPN + BGP |
| `<adom> / <device> / BGP neighbor <ip> down` | BGP only |
| `<adom> / <device> / host down` | Underlay (ping) + BGP |
| `<adom> / <device> / host down power issue` | BGP only |
| `<adom> / <device> / overall health` | Underlay → VPN → BGP |

BGP session status is always the **authoritative indicator** of site health.

---

## Prerequisites

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`
- Google ADK: `google-adk`
- Access to a FortiManager instance
- [Geekflare API key](https://geekflare.com/api/) (for external ping)

### FortiManager Requirements

Two CLI scripts must be pre-created on FortiManager under the target ADOM:

| Script Name | Purpose |
|---|---|
| `checkbgp` | Runs BGP diagnostic commands on the target FortiGate |
| `checkvpn` | Runs VPN diagnostic commands on the target FortiGate |

---

## Installation

```bash
# Clone the repo
git clone https://github.com/<your-username>/fortimanager-health-agents.git
cd fortimanager-health-agents

# Create and activate virtual environment
uv venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# Install dependencies
uv pip install google-adk requests pandas openpyxl urllib3
```

---

## Configuration

### 1. FortiManager credentials — `session_manager.py`

```python
FMG_IP    = "192.168.10.10"   # Your FortiManager IP
USERNAME  = "admin"
PASSWORD  = "admin"
```

> **Note:** For production use, move credentials to environment variables or a `.env` file (see [Security](#security)).

### 2. Geekflare API key — `externalping_agent.py`

```python
API_KEY = "your_geekflare_api_key_here"
```

### 3. Site inventory — `site_inventory.xlsx`

Create an Excel file with the following columns:

| adom | device | wan_gateway |
|---|---|---|
| dev_adom | fgt-spoke | 203.0.113.1 |
| prod_adom | fgt-branch-01 | 198.51.100.1 |

The `wan_gateway` value is used by the external ping tool to validate underlay connectivity.

---

## Usage

### Run via ADK Web (recommended)

```bash
adk web
```

Open `http://localhost:8000` and type alerts in the chat interface.

### Run via CLI (standalone)

Edit the query in `root_agent.py` under `main()`:

```python
text="dev_adom / fgt-spoke / host down power issue"
```

Then run:

```bash
python root_agent.py
```

### Example Queries

```
dev_adom / fgt-spoke / wan down
dev_adom / fgt-spoke / BGP neighbor 10.0.0.1 down
prod_adom / fgt-branch-01 / host down
prod_adom / fgt-branch-01 / host down power issue
dev_adom / fgt-spoke / overall health
```

---

## Project Structure

```
fortimanager-health-agents/
├── app.py                   # ADK Web runner
├── root_agent.py            # Root coordinator agent
├── checkbgp_agent.py        # BGP health tool
├── checkvpn_agent.py        # VPN health tool
├── externalping_agent.py    # Underlay ping tool
├── config_resolver.py       # WAN IP lookup from inventory
├── session_manager.py       # FortiManager session management
├── site_inventory.xlsx      # Site-to-WAN-gateway mapping
├── .adk/                    # ADK project config
├── agents/                  # (reserved for sub-agent expansions)
├── requirements.txt
└── README.md
```

---

## Security

> The default config has credentials hardcoded — **do not commit these to a public repo**.

Use environment variables instead:

```python
import os
FMG_IP   = os.environ["FMG_IP"]
USERNAME = os.environ["FMG_USER"]
PASSWORD = os.environ["FMG_PASS"]
API_KEY  = os.environ["GEEKFLARE_API_KEY"]
```

Add a `.env` file and load with `python-dotenv`, and make sure `.env` is in `.gitignore`.

---

## How It Works

1. **Session Manager** — logs into FortiManager once and reuses the session token for 5 minutes (TTL-based).
2. **Script Execution** — each health tool triggers a pre-created FortiManager CLI script on the target FortiGate device via the `/dvmdb/adom/{adom}/script/execute` API endpoint.
3. **Log Retrieval** — after a 10-second wait, the tool fetches the script execution log from `/dvmdb/adom/{adom}/script/log/latest/device/{device}`.
4. **Root Agent** — Gemini 2.0 Flash receives the raw CLI output and produces a structured health summary based on the agent instruction rules.

---

## Limitations

- Script execution has a hardcoded 10-second `time.sleep()` — large FortiGates with slow CLI may need this increased.
- The log match validation (`log_id != task_id * 10`) assumes a specific FortiManager log ID convention; verify this against your FMG version.
- External ping uses the Geekflare API (requires an active API key and internet access from the machine running the agent).

---

## License

MIT
