import pandas as pd

EXCEL_PATH = "site_inventory.xlsx"

def get_wan_gateway(adom: str, device: str) -> str | None:
    try:
        df = pd.read_excel(EXCEL_PATH)
    except Exception:
        return None

    df["adom"]   = df["adom"].astype(str).str.strip().str.lower()
    df["device"] = df["device"].astype(str).str.strip().str.lower()

    row = df[
        (df["adom"]   == adom.strip().lower()) &
        (df["device"] == device.strip().lower())
    ]

    if row.empty:
        return None

    return str(row.iloc[0]["wan_gateway"]).strip()