import pandas as pd

EXCEL_PATH = "site_inventory.xlsx"

def get_wan_gateway(adom: str, device: str) -> str | None:
    print("externalping agent getting wan ip from config resolver")
    try:
        df = pd.read_excel(EXCEL_PATH)
    except Exception:
        return None

    # normalize inventory
    df["adom"] = df["adom"].astype(str).str.strip().str.lower()
    df["device"] = df["device"].astype(str).str.strip().str.lower()

    adom = adom.strip().lower()
    device = device.strip().lower()
    
    row = df[
        (df["adom"] == adom) &
        (df["device"] == device)
    ]

    if row.empty:
        return None
    
    return str(row.iloc[0]["wan_gateway"]).strip()

