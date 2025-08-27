import pandas as pd
import streamlit as st


def render_delete_form(df: pd.DataFrame, file_path: str):
    """
    Usuwanie rekordów po wybranym kluczu:
    - "nr badania" (domyślnie)
    - "nr zamówienia"

    Zwraca (df_po_usunięciu, czy_usunięto_bool)
    """
    st.subheader("🗑️ Usuń rekord")

    key_choice = st.radio(
        "Wybierz po czym chcesz usunąć:",
        ["nr badania", "nr zamówienia"],
        index=0,
        horizontal=True,
        key="delete_key_choice",
    )

    placeholder = "Podaj nr badania" if key_choice == "nr badania" else "Podaj nr zamówienia"
    value = st.text_input(placeholder, key="delete_value")

    # Podpowiedź: gdy po "nr zamówienia" może być wiele rekordów
    if key_choice == "nr zamówienia":
        st.caption("Uwaga: pod jednym numerem zamówienia może być wiele rekordów – wszystkie zostaną usunięte.")

    delete_btn = st.button("Usuń rekord(y)", type="primary", use_container_width=True)

    if delete_btn and value:
        col = key_choice
        if col not in df.columns:
            st.error(f"❌ Brak kolumny '{col}' w danych.")
            return df, False

        mask = df[col].astype(str).str.strip() == str(value).strip()
        n = int(mask.sum())
        if n == 0:
            st.warning("Nie znaleziono pasujących rekordów.")
            return df, False

        df = df.loc[~mask].copy()
        try:
            df.to_excel(file_path, index=False)
            st.cache_data.clear()  # odświeżenie cache po zapisie
            st.success(f"✅ Usunięto {n} rekord(y) po '{col}'.")
            return df, True
        except Exception as e:
            st.error(f"❌ Błąd zapisu: {e}")
            return df, False

    return df, False
