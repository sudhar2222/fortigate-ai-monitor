import time
import requests
import urllib3
from google.adk.tools.function_tool import FunctionTool
from session_manager import get_session, API_ENDPOINT

urllib3.disable_warnings()


# ===== TOOL FUNCTION =====
def check_vpn_status(adom: str, device: str):
    SESSION = get_session()
    print("Root agent calls vpn agent..")
    run = {
        "id": 1,
        "method": "exec",
        "session": SESSION,
        "params": [{
            "url": f"/dvmdb/adom/{adom}/script/execute",
            "data": {
                "adom": adom,
                "script": "checkvpn",
                "scope": [{
                    "name": device,
                    "vdom": "root"
                }]
            }
        }]
    }

    r = requests.post(API_ENDPOINT, json=run, verify=False).json()
    
    task_id = r["result"][0]["data"]["task"]

    time.sleep(10)

    log = {
        "id": 1,
        "method": "get",
        "session": SESSION,
        "params": [{
            "url": f"/dvmdb/adom/{adom}/script/log/latest/device/{device}"
        }]
    }
    
    out = requests.post(API_ENDPOINT, json=log, verify=False).json()
    data = out["result"][0]["data"]


    if (data.get("log_id") != task_id * 10) and (data.get("script_name") != "checkvpn"):
        return {"status": "error", "reason": "log mismatch"}

    return {
        "status": "success",
        "output": data.get("content", "")
    }

# ===== TOOL REGISTRATION =====
check_vpn_tool = FunctionTool(check_vpn_status)
