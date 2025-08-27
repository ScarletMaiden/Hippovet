from typing import List
import re
import pandas as pd
import streamlit as st
from powiat_utils import powiat_from_postal


def _norm(s) -> str:
    """Prosta normalizacja do porównań: string, bez nadmiarowych spacji."""
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()


def render_add_form(df: pd.DataFrame, file_path: str, cols: List[str]):
    st.divider()
    st.subheader("➕ Dodaj nowy rekord")

    with st.form("add_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            nr_zam = st.text_input("nr zamówienia")
            nr_bad = st.text_input("nr badania", help="Pole wymagane i unikalne")
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

    nr_bad_norm = _norm(nr_bad)
    if nr_bad_norm == "":
        st.error("❌ 'nr badania' jest wymagany — uzupełnij to pole.")
        return df, False

    if "nr badania" not in df.columns:
        df["nr badania"] = pd.NA

    existing_norm = df["nr badania"].astype(str).map(_norm)
    if existing_norm.eq(nr_bad_norm).any():
        st.warning("⚠️ Rekord z takim 'nr badania' już istnieje. Dodawanie przerwane.")
        return df, False

    try:
        new_row = {
            "nr zamówienia": _norm(nr_zam),
            "nr badania": nr_bad_norm,
            "imię konia": _norm(imie),
            "Anoplocephala perfoliata": int(a),
            "Oxyuris equi": int(o),
            "Parascaris equorum": int(p),
            "Strongyloides spp": int(s),
            "Kod-pocztowy": _norm(kod),
            "Miasto": _norm(miasto),
        }

        if new_row["Kod-pocztowy"]:
            new_row["Powiat"] = powiat_from_postal(new_row["Kod-pocztowy"])
        else:
            new_row["Powiat"] = ""

        for c in cols:
            if c not in df.columns:
                df[c] = pd.NA

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(file_path, index=False)

        st.cache_data.clear()

        st.success("✅ Rekord dodany.")
        return df, True

    except Exception as e:
        st.error(f"❌ Nie udało się zapisać: {e}")
        return df, False
