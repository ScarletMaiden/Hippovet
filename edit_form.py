from typing import List
import pandas as pd
import streamlit as st
from powiat_utils import powiat_from_postal

def render_edit_form(df: pd.DataFrame, file_path: str, cols: List[str]):
    st.divider()
    st.subheader("✏️ Edytuj istniejący rekord")

    nr_badania = st.text_input("Podaj 'nr badania' do edycji", key="edit_id")
    row_idx = None

    if nr_badania:
        mask = df["nr badania"].astype(str) == nr_badania.strip()
        idx = df.index[mask]
        if len(idx) == 1:
            row_idx = idx[0]
            row = df.loc[row_idx].to_dict()
        elif len(idx) > 1:
            st.warning("Znaleziono wiele rekordów z tym samym 'nr badania'. Edycja wstrzymana.")
        else:
            st.info("Nie znaleziono rekordu o podanym numerze.")

    if row_idx is None:
        return df, False

    with st.form("edit_form"):
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            nr_zam = st.text_input("nr zamówienia", value=str(row.get("nr zamówienia") or ""))
            nr_bad = st.text_input("nr badania", value=str(row.get("nr badania") or ""))
            imie = st.text_input("imię konia", value=str(row.get("imię konia") or ""))
        with c2:
            kod = st.text_input("Kod-pocztowy", value=str(row.get("Kod-pocztowy") or ""))
            miasto = st.text_input("Miasto", value=str(row.get("Miasto") or ""))
        with c3:
            a = st.radio("Anoplocephala perfoliata", ["0", "1"], index=int(row.get("Anoplocephala perfoliata") or 0), horizontal=True)
            o = st.radio("Oxyuris equi", ["0", "1"], index=int(row.get("Oxyuris equi") or 0), horizontal=True)
            p = st.radio("Parascaris equorum", ["0", "1"], index=int(row.get("Parascaris equorum") or 0), horizontal=True)
            s = st.radio("Strongyloides spp", ["0", "1"], index=int(row.get("Strongyloides spp") or 0), horizontal=True)

        submitted = st.form_submit_button("Zapisz zmiany")

    if not submitted:
        return df, False

    try:
        df.at[row_idx, "nr zamówienia"] = nr_zam.strip()
        df.at[row_idx, "nr badania"] = nr_bad.strip()
        df.at[row_idx, "imię konia"] = imie.strip()
        df.at[row_idx, "Kod-pocztowy"] = kod.strip()
        df.at[row_idx, "Miasto"] = miasto.strip()
        df.at[row_idx, "Anoplocephala perfoliata"] = int(a)
        df.at[row_idx, "Oxyuris equi"] = int(o)
        df.at[row_idx, "Parascaris equorum"] = int(p)
        df.at[row_idx, "Strongyloides spp"] = int(s)

        if df.at[row_idx, "Kod-pocztowy"]:
            df.at[row_idx, "Powiat"] = powiat_from_postal(df.at[row_idx, "Kod-pocztowy"])

        df.to_excel(file_path, index=False)

        st.cache_data.clear()

        st.success("✅ Zmiany zapisane.")
        return df, True

    except Exception as e:
        st.error(f"❌ Błąd przy zapisie: {e}")
        return df, False

