import os
import pandas as pd
import streamlit as st

from add_form import render_add_form
from edit_form import render_edit_form
from delete_form import render_delete_form
from powiat_utils import fill_powiat_auto
from simple_map import render_simple_map

BASE_DIR = os.path.dirname(__file__)
FILE_PATH = os.path.join(BASE_DIR, "praca.xlsx")

COLS = [
    "nr zamówienia", "nr badania", "imię konia",
    "Anoplocephala perfoliata", "Oxyuris equi",
    "Parascaris equorum", "Strongyloides spp",
    "Kod-pocztowy", "Powiat", "Miasto",
]

def _init_excel_if_missing(path: str):
    if not os.path.exists(path):
        df0 = pd.DataFrame({c: [] for c in COLS})
        df0.to_excel(path, index=False)

@st.cache_data(show_spinner=False)
def load_df(path: str, _file_mtime: float | None):
    try:
        df0 = pd.read_excel(path, dtype=str)
    except FileNotFoundError:
        df0 = pd.DataFrame()

    if len(df0.columns) > 0:
        df0.columns = [str(c).strip() for c in df0.columns]
        df0 = df0.loc[:, ~df0.columns.duplicated()]
        df0 = df0.loc[:, ~df0.columns.str.contains("^Unnamed", case=False)]

    for c in COLS:
        if c not in df0.columns:
            df0[c] = pd.NA

    for c in ["Anoplocephala perfoliata", "Oxyuris equi", "Parascaris equorum", "Strongyloides spp"]:
        if c in df0.columns:
            df0[c] = pd.to_numeric(df0[c], errors="coerce").fillna(0).astype(int)

    return df0


def save_df(df: pd.DataFrame, path: str):
    df_out = df.copy()
    for c in COLS:
        if c not in df_out.columns:
            df_out[c] = pd.NA
    df_out.to_excel(path, index=False)
    st.cache_data.clear()

st.set_page_config(page_title="Zamówienia", page_icon="📦", layout="wide")
st.title("📦 Podgląd i dodawanie zamówień")

_init_excel_if_missing(FILE_PATH)

try:
    _MTIME = os.path.getmtime(FILE_PATH)
except FileNotFoundError:
    _MTIME = None

df = load_df(FILE_PATH, _MTIME)

with st.sidebar:
    st.header("🔎 Wyszukiwanie")
    q = st.text_input("Numer zamówienia (część lub całość)", placeholder="np. 12345")
    szukaj = st.button("Szukaj", use_container_width=True)

    st.divider()
    st.header("🗑️ Usuń rekord")
    df, deleted = render_delete_form(df, FILE_PATH)

df, filled, used_col = fill_powiat_auto(df, powiat_col="Powiat", kod_candidates=("Kod-pocztowy", "Kod-pocztowy "))
if filled:
    save_df(df, FILE_PATH)
    st.info(f"Uzupełniono 'Powiat' w {filled} wierszach (źródło: {used_col}).")

st.subheader("📑 Wszystkie dane")
desired_order = [
    "nr zamówienia", "nr badania", "imię konia",
    "Anoplocephala perfoliata", "Oxyuris equi",
    "Parascaris equorum", "Strongyloides spp",
    "Kod-pocztowy", "Powiat", "Miasto",
]
for col in desired_order:
    if col not in df.columns:
        df[col] = pd.NA

df = df.loc[:, desired_order]

if q and szukaj:
    mask = df["nr zamówienia"].astype(str).str.contains(q.strip(), case=False, na=False)
    res = df.loc[mask].copy()
    if len(res) == 0:
        st.info("Brak wyników.")
    else:
        st.success(f"Znaleziono {len(res)} rekord(y).")
        st.dataframe(res, use_container_width=True, height=420)
else:
    st.dataframe(df, use_container_width=True, height=420)

render_simple_map(df)

df, added = render_add_form(df, FILE_PATH, COLS)
df, edited = render_edit_form(df, FILE_PATH, COLS)

if any([added, edited, deleted]):
    st.rerun()

