# delete_form.py
from typing import Callable
import pandas as pd
import streamlit as st

def render_delete_form(df: pd.DataFrame, save_fn: Callable[[pd.DataFrame], None]):
    st.divider()
    st.subheader("🗑️ Usuń rekordy")

    with st.form("delete_form"):
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            by_nr_badania = st.text_input("nr badania (opcjonalnie)")
        with c2:
            by_nr_zamowienia = st.text_input("nr zamówienia (opcjonalnie)")
        with c3:
            by_id = st.text_input("ID rekordu (opcjonalnie)")
        submitted = st.form_submit_button("Usuń", type="primary", use_container_width=True)

    if not submitted:
        return df, False

    # Walidacja: musi być przynajmniej jedno kryterium
    if not any([by_nr_badania.strip() if by_nr_badania else "",
                by_nr_zamowienia.strip() if by_nr_zamowienia else "",
                by_id.strip() if by_id else ""]):
        st.error("⚠ Podaj przynajmniej jedno kryterium: nr badania, nr zamówienia lub ID.")
        return df, False

    # Przygotuj maskę do usuwania
    mask = pd.Series(False, index=df.index)

    # Usuwanie po nr badania
    if by_nr_badania and "nr badania" in df.columns:
        val = by_nr_badania.strip()
        mask = mask | (df["nr badania"].astype(str).str.strip() == val)
    elif by_nr_badania:
        st.warning("Kolumna 'nr badania' nie istnieje w danych.")

    # Usuwanie po nr zamówienia
    if by_nr_zamowienia and "nr zamówienia" in df.columns:
        val = by_nr_zamowienia.strip()
        mask = mask | (df["nr zamówienia"].astype(str).str.strip() == val)
    elif by_nr_zamowienia:
        st.warning("Kolumna 'nr zamówienia' nie istnieje w danych.")

    # Usuwanie po ID (obsłuż alternatywę 'id' jeśli taka jest)
    id_col = None
    if "ID" in df.columns:
        id_col = "ID"
    elif "id" in df.columns:
        id_col = "id"

    if by_id:
        if id_col is not None:
            val = by_id.strip()
            mask = mask | (df[id_col].astype(str).str.strip() == val)
        else:
            st.warning("Kolumna 'ID' (ani 'id') nie istnieje w danych.")

    to_delete = int(mask.sum())
    if to_delete == 0:
        st.info("Nie znaleziono pasujących rekordów do usunięcia.")
        return df, False

    # Usuń i zapisz
    new_df = df.loc[~mask].copy()
    try:
        save_fn(new_df)
        st.success(f"✅ Usunięto {to_delete} rekord(ów).")
        return new_df, True
    except Exception as e:
        st.error(f"❌ Błąd zapisu: {e}")
        return df, False
