from typing import List, Callable
import pandas as pd
import streamlit as st
from powiat_utils import powiat_from_postal

def render_edit_form(df: pd.DataFrame, save_fn: Callable[[pd.DataFrame], None], cols: List[str]):
    st.divider()
    st.subheader("✏️ Edytuj istniejący rekord")

    nr_badania = st.text_input("Podaj 'nr badania' do edycji", key="edit_id")
    row_idx = None

    if nr_badania:
        # Znajdź wszystkie indeksy pasujące do numeru badania
        mask = df["nr badania"].astype(str) == nr_badania.strip()
        matching_indices = df.index[mask].tolist()

        if len(matching_indices) == 1:
            row_idx = matching_indices[0]
        elif len(matching_indices) > 1:
            st.warning(f"🔎 Znaleziono {len(matching_indices)} rekordy dla numeru: {nr_badania}")
            
            # Tworzymy listę opcji do wyboru dla użytkownika, żeby wiedział który rekord edytuje
            options = {
                idx: f"Koń: {df.at[idx, 'imię konia']} | Zamówienie: {df.at[idx, 'nr zamówienia']} (wiersz {idx+2})"
                for idx in matching_indices
            }
            
            # Selectbox do wyboru konkretnego wiersza
            selected_idx = st.selectbox(
                "Wybierz konkretny rekord do edycji:",
                options=list(options.keys()),
                format_func=lambda x: options[x]
            )
            row_idx = selected_idx
        else:
            st.info("Nie znaleziono rekordu o podanym numerze.")

    # Jeśli nie wybrano/nie znaleziono wiersza, kończymy
    if row_idx is None:
        return df, False

    # Pobieramy dane wybranego wiersza
    row = df.loc[row_idx].to_dict()

    # Formularz edycji
    with st.form("edit_form_container"):
        st.write(f"### Edycja wiersza: {row_idx + 2}") # +2 bo nagłówek i indeks 0
        c1, c2, c3 = st.columns([1, 1, 1])
        
        with c1:
            nr_zam = st.text_input("nr zamówienia", value=str(row.get("nr zamówienia") or ""))
            nr_bad_val = st.text_input("nr badania", value=str(row.get("nr badania") or ""))
            imie = st.text_input("imię konia", value=str(row.get("imię konia") or ""))
        
        with c2:
            kod = st.text_input("Kod-pocztowy", value=str(row.get("Kod-pocztowy") or ""))
            miasto = st.text_input("Miasto", value=str(row.get("Miasto") or ""))
            
        with c3:
            # Funkcja pomocnicza do bezpiecznej konwersji na int dla radio
            def safe_int(val):
                try: return int(float(val))
                except: return 0

            a = st.radio("Anoplocephala perfoliata", ["0", "1"], index=safe_int(row.get("Anoplocephala perfoliata")), horizontal=True)
            o = st.radio("Oxyuris equi", ["0", "1"], index=safe_int(row.get("Oxyuris equi")), horizontal=True)
            p = st.radio("Parascaris equorum", ["0", "1"], index=safe_int(row.get("Parascaris equorum")), horizontal=True)
            s = st.radio("Strongyloides spp", ["0", "1"], index=safe_int(row.get("Strongyloides spp")), horizontal=True)

        submitted = st.form_submit_button("Zapisz zmiany")

    if submitted:
        try:
            # Aktualizacja wybranego wiersza w DataFrame
            df.at[row_idx, "nr zamówienia"] = nr_zam.strip()
            df.at[row_idx, "nr badania"] = nr_bad_val.strip()
            df.at[row_idx, "imię konia"] = imie.strip()
            df.at[row_idx, "Kod-pocztowy"] = kod.strip()
            df.at[row_idx, "Miasto"] = miasto.strip()
            df.at[row_idx, "Anoplocephala perfoliata"] = int(a)
            df.at[row_idx, "Oxyuris equi"] = int(o)
            df.at[row_idx, "Parascaris equorum"] = int(p)
            df.at[row_idx, "Strongyloides spp"] = int(s)

            # Aktualizacja powiatu
            if kod.strip():
                df.at[row_idx, "Powiat"] = powiat_from_postal(kod.strip())

            # Zapis do Google Sheets
            save_fn(df)
            st.success(f"✅ Zaktualizowano rekord dla konia {imie}!")
            return df, True

        except Exception as e:
            st.error(f"❌ Błąd przy zapisie: {e}")
            return df, False

    return df, False
