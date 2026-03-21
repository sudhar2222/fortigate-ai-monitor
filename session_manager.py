import time
import requests
import urllib3

urllib3.disable_warnings()

FMG_IP = "192.168.10.10"
USERNAME = "admin"
PASSWORD = "admin"
API_ENDPOINT = f"https://{FMG_IP}/jsonrpc"

_SESSION = {
    "id": None,
    "created_at": 0
}

SESSION_TTL = 300  # 5 minutes


def _login() -> str:
    payload = {
        "id": 1,
        "method": "exec",
        "params": [{
            "url": "/sys/login/user",
            "data": {
                "user": USERNAME,
                "passwd": PASSWORD
            }
        }]
    }

    r = requests.post(API_ENDPOINT, json=payload, verify=False, timeout=10)
    r.raise_for_status()

    return r.json()["session"]


def get_session() -> str:
    print("Root agent calls session manager..")
    now = time.time()

    # reuse session if still valid
    if _SESSION["id"] and (now - _SESSION["created_at"] < SESSION_TTL):
        return _SESSION["id"]

    # otherwise create new session
    session_id = _login()
    _SESSION["id"] = session_id
    _SESSION["created_at"] = now

    return session_id
