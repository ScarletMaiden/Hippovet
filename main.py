import pandas as pd
import streamlit as st

from add_form import render_add_form
from edit_form import render_edit_form
from delete_form import render_delete_form
from powiat_utils import fill_powiat_auto
from simple_map import render_simple_map  # zostaw, jeśli masz ten moduł

# ==== NOWE: Google Sheets ====
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# ==== KONFIGURACJA BACKENDU DANYCH ====
SHEET_ID = "1GAP0mBSS5TRrGTpPQW52rfG6zKdNHiEnE9kdsmC-Zkc"
WORKSHEET_NAME = "praca"

# Kolumny wymagane przez aplikację — nazwy bez dodatkowych spacji
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

@st.cache_resource(show_spinner=False)
def _get_ws():
    """Zwraca uchwyt do worksheetu Google Sheets."""
    # Sekrety MUSZĄ zawierać cały JSON konta serwisowego pod kluczem gcp_service_account
    info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    return sh.worksheet(WORKSHEET_NAME)

@st.cache_data(show_spinner=False)
def load_df() -> pd.DataFrame:
    """Czyta cały arkusz do DataFrame i porządkuje kolumny/typy."""
    ws = _get_ws()
    df0 = get_as_dataframe(
        ws,
        evaluate_formulas=True,
        header=1,                 # 1. wiersz to nagłówki
        dtype=str,                # czytamy jako tekst, potem rzutujemy binaria
        nrows=None
    )

    # Usuwamy puste wiersze na końcu/środku
    if df0 is None:
        df0 = pd.DataFrame()
    else:
        # gspread_dataframe potrafi dodać kolumnę None, czyśćmy nagłówki
        df0.columns = [str(c).strip() for c in df0.columns if c is not None]
        # usuń wiersze kompletnie puste
        df0 = df0.dropna(how="all")

    # 1) Ujednolicenie nagłówków + usunięcie duplikatów
    if len(df0.columns) > 0:
        df0.columns = [str(c).strip() for c in df0.columns]
        df0 = df0.loc[:, ~df0.columns.duplicated()]

    # 2) Dołóż brakujące kolumny wymagane przez app
    for c in COLS:
        if c not in df0.columns:
            df0[c] = pd.NA

    # 3) Typy binarne jako 0/1 (spójnie dla UI)
    for c in BINARY_COLS:
        df0[c] = pd.to_numeric(df0[c], errors="coerce").fillna(0).astype(int)

    # Tylko wymagane kolumny, w oczekiwanej kolejności
    df0 = df0.loc[:, COLS]

    return df0

def save_df(df: pd.DataFrame) -> None:
    """Nadpisuje zawartość arkusza bieżącą ramką danych."""
    ws = _get_ws()
    # Upewnij się, że mamy wszystkie kolumny
    df_out = df.copy()
    for c in COLS:
        if c not in df_out.columns:
            df_out[c] = pd.NA
    df_out = df_out.loc[:, COLS]

    # Zapis z nagłówkiem i auto-dopasowaniem rozmiaru arkusza
    set_with_dataframe(
        ws,
        df_out,
        include_index=False,
        include_column_header=True,
        resize=True
    )
    # Po każdym zapisie unieważnij cache, żeby od razu było widać zmiany
    st.cache_data.clear()

# ====== UI ======
st.set_page_config(page_title="Zamówienia", page_icon="📦", layout="wide")
st.title("📦 Podgląd i dodawanie zamówień")

df = load_df()

# Lewy panel: wyszukiwarka + usuwanie
with st.sidebar:
    st.header("🔎 Wyszukiwanie")
    q = st.text_input("Numer zamówienia (część lub całość)", placeholder="np. 12345")
    szukaj = st.button("Szukaj", use_container_width=True)

    st.divider()
    st.header("🗑️ Usuń rekord")
    df, deleted = render_delete_form(df, save_df)  # ⬅ zmiana: przekazujemy funkcję zapisu

# Automatyczne uzupełnienie powiatu (na bazie kodu)
df, filled, used_col = fill_powiat_auto(df, powiat_col="Powiat", kod_candidates=("Kod-pocztowy", "Kod-pocztowy "))
if filled:
    save_df(df)
    st.info(f"Uzupełniono 'Powiat' w {filled} wierszach (źródło: {used_col}).")

# Widoki danych (tabela w stałej kolejności)
st.subheader("📑 Wszystkie dane")
desired_order = COLS[:]  # zachowaj tę samą kolejność
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

# Mapa (agregacja po powiecie)
render_simple_map(df)

# Formularze (dodawanie/edycja) — przekazujemy save_df zamiast ścieżki do Excela
df, added = render_add_form(df, save_df, COLS)
df, edited = render_edit_form(df, save_df, COLS)

# Odśwież po modyfikacjach
if any([added, edited, deleted]):
    st.rerun()
