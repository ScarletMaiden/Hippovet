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

SHEET_ID = "1GAP0mBSS5TRrGTpPQW52rfG6zKdNHiEnE9kdsmC-Zkc"
WORKSHEET_GID = 2113617863 

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

st.set_page_config(page_title="Zamówienia", page_icon="📦", layout="wide")

try:
    from simple_map import render_simple_map
except Exception:
    render_simple_map = None


@st.cache_resource(show_spinner=False)
def _get_ws():
    try:
        raw = st.secrets["gcp_service_account_json"]
        info = json.loads(raw)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.get_worksheet_by_id(WORKSHEET_GID)
        if ws is None:
            st.error(f"❌ Nie znaleziono zakładki o GID={WORKSHEET_GID}.")
            st.stop()
        return ws
    except KeyError:
        st.error("❌ Brak klucza 'gcp_service_account_json' w Settings → Secrets.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Nie udało się połączyć z Google Sheets. Szczegóły: {type(e).__name__}: {e}")
        st.stop()


@st.cache_data(show_spinner=False)
def load_df() -> pd.DataFrame:
    ws = _get_ws()

    values = ws.get_all_values() or []
    if not values:
        return pd.DataFrame(columns=COLS)

    while values and all((c.strip() == "" for c in values[-1])):
        values.pop()

    headers = [h.strip() for h in values[0]]
    data_rows = values[1:]

    width = len(headers)
    data_rows = [r[:width] + [""] * max(0, width - len(r)) for r in data_rows]
    df0 = pd.DataFrame(data_rows, columns=headers)

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
    df0 = df0.rename(columns={c: aliases.get(str(c).strip().lower(), str(c).strip()) for c in df0.columns})

    df0 = df0.replace(r"^\s*$", pd.NA, regex=True)
    lower = df0.astype(str).apply(lambda s: s.str.strip().str.lower())
    df0 = df0.mask(lower.isin(["none", "null"]))
    df0 = df0.dropna(how="all")

    for c in COLS:
        if c not in df0.columns:
            df0[c] = pd.NA
    df0 = df0.loc[:, COLS]

    for c in BINARY_COLS:
        df0[c] = pd.to_numeric(df0[c], errors="coerce").fillna(0).astype(int)

    return df0


# ===== ZAPIS =====
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


st.title("📦 Podgląd i dodawanie zamówień")

with st.sidebar:
    st.header("🔎 Wyszukiwanie")

    search_field = st.radio(
        "Szukaj wg:",
        ["nr zamówienia", "nr badania"],
        horizontal=True,
        key="search_field",
    )

    placeholder = "np. 12345" if search_field == "nr zamówienia" else "np. 733"
    q = st.text_input(f"{search_field} (część lub całość)", placeholder=placeholder, key="search_q")

    szukaj = st.button("Szukaj", use_container_width=True)

    st.divider()
    st.header("🗑️ Usuń rekord")

# wczytaj dane
df = load_df()

with st.sidebar:
    df, deleted = render_delete_form(df, save_df)

df, filled, used_col = fill_powiat_auto(df, powiat_col="Powiat", kod_candidates=("Kod-pocztowy", "Kod-pocztowy "))
if filled:
    save_df(df)
    st.info(f"ℹ️ Uzupełniono 'Powiat' w {filled} wierszach (źródło: {used_col}).")

st.subheader("📑 Wszystkie dane")
for col in COLS:
    if col not in df.columns:
        df[col] = pd.NA
df = df.loc[:, COLS]

if q and szukaj:
    col = search_field  
    mask = df[col].astype(str).str.contains(q.strip(), case=False, na=False)
    res = df.loc[mask].copy()
    if len(res) == 0:
        st.info("Brak wyników.")
    else:
        st.success(f"Znaleziono {len(res)} rekord(y).")
        st.dataframe(res, use_container_width=True, height=420)
else:
    st.dataframe(df, use_container_width=True, height=420)


st.subheader("")
if render_simple_map is None:
    st.info("Mapa niedostępna (brak modułu simple_map lub zależności).")
else:
    try:
        render_simple_map(df)
    except Exception as e:
        st.error(f"Nie udało się narysować mapy: {type(e).__name__}: {e}")

df, added = render_add_form(df, save_df, COLS)
df, edited = render_edit_form(df, save_df, COLS)

if any([added, edited, deleted]):
    st.rerun()
