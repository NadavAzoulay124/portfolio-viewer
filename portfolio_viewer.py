# portfolio_viewer.py
import json, os, pathlib, tempfile
from datetime import date

import lseg.data as ld
import pandas as pd
import streamlit as st

# ────────────────────────── 1. PAGE CONFIG ───────────────────────────
st.set_page_config("Portfolio Viewer", layout="wide")
st.title("📈 Portfolio Viewer — Long / Short with PnL")

# ────────────────────────── 2. SESSION BOOTSTRAP ─────────────────────
# template JSON (placeholders only) must be in the same folder
template_path = pathlib.Path(__file__).with_name("rdp_template.json")

if template_path.exists():
    cfg = json.loads(template_path.read_text())
else:  # minimal fallback when file missing
    cfg = {
        "sessions": {
            "platform.rdp": {
                "type": "platform",
                "credential": {"app_key": "", "username": "", "password": ""},
                "state": "enabled",
            }
        }
    }

cred = cfg["sessions"]["platform.rdp"]["credential"]
cred["app_key"] = st.secrets["RDP_APP_KEY"]
cred["username"] = st.secrets["RDP_USERNAME"]
cred["password"] = st.secrets["RDP_PASSWORD"]

tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
json.dump(cfg, tmp); tmp.close()
os.environ["RDP_CONFIG_PATH"] = tmp.name     # <- SDK picks this up

session = ld.open_session("platform.rdp").open()  # default session

# ────────────────────────── 3. HELPERS ───────────────────────────────
REQ_LONG  = ["Instrument", "ICB Industry", "Weight"]
REQ_SHORT = ["Instrument.1", "ICB Industry.1", "Weight.1"]

def split_excel(file):
    df = pd.read_excel(file)

    miss_long  = set(REQ_LONG)  - set(df.columns)
    miss_short = set(REQ_SHORT) - set(df.columns)
    if miss_long or miss_short:
        raise ValueError(
            f"Missing columns — long: {miss_long or 'OK'}, "
            f"short: {miss_short or 'OK'}"
        )

    longs  = df[REQ_LONG].copy()
    shorts = df[REQ_SHORT].copy()
    shorts.columns = ["Instrument", "ICB Industry", "Weight"]
    return longs, shorts

@st.cache_data(ttl=10 * 60)
def fetch_last(rics):
    resp = ld.get_data(session=session, universe=rics, fields=["TRDPRC_1"])
    return resp.set_index("RIC")["TRDPRC_1"].dropna().to_dict()

@st.cache_data(ttl=24 * 60 * 60)
def fetch_close(rics, d):
    resp = ld.get_data(
        session=session,
        universe=rics,
        fields=["CLOSE"],
        parameters={"SDate": d, "EDate": d},
    )
    return resp.set_index("RIC")["CLOSE"].dropna().to_dict()

# ────────────────────────── 4. UI WIDGETS ────────────────────────────
uploaded = st.file_uploader(
    "Upload portfolio Excel",
    type=["xlsx", "xls"],
    help="Longs: Instrument / ICB Industry / Weight • "
         "Shorts: Instrument.1 / ICB Industry.1 / Weight.1",
)

exec_day = st.date_input(
    "Execution date (closing price reference)",
    value=date.today(),
)
exec_str = exec_day.strftime("%Y-%m-%d")

# ────────────────────────── 5. MAIN FLOW ─────────────────────────────
if uploaded:
    try:
        longs_df, shorts_df = split_excel(uploaded)
        st.success(f"Excel OK — fetching prices for {exec_str}…")

        rics = longs_df["Instrument"].tolist() + shorts_df["Instrument"].tolist()
        last_px  = fetch_last(rics)
        close_px = fetch_close(rics, exec_str)

        def enrich(df):
            df["LastPrice"] = df["Instrument"].map(last_px)
            df["ExecClose"] = df["Instrument"].map(close_px)
            df["PnL %"] = ((df["LastPrice"] - df["ExecClose"])
                           / df["ExecClose"] * 100).round(2)
            return df

        longs_df  = enrich(longs_df)
        shorts_df = enrich(shorts_df)

        tab_long, tab_short = st.tabs(["Long positions", "Short positions"])
        with tab_long:
            st.dataframe(longs_df, use_container_width=True)
        with tab_short:
            st.dataframe(shorts_df, use_container_width=True)

    except Exception as err:
        st.error(f"❌ {err}")

else:
    st.info("Upload an Excel file, then pick the execution date.")

# ────────────────────────── 6. CLEANUP ───────────────────────────────
# (Not strictly necessary; session auto-closes on app shutdown)
# session.close()
