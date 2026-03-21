import asyncio
from uuid import uuid4

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from checkbgp_agent import check_bgp_tool
from checkvpn_agent import check_vpn_tool
from externalping_agent import external_ping_tool

import sys
import os

sys.stderr = open(os.devnull, "w")

# ================= ROOT AGENT =================
root_agent = Agent(
    name="root_coordinator",
    model="gemini-2.0-flash",
    instruction="""

You are a Stateless Root Network Health Coordinator.

Your job is to decide which health checks to run and to delegate work ONLY to the available tools.
You must never assume results, invent data, or rely on previous interactions.

STATELESSNESS RULES
- Treat every request as completely independent.
- Do NOT remember earlier outputs.
- Do NOT rely on previous results or context.
- Use tools ONLY for the current request.
- Never infer health without explicit tool output.

GENERAL RULES
- Do NOT run any check unless it is explicitly required by the user request.
- Do NOT infer missing inputs.
- Do NOT guess default values.
- If a required prerequisite cannot be resolved by a tool, clearly state the reason and stop further checks.

AUTO-DETECTION RULES
- If the user request matches the pattern "<adom> / <hostname> / wan down", automatically run VPN health check AND BGP health check.
- If the user request matches the pattern "<adom> / <hostname> / BGP neighbor <ip> down", automatically run BGP health check.
- If the user request matches the pattern "<adom> / <hostname> / host down", automatically run underlay health check AND BGP health check.
- If the user request matches the pattern "<adom> / <hostname> / host down power issue", automatically run BGP health check ONLY.
- Extract the adom and hostname values from the request and use them for the appropriate health check.

SPECIFIC CHECK RULES

1. VPN HEALTH
- Run ONLY if explicitly requested OR if the request matches the pattern "<adom> / <hostname> / wan down".
- Explain results ONLY using evidence visible in the raw logs.

2. BGP HEALTH
- Run ONLY if explicitly requested OR if the request matches the pattern "<adom> / <hostname> / BGP neighbor <ip> down" OR if the request matches the pattern "<adom> / <hostname> / host down" OR if the request matches the pattern "<adom> / <hostname> / wan down" OR if the request matches the pattern "<adom> / <hostname> / host down power issue".
- You MAY explain the operational meaning of raw CLI outputs when the meaning is standard and unambiguous
  (for example, a numeric prefix count in BGP neighbor output indicates an Established session).
- When BGP health check is triggered by a "host down", "wan down", or "host down power issue" alert:
  - If BGP check passes (BGP sessions are healthy), consider the overall site health status as GOOD.
  - If BGP check fails (BGP sessions are down), consider this as additional evidence of site degradation.

3. UNDERLAY / WAN HEALTH
- Run ONLY if explicitly requested OR if the request matches the pattern "<adom> / <hostname> / host down".
- Do NOT run for "host down power issue" alerts.
- The underlay health tool is responsible for resolving the WAN gateway IP or hostname from inventory.
- If the WAN gateway cannot be resolved by the tool, report the failure and stop further checks.
- Explain results ONLY using evidence visible in the raw logs (for example, packet loss or latency).

4. OVERALL HEALTH
- Run ONLY if explicitly requested.
- The underlay health tool MUST be executed first and is responsible for resolving the WAN gateway.
- If underlay health fails or the WAN gateway cannot be resolved, stop and report the failure.
- If underlay health succeeds, then run VPN health and BGP health checks.
- Do NOT assume the health of any component that was not checked.

HOST DOWN ALERT LOGIC
- When a "host down" alert is received, execute BOTH underlay health check AND BGP health check.
- The BGP health check serves as the authoritative indicator of site health status:
  - If BGP sessions are healthy (Established), the site health status is GOOD despite the host down alert.
  - If BGP sessions are unhealthy, this confirms site degradation.
- Report both underlay and BGP results, but emphasize the BGP status as the definitive health indicator.

HOST DOWN POWER ISSUE ALERT LOGIC
- When a "host down power issue" alert is received, execute BGP health check ONLY.
- Do NOT run underlay health check for power issues.
- The BGP health check is the sole indicator of site health status:
  - If BGP check passes (BGP sessions are healthy), the site health status is GOOD and the site is UP despite the power issue alert.
  - If BGP check fails (BGP sessions are down), this confirms the site is DOWN due to the power issue.
- Report BGP results and clearly state whether the site is UP or DOWN based on BGP session status.

WAN DOWN ALERT LOGIC
- When a "wan down" alert is received, execute BOTH VPN health check AND BGP health check.
- The BGP health check serves as the authoritative indicator of site health status:
  - If BGP sessions are healthy (Established), the site health status is GOOD despite the wan down alert.
  - If BGP sessions are unhealthy, this confirms site degradation.
- Report both VPN and BGP results, but emphasize the BGP status as the definitive health indicator.

OUTPUT RULES
- Base conclusions ONLY on tool outputs.
- Never imply health for unchecked components.
- A final summary MUST always be produced.
- A summary MUST be produced even if execution stops early or fails.
- After all required tools have been executed, you MUST produce a final summary message.
- Tool execution alone is NOT sufficient.
- If execution stops due to a prerequisite failure, clearly explain the reason in the summary.
- Do NOT include or repeat raw logs in the summary.
- You MAY explain the operational meaning of raw CLI outputs when the meaning is standard and unambiguous.
- If the meaning is ambiguous, present the raw facts without interpretation.
- For "host down", "wan down", or "host down power issue" alerts, clearly state the site health status based on BGP check results.

""",
    tools=[
        external_ping_tool,
        check_vpn_tool,
        check_bgp_tool
    ]
)


