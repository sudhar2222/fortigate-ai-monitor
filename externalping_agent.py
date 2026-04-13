import requests
from google.adk.tools.function_tool import FunctionTool
from config_resolver import get_wan_gateway

API_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
PING_API = "https://api.geekflare.com/ping"


def external_ping(adom: str, device: str) -> dict:
    print("Root agent calls external ping agent..")

    """
    Resolve WAN gateway from inventory and ping it
    to validate underlay connectivity.
    """

    if not API_KEY:
        return {
            "status": "error",
            "reason": "GEEKFLARE_API_KEY not configured"
        }

    # 🔑 Resolve WAN IP from inventory
    wan_ip = get_wan_gateway(adom, device)

    if not wan_ip:
        return {
            "status": "error",
            "reason": f"WAN gateway not found in inventory for {device} ({adom})"
        }

    try:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": API_KEY
        }

        payload = {"url": wan_ip}

        response = requests.post(
            PING_API,
            json=payload,
            headers=headers,
            timeout=20
        )

        response.raise_for_status()

        return {
            "status": "success",
            "target": wan_ip,
            "result": response.json()
        }

    except Exception as e:
        return {
            "status": "error",
            "target": wan_ip,
            "message": str(e)
        }


# ===== TOOL REGISTRATION =====
external_ping_tool = FunctionTool(external_ping)
