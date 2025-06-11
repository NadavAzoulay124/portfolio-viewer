import streamlit as st
import pandas as pd
import lseg.data as ld
from datetime import date
import json, os, pathlib, tempfile

# ─────────────────────────  Streamlit page  ─────────────────────────
st.set_page_config("Portfolio Viewer", layout="wide")
st.title("📈 Portfolio Viewer — Long / Short with PnL")



