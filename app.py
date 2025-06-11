import streamlit as st
import pandas as pd

st.set_page_config(page_title="Portfolio Demo", layout="wide")
st.title("📈 Portfolio Viewer – Proof of Concept")

uploaded = st.file_uploader(
    "Upload your Excel (.xlsx / .xls) file",
    type=["xlsx", "xls"],
    help="Template needs columns: Ticker, Shares, BuyPrice",
)

if uploaded:
    try:
        df = pd.read_excel(uploaded)
        st.subheader("Raw data")
        st.dataframe(df, use_container_width=True)

        required = {"Ticker", "Shares", "BuyPrice"}
        if required.issubset(df.columns):
            df["MarketValue"] = df["Shares"] * df["BuyPrice"]
            st.subheader("Quick check – cost × shares")
            st.dataframe(df[["Ticker", "MarketValue"]], use_container_width=True)
        else:
            st.warning(f"Missing columns: {required - set(df.columns)}")
    except Exception as e:
        st.error(f"Couldn’t read Excel: {e}")
else:
    st.info("⬆️ Upload a sample file to see it in the table")