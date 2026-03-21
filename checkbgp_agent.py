import time
import requests
import urllib3
from google.adk.tools.function_tool import FunctionTool
from session_manager import get_session, API_ENDPOINT

# ===== TOOL FUNCTION =====
def check_bgp_status(adom: str, device: str):
    SESSION = get_session()
    print("Root agent calls bgp agent..")
    run = {
        "id": 1,
        "method": "exec",
        "session": SESSION,
        "params": [{
            "url": f"/dvmdb/adom/{adom}/script/execute",
            "data": {
                "adom": adom,
                "script": "checkbgp",
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

    

    if (data.get("log_id") != task_id * 10) and (data.get("script_name") != "checkbgp"):
        return {"status": "error", "reason": "log mismatch"}

    return {
        "status": "success",
        "output": data.get("content", "")
    }

# ===== TOOL REGISTRATION =====
check_bgp_tool = FunctionTool(check_bgp_status)
