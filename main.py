# main.py
import json
import os
import pandas as pd
import streamlit as st

# Importy z Twoich plików
from add_form import render_add_form
from edit_form import render_edit_form
from delete_form import render_delete_form
from powiat_utils import fill_powiat_auto

import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe

# ===== KONFIGURACJA =====
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

st.set_page_config(page_title="Hippovet Wyniki", page_icon="🐴", layout="wide")

# --- Próba importu mapy ---
try:
    from simple_map import render_simple_map
except Exception:
    render_simple_map = None


# ===== FUNKCJA POMOCNICZA: SZUKANIE LOGA =====
def get_logo_path():
    """Szuka pliku z logiem na serwerze"""
    # Tutaj wpisujemy możliwe nazwy Twojego pliku
    possible_names = [
        "612_124_hippovet_logo_poziom_1500px.png",  # <--- TWOJA NAZWA (Najważniejsza)
        "logo.png", "Logo.png", "LOGO.png",
        "logo.jpg", "Logo.jpg", "Hippovet.png"
    ]
    for name in possible_names:
        if os.path.exists(name):
            return name
    return None


# ===== FUNKCJA STOPKI (FOOTER) =====
def render_footer():
    st.markdown("""
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: white;
        color: #888;
        text-align: center;
        padding: 10px;
        font-size: 12px;
        border-top: 1px solid #eee;
        z-index: 1000;
    }
    footer {visibility: hidden;}
    </style>
    
    <div style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #888; font-size: 13px;">
        <p>
            &copy; 2025 <b>Hippovet</b>. Wszelkie prawa zastrzeżone.<br>
            Dbamy o zdrowie Twoich koni 🐴
        </p>
    </div>
    """, unsafe_allow_html=True)


# ===== POŁĄCZENIE Z GOOGLE SHEETS =====
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
        st.error(f"❌ Błąd połączenia z Google Sheets: {e}")
        st.stop()


# ===== ODCZYT DANYCH =====
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


# ===== ZAPIS DANYCH =====
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


# ==========================================
# ===== WIDOK PUBLICZNY (Dla Klienta) =====
# ==========================================
def render_public_view(df: pd.DataFrame):
    
    # === INTELIGENTNE LOGO ===
    logo_file = get_logo_path()
    
    if logo_file:
        # width=500 - dopasuj jeśli logo jest za duże/za małe
        st.image(logo_file, width=500) 
    else:
        st.title("🐴 Hippovet - Wyniki Badań")
        # Diagnostyka (pokaż tylko jeśli plik nie został wykryty)
        with st.expander("⚠️ Debugowanie loga"):
            st.warning(f"Nie znaleziono pliku. Szukałem m.in: '612_124_hippovet_logo_poziom_1500px.png'")
            st.write("Pliki na serwerze:", os.listdir("."))

    st.write("---")

    if "selected_map_view" not in st.session_state:
        st.session_state["selected_map_view"] = "konie"

    st.markdown("<h3 style='text-align: center;'>🗺️ Wybierz mapę występowania</h3>", unsafe_allow_html=True)
    st.write("") 

    # Przyciski
    c1, c2, c3 = st.columns(3)
    
    with c1:
        btn_type = "primary" if st.session_state["selected_map_view"] == "konie" else "secondary"
        if st.button("🐴 Pasożyty (Konie)", use_container_width=True, type=btn_type):
            st.session_state["selected_map_view"] = "konie"
            st.rerun()
            
    with c2:
        btn_type = "primary" if st.session_state["selected_map_view"] == "bydlo" else "secondary"
        if st.button("🐮 Bydło (Plan)", use_container_width=True, type=btn_type):
            st.session_state["selected_map_view"] = "bydlo"
            st.rerun()
            
    with c3:
        btn_type = "primary" if st.session_state["selected_map_view"] == "mix" else "secondary"
        if st.button("🔄 Mapa zbiorcza (Plan)", use_container_width=True, type=btn_type):
            st.session_state["selected_map_view"] = "mix"
            st.rerun()

    st.write("") 
    
    with st.container(border=True):
        if st.session_state["selected_map_view"] == "konie":
            st.markdown("#### 🐴 Występowanie pasożytów u koni")
            if render_simple_map:
                try:
                    render_simple_map(df)
                except Exception as e:
                    st.error(f"Błąd mapy: {e}")
            else:
                st.info("Moduł mapy niedostępny.")
                
        elif st.session_state["selected_map_view"] == "bydlo":
            st.markdown("#### 🐮 Mapa Bydła (W przygotowaniu)")
            st.info("Ta funkcjonalność zostanie dodana wkrótce.")
            st.image("https://placehold.co/800x300?text=Mapa+Dla+Bydla+wkrotce", use_container_width=True)
            
        elif st.session_state["selected_map_view"] == "mix":
            st.markdown("#### 🔄 Mapa zbiorcza / Nakładka")
            st.info("Tutaj będziesz mógł porównać dane z obu map.")
            st.image("https://placehold.co/800x300?text=Mapa+Zbiorcza", use_container_width=True)

    st.divider()

    st.subheader("🔎 Sprawdź wynik badania")
    
    public_cols = [c for c in COLS if c != "nr zamówienia"]
    df_public = df[public_cols].copy()

    q = st.text_input("Podaj numer badania:", placeholder="np. 26-02")
    
    if q:
        mask = df_public["nr badania"].astype(str).str.contains(q.strip(), case=False, na=False)
        res = df_public.loc[mask]
        
        if len(res) > 0:
            st.success(f"Znaleziono {len(res)} wynik(ów).")
            st.dataframe(res, use_container_width=True)
        else:
            st.warning("Nie znaleziono badania o takim numerze.")
    else:
        st.write("Ostatnie wyniki:")
        st.dataframe(df_public, use_container_width=True)


