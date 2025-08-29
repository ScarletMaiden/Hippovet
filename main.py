# main.py
import json
import pandas as pd
import streamlit as st

from add_form import render_add_form
from edit_form import render_edit_form
from delete_form import render_delete_form
from powiat_utils import fill_powiat_auto

import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe

# === KONFIG ===
SHEET_ID = "1GAP0mBSS5TRrGTpPQW52rfG6zKdNHiEnE9kdsmC-Zkc"
WORKSHEET_GID = 2113617863  # gid=... z linku do zakładki

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


# === Google Sheets: połączenie ===
@st.cache_resource(show_spinner=False)
def _get_ws():
    try:
        raw = st.secrets["gcp_service_account_json"]
    except KeyError:
        st.error("Brak klucza 'gcp_service_account_json' w Settings → Secrets.")
        st.stop()

    try:
        info = json.loads(raw)
    except Exception as e:
        st.error(f"Nie mogę zinterpretować JSON z kluczem serwisowym: {type(e).__name__}: {e}")
        st.stop()

    try:
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.get_worksheet_by_id(WORKSHEET_GID)
        if ws is None:
            st.error(f"Nie znaleziono zakładki o GID={WORKSHEET_GID}.")
            st.stop()
        return ws
    except Exception as e:
        st.error(f"Nie udało się połączyć z Google Sheets. Szczegóły: {type(e).__name__}: {e}")
        st.stop()


# === ODCZYT (odporny na bałagan w arkuszu) ===
@st.cache_data(show_spinner=False)
def load_df() -> pd.DataFrame:
    ws = _get_ws()

    values = ws.get_all_values() or []
    if not values:
        return pd.DataFrame(columns=COLS)

    # usuń puste wiersze z końca
    while values and all((c.strip() == "" for c in values[-1])):
        values.pop()

    # auto-detekcja wiersza nagłówków (>=3 znane kolumny)
    wanted_lc = [c.lower() for c in COLS]
    header_row_idx = 0
    for i, row in enumerate(values[:20]):
        row_lc = [c.strip().lower() for c in row]
        score = sum(1 for c in row_lc if c in wanted_lc)
        if score >= 3:
            header_row_idx = i
            break

    headers = [h.strip() for h in values[header_row_idx]]
    data_rows = values[header_row_idx + 1:]

    width = len(headers)
    data_rows = [r[:width] + [""] * max(0, width - len(r)) for r in data_rows]
    df0 = pd.DataFrame(data_rows, columns=headers)

    # aliasy nazw -> nazwy kanoniczne
    aliases = {
        "nr zamowienia": "nr zamówienia",
        "nr badania": "nr badania",
        "imie konia": "imię konia",
        "anoplocephala perfoliata": "Anoplocephala perfoliata",
        "oxyuris equi": "Oxyuris equi",
        "parascaris equorum": "Parascaris equorum",
        "strongyloides spp": "Strongyloides spp",
        "kod-pocztowy": "Kod-pocztowy",
        "kod pocztowy": "Kod-pocztowy",
        "powiat": "Powiat",
        "miasto": "Miasto",
    }
    colmap = {}
    for c in df0.columns:
        key = str(c).strip().lower()
        colmap[c] = aliases.get(key, str(c).strip())
    df0 = df0.rename(columns=colmap)

    # normalizacja pustych wartości / "none" / "null"
    df0 = df0.replace(r"^\s*$", pd.NA, regex=True)
    df0 = df0.mask(df0.astype(str).str.lower().isin(["none", "null"]))

    # usuń wiersze kompletnie puste
    df0 = df0.dropna(how="all")

    # dołóż brakujące kolumny i ustaw kolejność
    for c in COLS:
        if c not in df0.columns:
            df0[c] = pd.NA
    df0 = df0.loc[:, COLS]

    # binaria na 0/1
    for c in BINARY_COLS:
        df0[c] = pd.to_numeric(df0[c], errors="coerce").fillna(0).astype(int)

    return df0


# === ZAPIS ===
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
    st.cache_data.clear()


# === UI ===
st.set_page_config(page_title="Zamówienia", page_icon="📦", layout="wide")
st.title("📦 Podgląd i dodawanie zamówień")

df = load_df()

with st.sidebar:
    st.header("🔎 Wyszukiwanie")
    q = st.text_input("Numer zamówienia (część lub całość)", placeholder="np. 12345")
    szukaj = st.button("Szukaj", use_container_width=True)

    st.divider()
    st.header("🗑️ Usuń rekord")
    df, deleted = render_delete_form(df, save_df)

# auto-uzupełnianie powiatu
df, filled, used_col = fill_powiat_auto(df, powiat_col="Powiat", kod_candidates=("Kod-pocztowy", "Kod-pocztowy "))
if filled:
    save_df(df)
    st.info(f"Uzupełniono 'Powiat' w {filled} wierszach (źródło: {used_col}).")

# tabela
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

# formularze
df, added = render_add_form(df, save_df, COLS)
df, edited = render_edit_form(df, save_df, COLS)

if any([added, edited, deleted]):
    st.rerun()