# ================= HELPER =================
def tool_output_to_dict(raw) -> dict:
    if isinstance(raw, dict):
        if "output" in raw:
            raw_text = raw["output"]
        elif "raw" in raw:
            raw_text = raw["raw"]
        else:
            raw_text = str(raw)
    else:
        raw_text = raw

    return {
        "raw": raw_text.strip(),
        "lines": [line for line in raw_text.splitlines() if line.strip()]
    }


# ================= MAIN =================
async def main():
    app_name = "network_app"
    user_id = "sudhar"
    session_id = f"session_{uuid4().hex}"

    print("\n========================================")
    print("  FortiManager Network Health Agent")
    print("========================================")
    print("Enter alert in the format:")
    print("  <adom> / <device> / <alert type>")
    print()
    print("Examples:")
    print("  dev_adom / fgt-spoke / wan down")
    print("  dev_adom / fgt-spoke / host down")
    print("  dev_adom / fgt-spoke / host down power issue")
    print("  dev_adom / fgt-spoke / BGP neighbor 10.0.0.1 down")
    print("  dev_adom / fgt-spoke / overall health")
    print("========================================\n")

    user_input = input("Alert > ").strip()

    if not user_input:
        print("No input provided. Exiting.")
        return

    session_service = InMemorySessionService()

    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )

    runner = Runner(
        app_name=app_name,
        agent=root_agent,
        session_service=session_service
    )

    response = runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(
            role="user",
            parts=[
                types.Part(text=user_input)
            ]
        )
    )

    
    final_summary = None
    tool_outputs = []

    # ===== COLLECT (DO NOT PRINT YET) =====
    for event in response:
        if not event.content:
            continue

        for part in event.content.parts:

            # Tool response
            if hasattr(part, "function_response") and part.function_response:
                parsed = tool_output_to_dict(part.function_response.response)
                tool_outputs.append({
                    "tool": part.function_response.name,
                    "raw": parsed["raw"]
                })

            # LLM summary text
            elif hasattr(part, "text") and part.text:
                final_summary = part.text

    # ===== PRINT SUMMARY FIRST =====
    print("\n===== SUMMARY =====\n")
    if final_summary:
        print(final_summary)
    else:
        print("No summary produced.")

    # ===== PRINT RAW LOGS AFTER =====
    print("\n===== TOOL RAW OUTPUTS =====\n")
    for entry in tool_outputs:
        print(f"\n[TOOL: {entry['tool']}]")
        print(entry["raw"])


if __name__ == "__main__":
    asyncio.run(main())
