# delete_form.py
from typing import Callable
import pandas as pd
import streamlit as st

def render_delete_form(df: pd.DataFrame, save_fn: Callable[[pd.DataFrame], None]):
    st.divider()
    st.subheader("🗑️ Usuń rekord")

    with st.form("delete_form"):
        # wybór kryterium
        option = st.radio(
            "Wybierz kryterium usuwania:",
            ["nr badania", "nr zamówienia", "ID rekordu"],
            horizontal=False
        )

        # odpowiednie pole w zależności od wyboru
        value = st.text_input(f"Podaj {option}")

        submitted = st.form_submit_button("Usuń", type="primary", use_container_width=True)

    if not submitted:
        return df, False

    if not value.strip():
        st.error(f"⚠ Musisz podać {option}, aby usunąć rekord.")
        return df, False

    # przygotuj maskę
    mask = pd.Series(False, index=df.index)

    if option == "nr badania" and "nr badania" in df.columns:
        mask = df["nr badania"].astype(str).str.strip() == value.strip()
    elif option == "nr zamówienia" and "nr zamówienia" in df.columns:
        mask = df["nr zamówienia"].astype(str).str.strip() == value.strip()
    elif option == "ID rekordu":
        id_col = "ID" if "ID" in df.columns else ("id" if "id" in df.columns else None)
        if id_col:
            mask = df[id_col].astype(str).str.strip() == value.strip()
        else:
            st.warning("Kolumna 'ID' nie istnieje w danych.")
            return df, False
    else:
        st.warning(f"Kolumna '{option}' nie istnieje w danych.")
        return df, False

    to_delete = int(mask.sum())
    if to_delete == 0:
        st.info("❕ Nie znaleziono pasujących rekordów.")
        return df, False

    # usuń i zapisz
    new_df = df.loc[~mask].copy()
    try:
        save_fn(new_df)
        st.success(f"✅ Usunięto {to_delete} rekord(ów).")
        return new_df, True
    except Exception as e:
        st.error(f"❌ Błąd zapisu: {e}")
        return df, False
