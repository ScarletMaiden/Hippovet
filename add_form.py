import streamlit as st
import pandas as pd
from powiat_utils import load_df, save_df

def add_form():
    st.header("Dodaj nowy rekord")

    with st.form("add_record_form"):
        nr_zamowienia = st.text_input("Numer zamówienia")
        nr_badania = st.text_input("Numer badania *")  # wymagane pole
        imie = st.text_input("Imię")
        nazwisko = st.text_input("Nazwisko")
        data = st.date_input("Data")

        submitted = st.form_submit_button("Dodaj rekord")

        if submitted:
            if not nr_badania.strip():  # sprawdzamy czy niepuste
                st.error("⚠ Numer badania jest wymagany. Rekord nie został dodany.")
            else:
                df = load_df()
                new_record = {
                    "Numer zamówienia": nr_zamowienia,
                    "Numer badania": nr_badania,
                    "Imię": imie,
                    "Nazwisko": nazwisko,
                    "Data": data.strftime("%Y-%m-%d"),
                }
                df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
                save_df(df)
                st.success("✅ Rekord został dodany pomyślnie!")
