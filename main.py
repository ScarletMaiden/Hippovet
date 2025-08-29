# main.py
import pandas as pd
import streamlit as st
import json

from add_form import render_add_form
from edit_form import render_edit_form
from delete_form import render_delete_form
from powiat_utils import fill_powiat_auto

# Google Sheets
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# === KONFIG ===
SHEET_ID = "1GAP0mBSS5TRrGTpPQW52rfG6zKdNHiEnE9kdsmC-Zkc"
WORKSHEET_GID = 2113617863  # <- zakładka z linku gid=...

COLS = [
    "nr zamówienia", "nr badania", "imię konia",
    "Anoplocephala perfoliata", "Oxyuris equi",
    "Parascaris equorum", "Strongyloides spp",
    "Kod-pocztowy", "Powiat", "Miasto",
]
BINARY_COLS = [
    "Anoplocephala perfoliata", "Oxyuris equi",
    "Parascaris equorum", "Strongyloides spp",
]
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# ============ Google Sheets: połączenie ============
@st.cache_resource(show_spinner=False)
def _get_ws():
    try:
        raw = st.secrets["gcp_service_account_json"]
    except KeyError:
        st.error("❌ Brak klucza 'gcp_service_account_json' w Secrets.")
        st.stop()

    try:
        info = json.loads(raw)
    except Exception as e:
        st.error(f"❌ Nie mogę zinterpretować JSON z kluczem serwisowym: {type(e).__name__}: {e}")
        st.stop()

    try:
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.get_worksheet_by_id(WORKSHEET_GID)
        if ws is None:
            st.error(f"❌ Nie znaleziono zakładki o GID={WORKSHEET_GID}.")
            st.stop()
        return ws
    except Exception as e:
        st.error(f"❌ Nie udało się połączyć z Google Sheets. Szczegóły: {type(e).__name__}: {e}")
        st.stop()


# ============ Dane: odczyt / zapis ============
@st.cache_data(show_spinner=False)
def load_df() -> pd.DataFrame:
    ws = _get_ws()
    df0 = get_as_dataframe(
        ws,
        evaluate_formulas=True,
        header=1,  # pierwszy wiersz = nagłówki
        dtype=str,
        nrows=None
    )

    if df0 is None:
        df0 = pd.DataFrame()

    df0.columns = [str(c).strip() for c in df0.columns if c is not None]
    df0 = df0.dropna(how="all")

    if len(df0.columns) > 0:
        df0 = df0.loc[:, ~df0.columns.duplicated()]

    # dołóż brakujące kolumny
    for c in COLS:
        if c not in df0.columns:
            df0[c] = pd.NA

    # rzutuj binaria na 0/1
    for c in BINARY_COLS:
        df0[c] = pd.to_numeric(df0[c], errors="coerce").fillna(0).astype(int)

    return df0.loc[:, COLS]


def save_df(df: pd.DataFrame) -> None:
    ws = _get_ws()
    out = df.copy()

    for c in COLS:
        if c not in out.columns:
            out[c] = pd.NA
    out = out.loc[:, COLS]

    set_with_dataframe(
        ws,
        out,
        include_index=False,
        include_column_header=True,
        resize=True
    )
    st.cache_data.clear()  # odśwież cache


# ============ UI ============
st.set_page_config(page_title="Zamówienia", page_icon="📦", layout="wide")
st.title("📦 Podgląd i dodawanie zamówień")

df = load_df()

# Sidebar: wyszukiwanie + usuwanie
with st.sidebar:
    st.header("🔎 Wyszukiwanie")
    q = st.text_input("Numer zamówienia (część lub całość)", placeholder="np. 12345")
    szukaj = st.button("Szukaj", use_container_width=True)

    st.divider()
    st.header("🗑️ Usuń rekord")
    df, deleted = render_delete_form(df, save_df)

# Auto-uzupełnianie powiatu
df, filled, used_col = fill_powiat_auto(df, powiat_col="Powiat", kod_candidates=("Kod-pocztowy", "Kod-pocztowy "))
if filled:
    save_df(df)
    st.info(f"ℹ️ Uzupełniono 'Powiat' w {filled} wierszach (źródło: {used_col}).")

# Widok tabeli
st.subheader("📑 Wszystkie dane")
for col in COLS:
    if col not in df.columns:
        df[col] = pd.NA
df = df.loc[:, COLS]

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

# Formularze (dodawanie/edycja)
df, added = render_add_form(df, save_df, COLS)
df, edited = render_edit_form(df, save_df, COLS)

# Odśwież po modyfikacjach
if any([added, edited, deleted]):
    st.rerun()