# ==========================================
# ===== WIDOK ADMINA (Pełny dostęp) =====
# ==========================================
def render_admin_view(df: pd.DataFrame):
    st.title("🛠️ Panel Administratora")
    st.success("Jesteś w trybie edycji (pełny dostęp).")

    with st.sidebar:
        st.markdown("---")
        st.write("### 🗑️ Usuwanie")
        df, deleted = render_delete_form(df, save_df) 
    
    # Auto-uzupełnianie powiatów
    df_before = df.copy()
    df_after, _, used_col = fill_powiat_auto(
        df, powiat_col="Powiat", kod_candidates=("Kod-pocztowy", "Kod-pocztowy ")
    )
    try:
        new_filled = (df_before["Powiat"].isna() & df_after["Powiat"].notna()).sum()
    except KeyError:
        new_filled = 0
    
    df = df_after
    if new_filled > 0:
        save_df(df)
        st.toast(f"ℹ️ Automat uzupełnił powiaty w {new_filled} wierszach.")

    with st.expander("🗺️ Pokaż mapę", expanded=False):
        if render_simple_map:
            render_simple_map(df)

    st.subheader("📑 Pełna baza danych (z nr zamówienia)")
    
    c1, c2 = st.columns([1, 2])
    with c1:
        search_field = st.selectbox("Szukaj po:", ["nr zamówienia", "nr badania"])
    with c2:
        q_admin = st.text_input("Szukana fraza...", key="admin_q")
    
    for col in COLS:
        if col not in df.columns:
            df[col] = pd.NA
    df = df.loc[:, COLS]

    if q_admin:
        mask = df[search_field].astype(str).str.contains(q_admin.strip(), case=False, na=False)
        res = df.loc[mask]
        st.dataframe(res, use_container_width=True)
    else:
        st.dataframe(df, use_container_width=True, height=400)

    st.divider()
    
    col_add, col_edit = st.columns(2)
    
    with col_add:
        st.subheader("➕ Dodaj rekord")
        df, added = render_add_form(df, save_df, COLS)
    
    with col_edit:
        st.subheader("✏️ Edytuj rekord")
        df, edited = render_edit_form(df, save_df, COLS)

    if any([added, edited, deleted]):
        st.rerun()


# ==========================================
# ===== LOGIKA GŁÓWNA =====
# ==========================================

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False      
if "show_login_form" not in st.session_state:
    st.session_state["show_login_form"] = False 

df = load_df()

# --- SIDEBAR (Pasek boczny) ---
with st.sidebar:
    
    # Logo w sidebarze
    logo_file = get_logo_path()
    if logo_file:
        st.image(logo_file, use_container_width=True)
    else:
        st.image("https://placehold.co/200x100?text=HIPPOVET", use_container_width=True)

    
    if st.session_state["logged_in"]:
        st.success("Zalogowano: Admin")
        if st.button("Wyloguj", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["show_login_form"] = False
            st.rerun()
            
    else:
        if not st.session_state["show_login_form"]:
            st.write("") 
            if st.button("🔐 Administracja", use_container_width=True):
                st.session_state["show_login_form"] = True
                st.rerun()
        else:
            st.markdown("---")
            st.markdown("##### Logowanie")
            password = st.text_input("Hasło:", type="password", key="login_pass")
            
            col_ok, col_x = st.columns([1, 1])
            with col_ok:
                if st.button("Zaloguj", use_container_width=True):
                    if password == "123":
                        st.session_state["logged_in"] = True
                        st.session_state["show_login_form"] = False
                        st.rerun()
                    else:
                        st.error("Błąd!")
            with col_x:
                if st.button("❌", use_container_width=True):
                    st.session_state["show_login_form"] = False
                    st.rerun()

# Wyświetlenie treści
if st.session_state["logged_in"]:
    render_admin_view(df)
else:
    render_public_view(df)

# STOPKA
render_footer()
