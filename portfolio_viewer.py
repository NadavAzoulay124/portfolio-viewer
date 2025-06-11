import streamlit as st
import pandas as pd
import lseg.data as ld
from datetime import date
import json, os, pathlib, tempfile

# ─────────────────────────  Streamlit page  ─────────────────────────
st.set_page_config("Portfolio Viewer", layout="wide")
st.title("📈 Portfolio Viewer — Long / Short with PnL")

# ─────────────────────────  Excel helper  ───────────────────────────
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
    shorts.columns = ["Instrument", "ICB Industry", "Weight"]  # nicer header
    return longs, shorts

# ─────────────────────────  Refinitiv session  ──────────────────────
if 'lseg_session' not in st.session_state or not st.session_state.lseg_session.is_opened:
    try:
        st.write("Attempting to open LSEG Data Platform session...")
        st.session_state.lseg_session = ld.open_session("platform.rdp")
        st.session_state.lseg_session.open()
        st.success("LSEG Data Platform session opened successfully!")
    except Exception as e:
        st.error(f"❌ Failed to open LSEG Data Platform session. "
                 f"Please ensure 'lseg-data.config.json' is in your repo root "
                 f"and 'LSEG_DATA_CONFIG_PATH' is set in Streamlit secrets. Error: {e}")
        st.stop() # Stop the app if session fails to open
else:
    st.info("LSEG Data Platform session already open.")

session = st.session_state.lseg_session # Use the stored session for subsequent API calls

# ─────────────────────────  Price fetchers  ─────────────────────────
@st.cache_data(ttl=10 * 60)                     # 10-min cache
def fetch_last_price(rics):
    """
    Return {RIC: last traded price} using a single ld.get_data() call.
    """
    resp = ld.get_data(
        universe=rics,
        fields=["TRDPRC_1"],          # last trade price
    )
    return resp.set_index("RIC")["TRDPRC_1"].dropna().to_dict()

@st.cache_data(ttl=24 * 60 * 60)               # one day cache
def fetch_exec_close(rics, exec_date):
    """
    Return {RIC: CLOSE price on exec_date}:
    SDate & EDate restrict the historical query to that single day.
    """
    resp = ld.get_data(
        universe=rics,
        fields=["CLOSE"],
        parameters={"SDate": exec_date, "EDate": exec_date},
    )
    return resp.set_index("RIC")["CLOSE"].dropna().to_dict()

# ─────────────────────────  UI widgets  ─────────────────────────────
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
exec_day_str = exec_day.strftime("%Y-%m-%d")

# ─────────────────────────  Main flow  ──────────────────────────────
if uploaded:
    try:
        longs_df, shorts_df = split_excel(uploaded)
        st.success(f"Excel OK — fetching prices for {exec_day_str}…")

        all_rics = longs_df["Instrument"].tolist() + shorts_df["Instrument"].tolist()
        last_px   = fetch_last_price(all_rics)
        close_px  = fetch_exec_close(all_rics, exec_day_str)

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

    except Exception as e:
        st.error(f"❌ {e}")

else:
    st.info("Upload an Excel file, then pick the execution date.")

