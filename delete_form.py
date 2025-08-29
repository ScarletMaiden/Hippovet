import streamlit as st
import pandas as pd
from powiat_utils import load_df, save_df

def delete_form():
    st.header("Usuń rekord")

    with st.form("delete_record_form"):
        nr_zamowienia = st.text_input("Numer zamówienia (opcjonalnie)")
        nr_badania = st.text_input("Numer badania (opcjonalnie)")

        submitted = st.form_submit_button("Usuń rekord")

        if submitted:
            if not nr_zamowienia.strip() and not nr_badania.strip():
                st.error("⚠ Podaj numer zamówienia lub numer badania, aby usunąć rekord.")
            else:
                df = load_df()
                start_len = len(df)

                if nr_zamowienia.strip():
                    df = df[df["Numer zamówienia"] != nr_zamowienia]

                if nr_badania.strip():
                    df = df[df["Numer badania"] != nr_badania]

                if len(df) < start_len:
                    save_df(df)
                    st.success("✅ Rekord został usunięty.")
                else:
                    st.warning("⚠ Nie znaleziono pasującego rekordu.")
