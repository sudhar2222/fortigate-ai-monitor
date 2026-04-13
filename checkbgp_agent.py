import time
import requests
import urllib3
from google.adk.tools.function_tool import FunctionTool
from session_manager import get_session, API_ENDPOINT

urllib3.disable_warnings()

def check_bgp_status(adom: str, device: str):
    SESSION = get_session()

    run = {
        "id": 1,
        "method": "exec",
        "session": SESSION,
        "params": [{
            "url": f"/dvmdb/adom/{adom}/script/execute",
            "data": {
                "adom": adom,
                "script": "checkbgp",
                "scope": [{"name": device, "vdom": "root"}]
            }
        }]
    }

    r = requests.post(API_ENDPOINT, json=run, verify=False).json()
    task_id = r["result"][0]["data"]["task"]
    expected_log_id = task_id * 10

    log_req = {
        "id": 1,
        "method": "get",
        "session": SESSION,
        "params": [{
            "url": f"/dvmdb/adom/{adom}/script/log/latest/device/{device}"
        }]
    }

    time.sleep(25)

    max_wait = 60
    interval = 5
    elapsed  = 0
    data     = {}

    while elapsed < max_wait:
        out  = requests.post(API_ENDPOINT, json=log_req, verify=False).json()
        data = out["result"][0]["data"]

        if data.get("log_id") == expected_log_id and data.get("script_name") == "checkbgp":
            return {
                "status": "success",
                "output": data.get("content", "")
            }

        time.sleep(interval)
        elapsed += interval

    return {
        "status": "timeout",
        "output": data.get("content", ""),
        "reason": f"log_id mismatch after {max_wait}s. got={data.get('log_id')} expected={expected_log_id}"
    }

check_bgp_tool = FunctionTool(check_bgp_status)