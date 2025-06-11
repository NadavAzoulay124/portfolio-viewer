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
session = ld.open_session(config_name="/mount/src/portfolio-viewer/lseg-data.config.json", name="platform.rdp")
session.open()

# ─────────────────────────  Price fetchers  ─────────────────────────
@st.cache_data(ttl=10 * 60)                     # 10-min cache
def fetch_last_price(rics):
    """
    Return {RIC: last traded price} using a single ld.get_data() call.
    """
    st.success(rics)
    resp = ld.get_data(
        universe = ['WGS.OQ', 'IBTA.N', 'CRDO.OQ', 'SEZL.OQ', 'APLD.OQ', 'RGTI.OQ', 'AKRO.OQ', 'APP.OQ', 'SMR.N', 'WULF.OQ', 'CODI.N', 'SOUN.OQ', 'CIFR.OQ', 'BTDR.OQ', 'NEO.OQ', 'TEM.OQ', 'FL.N', 'NFE.OQ', 'FLYW.OQ', 'SMCI.OQ', 'GOGO.OQ', 'SRPT.OQ', 'ASTS.OQ', 'VICR.OQ', 'RXRX.OQ', 'AGL.N', 'CABO.N', 'ETNB.OQ', 'MARA.OQ', 'DV.N', 'PI.OQ', 'BE.N', 'CVNA.N', 'ACHR.N', 'LITE.OQ', 'BILL.N', 'VSCO.N', 'MOD.N', 'SAIA.OQ', 'VNET.OQ', 'ELF.N', 'COHR.N', 'SVV.N', 'SYM.OQ', 'TPC.N', 'PCT.OQ', 'TNDM.OQ', 'VSTS.N', 'MCHP.OQ', 'WWW.N', 'AAP.N', 'ALGM.OQ', 'JBLU.OQ', 'ACMR.OQ', 'VFC.N', 'TSLA.OQ', 'FMC.N', 'PLUG.OQ', 'RIOT.OQ', 'COIN.OQ', 'FN.N', 'MGNI.OQ', 'GO.OQ', 'RKLB.OQ', 'ECG.N', 'DLO.OQ', 'HOOD.OQ', 'NEOG.OQ', 'ASAN.N', 'U.N', 'ENPH.OQ', 'TROX.N', 'BROS.N', 'ENVX.OQ', 'ARHS.OQ', 'MDB.OQ', 'MSTR.OQ', 'DECK.N', 'CDE.N', 'WST.N', 'CRL.N', 'ADPT.OQ', 'ARIS.N', 'CENX.OQ', 'VRT.N', 'STRL.OQ', 'ARDX.OQ', 'OCUL.OQ', 'TLN.OQ', 'QDEL.OQ', 'SG.N', 'WRBY.N', 'VST.N', 'MP.N', 'MNDY.OQ', 'MRVL.OQ', 'CLF.N', 'CAVA.N', 'CIVI.N', 'GLBE.OQ', 'J.N', 'CSX.OQ', 'SSNC.OQ', 'WM.N', 'CHTR.OQ', 'BG.N', 'MDT.N', 'FDP.N', 'CHD.N', 'MPLX.N', 'OGE.N', 'GD.N', 'MDU.N', 'PRMB.N', 'RSG.N', 'SLGN.N', 'SJM.N', 'KMI.N', 'ACI.N', 'VLTO.N', 'SWX.N', 'STZ.N', 'EVRI.N', 'KHC.OQ', 'QSR.N', 'POST.N', 'WLKP.N', 'DGX.N', 'ACM.N', 'FDS.N', 'COR.N', 'INGR.N', 'ET.N', 'DOX.OQ', 'CCK.N', 'AJG.N', 'ROP.OQ', 'GWW.N', 'NWE.OQ', 'BATRA.OQ', 'VRSK.OQ', 'TIGO.OQ', 'NOMD.N', 'AMED.OQ', 'STE.N', 'CAG.N', 'KDP.OQ', 'LH.N', 'AGS.N', 'FCFS.OQ', 'ADP.OQ', 'ATO.N', 'KR.N', 'LNT.OQ', 'T.N', 'AVA.N', 'BRO.N', 'OGS.N', 'MMC.N', 'ORA.N', 'FE.N', 'ICE.N', 'NFG.N', 'BMY.N', 'NWN.N', 'TSN.N', 'JNPR.N', 'PEG.N', 'ED.N', 'PARA.OQ', 'BIP.N', 'RPRX.OQ', 'BKH.N', 'VZ.N', 'ETR.N', 'K.N', 'D.N', 'WTW.OQ', 'SYY.N', 'LHX.N', 'EVRG.OQ', 'BBSI.OQ', 'PFE.N', 'NI.N', 'AON.N', 'AMGN.OQ', 'AEE.N', 'SR.N', 'PPL.N', 'SO.N', 'WEC.N', 'XEL.OQ', 'EPD.N', 'AEP.OQ', 'CMS.N', 'PCG.N', 'DTE.N', 'CNP.N', 'DUK.N', 'FYBR.OQ'],
        fields = [
            'CF_LAST',
            'TR.ClosePrice'
        ],
    )
    
    st.success(resp)
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

