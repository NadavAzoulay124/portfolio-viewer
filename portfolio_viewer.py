import lseg.data as ld
import time
import streamlit as st
import pandas as pd

# ---------- CONFIG ----------

st.set_page_config("Portfolio Viewer", layout="wide")

XL_FILE_PATH = 'Selections_For_June2025_100x100.xlsx'

# -------------HELPERS ---------------


def format_excel(file):
    REQUIRED_LONG = ["Instrument", "ICB Industry", "Weight"]
    REQUIRED_SHORT = ["Instrument.1", "ICB Industry.1", "Weight.1"]
    df = pd.read_excel(file)

     # Validate columns
    missing_long  = set(REQUIRED_LONG)  - set(df.columns)
    missing_short = set(REQUIRED_SHORT) - set(df.columns)
    if missing_long or missing_short:
        raise ValueError(
            f"Missing columns – long: {missing_long or 'OK'}, "
            f"short: {missing_short or 'OK'}"
        )
    
    longs  = df[REQUIRED_LONG].copy()
    shorts = df[REQUIRED_SHORT].copy()
    shorts.columns = ["Instrument", "ICB Industry", "Weight"]

    return longs, shorts



# ---------- UI ----------
st.title("📈 Portfolio Viewer — Long / Short Split")

uploaded = st.file_uploader(
    "Upload portfolio Excel (must contain the six columns shown below)",
    type=["xlsx", "xls"],
    help="Longs: Instrument, ICB Industry, Weight • Shorts: Instrument.1, ICB Industry.1, Weight.1",
)

if uploaded:
    try:
        longs_df, shorts_df = format_excel(uploaded)

        st.success("File loaded successfully!")

        tab1, tab2 = st.tabs(["Long positions", "Short positions"])

        with tab1:
            st.subheader("Longs")
            st.dataframe(longs_df, use_container_width=True)

        with tab2:
            st.subheader("Shorts")
            st.dataframe(shorts_df, use_container_width=True)

    except Exception as e:
        st.error(f"❌ {e}")

else:
    st.info("Drag & drop an Excel file to begin.")