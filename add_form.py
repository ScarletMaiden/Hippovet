from typing import List, Callable
import pandas as pd
import streamlit as st
from powiat_utils import powiat_from_postal

def render_add_form(df: pd.DataFrame, save_fn: Callable[[pd.DataFrame], None], cols: List[str]):
    st.divider()
    st.subheader("➕ Dodaj nowy rekord")

    with st.form("add_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            nr_zam = st.text_input("nr zamówienia")
            nr_bad = st.text_input("nr badania *", help="To pole jest wymagane")
            imie = st.text_input("imię konia")
        with c2:
            kod = st.text_input("Kod-pocztowy", help="np. 12-345 albo 12345")
            miasto = st.text_input("Miasto")
        with c3:
            a = st.radio("Anoplocephala perfoliata", ["0", "1"], horizontal=True)
            o = st.radio("Oxyuris equi", ["0", "1"], horizontal=True)
            p = st.radio("Parascaris equorum", ["0", "1"], horizontal=True)
            s = st.radio("Strongyloides spp", ["0", "1"], horizontal=True)

        submitted = st.form_submit_button("Dodaj")

    if not submitted:
        return df, False

    # 🔒 Walidacja: wymagany numer badania
    if not nr_bad or not nr_bad.strip():
        st.error("⚠ Numer badania jest wymagany. Rekord nie został dodany.")
        return df, False

    try:
        new_row = {
            "nr zamówienia": nr_zam.strip() if nr_zam else "",
            "nr badania": nr_bad.strip(),
            "imię konia": imie.strip() if imie else "",
            "Anoplocephala perfoliata": int(a),
            "Oxyuris equi": int(o),
            "Parascaris equorum": int(p),
            "Strongyloides spp": int(s),
            "Kod-pocztowy": (kod or "").strip(),
            "Miasto": (miasto or "").strip(),
        }
        # Powiat z kodu (jeśli jest)
        if new_row["Kod-pocztowy"]:
            new_row["Powiat"] = powiat_from_postal(new_row["Kod-pocztowy"])
        else:
            new_row["Powiat"] = ""

        # Dołóż brakujące kolumny
        for c in cols:
            if c not in df.columns:
                df[c] = pd.NA

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # 🔄 ZAPIS DO GOOGLE SHEETS
        save_fn(df)

        st.success("✅ Rekord dodany.")
        return df, True

    except Exception as e:
        st.error(f"❌ Nie udało się zapisać: {e}")
        return df, False
