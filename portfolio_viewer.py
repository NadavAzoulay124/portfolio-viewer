# import streamlit as st
# import pandas as pd
# import lseg.data as ld
# from datetime import date
# import json, os, pathlib, tempfile
# import logging

# # ─────────────────────────  Streamlit page  ─────────────────────────
# st.set_page_config("Portfolio Viewer", layout="wide")
# st.title("📈 Portfolio Viewer — Long / Short with PnL")
# # logging.basicConfig(
# #     level=logging.DEBUG,                   # root logger goes to stdout
# #     format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
# # )

# # ─────────────────────────  Excel helper  ───────────────────────────
# REQ_LONG  = ["Instrument", "ICB Industry", "Weight"]
# REQ_SHORT = ["Instrument.1", "ICB Industry.1", "Weight.1"]

# def split_excel(file):
#     df = pd.read_excel(file)

#     miss_long  = set(REQ_LONG)  - set(df.columns)
#     miss_short = set(REQ_SHORT) - set(df.columns)
#     if miss_long or miss_short:
#         raise ValueError(
#             f"Missing columns — long: {miss_long or 'OK'}, "
#             f"short: {miss_short or 'OK'}"
#         )

#     longs  = df[REQ_LONG].copy()
#     shorts = df[REQ_SHORT].copy()
#     shorts.columns = ["Instrument", "ICB Industry", "Weight"]  # nicer header
#     return longs, shorts

# # ─────────────────────────  Refinitiv session  ──────────────────────
# session = ld.open_session(config_name="/mount/src/portfolio-viewer/lseg-data.config.json", name="platform.rdp")
# session.open()

# # ─────────────────────────  Price fetchers  ─────────────────────────
# @st.cache_data(ttl=10 * 60)                     # 10-min cache
# def fetch_last_price(rics):
#     """
#     Return {RIC: last traded price} using a single ld.get_data() call.
#     """
#     st.success(rics)
#     logging.getLogger("refinitiv.data").setLevel(logging.DEBUG)
#     df = ld.get_data(
#         universe =rics,
#         fields = [
#             'CF_LAST'
#         ],
#     )
    
#     st.success(df)
#     return df.set_index("RIC")["TRDPRC_1"].dropna().to_dict()

# @st.cache_data(ttl=24 * 60 * 60)               # one day cache
# def fetch_exec_close(rics, exec_date):
#     """
#     Return {RIC: CLOSE price on exec_date}:
#     SDate & EDate restrict the historical query to that single day.
#     """
#     resp = ld.get_data(
#         universe=rics,
#         fields=["CLOSE"],
#         parameters={"SDate": exec_date, "EDate": exec_date},
#     )
#     return resp.set_index("RIC")["CLOSE"].dropna().to_dict()

# # ─────────────────────────  UI widgets  ─────────────────────────────
# uploaded = st.file_uploader(
#     "Upload portfolio Excel",
#     type=["xlsx", "xls"],
#     help="Longs: Instrument / ICB Industry / Weight • "
#          "Shorts: Instrument.1 / ICB Industry.1 / Weight.1",
# )

# exec_day = st.date_input(
#     "Execution date (closing price reference)",
#     value=date.today(),
# )
# exec_day_str = exec_day.strftime("%Y-%m-%d")

# # ─────────────────────────  Main flow  ──────────────────────────────
# if uploaded:
#     try:
#         longs_df, shorts_df = split_excel(uploaded)
#         st.success(f"Excel OK — fetching prices for {exec_day_str}…")

#         all_rics = longs_df["Instrument"].tolist() + shorts_df["Instrument"].tolist()

#         last_px   = fetch_last_price(all_rics)
#         close_px  = fetch_exec_close(all_rics, exec_day_str)


#         def enrich(df):
#             df["LastPrice"] = df["Instrument"].map(last_px)
#             df["ExecClose"] = df["Instrument"].map(close_px)
#             df["PnL %"] = ((df["LastPrice"] - df["ExecClose"])
#                            / df["ExecClose"] * 100).round(2)
#             return df

#         longs_df  = enrich(longs_df)
#         shorts_df = enrich(shorts_df)

#         tab_long, tab_short = st.tabs(["Long positions", "Short positions"])
#         with tab_long:
#             st.dataframe(longs_df, use_container_width=True)
#         with tab_short:
#             st.dataframe(shorts_df, use_container_width=True)

#     except Exception as e:
#         st.error(f"❌ {e}")

# else:
#     st.info("Upload an Excel file, then pick the execution date.")



# live_price.py  –  Streamlit demo pulling a live quote via Refinitiv RDP
import streamlit as st
import pandas as pd
import refinitiv.data as rd
from refinitiv.data.content import pricing
from datetime import datetime

# ───────────────────────────── page config ──────────────────────────────
st.set_page_config(page_title="OBEX Live Quote", page_icon="📈", layout="centered")
st.title("🟢 OBEX Analyzer – Live Quote")

# ───────────────────────────── credentials ──────────────────────────────
# Put these three keys in Streamlit Cloud ➜ Settings ➜ Secrets
#   RDP_APP_KEY = "APPKEY-32HEX"
#   RDP_USER    = "RDP_LOGIN"
#   RDP_PASS    = "RDP_PASSWORD"

app_key  = st.secrets["APP_KEY"]
username = st.secrets["USER_NAME"]
password = st.secrets["PASSWORD"]

# ───────────────────────────── open session once ────────────────────────
if "rd_session" not in st.session_state:
    sess = (
        rd.session.platform.Definition(
            app_key = app_key,
            grant   = rd.session.platform.GrantPassword(
                        username=username,
                        password=password,
                      )
        )
        .get_session()
    )
    sess.open()
    rd.session.set_default(sess)           # let SDK calls use it implicitly
    st.session_state["rd_session"] = sess

# ───────────────────────────── user input ───────────────────────────────
ric = st.text_input("Enter a RIC (e.g. AAPL.O)", value="AAPL.O")

# ───────────────────────────── autorefresh every 2 s ────────────────────
# triggers a script rerun; cached data older than TTL refreshes
from streamlit_extras.st_autorefresh import st_autorefresh
st_autorefresh(interval=2000, key="quote_refresh")   # 2 000 ms

# ───────────────────────────── cached price pull ────────────────────────
@st.cache_data(ttl=1)                               # max 1 REST call / s
def fetch_last_price(ric_code: str) -> pd.DataFrame:
    snap = (
        pricing.snap.Definition(
            universe = ric_code,
            fields   = ["TRDPRC_1", "TRDVWAP_1", "ACVOL"]
        )
        .get_data()
        .data.df
    )
    snap.reset_index(inplace=True)
    snap["Time"] = datetime.utcnow()
    return snap

# ───────────────────────────── display ──────────────────────────────────
try:
    df = fetch_last_price(ric)
    last_px   = float(df.loc[0, "TRDPRC_1"])
    vwap      = float(df.loc[0, "TRDVWAP_1"])
    volume    = int(df.loc[0, "ACVOL"])
    pct_delta = (last_px - vwap) / vwap * 100 if vwap else 0.0

    st.metric(
        label=f"{ric} – last trade",
        value=f"${last_px:,.2f}",
        delta=f"{pct_delta:+.2f} %",
        delta_color="inverse" if pct_delta < 0 else "normal",
    )
    st.caption(f"VWAP {vwap:,.2f} • Vol {volume:,} • UTC {df.loc[0,'Time'].strftime('%H:%M:%S')}")
except Exception as err:
    st.error(f"Could not fetch data for “{ric}”.  {err}")
