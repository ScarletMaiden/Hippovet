# delete_form.py
from typing import Callable
import pandas as pd
import streamlit as st

def _with_pozycja(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    nb = pd.to_numeric(out.get("nr badania"), errors="coerce")
    sorted_idx = (
        pd.Series(range(len(out)), index=out.index)
        .to_frame("_orig")
        .assign(_nb=nb)
        .sort_values(by=["_nb", "_orig"], ascending=[True, True], na_position="last")
        .index
    )
    pozycja_map = {idx: i for i, idx in enumerate(sorted_idx, start=1)}
    out.insert(0, "pozycja", out.index.map(pozycja_map))
    out = out.sort_values("pozycja").reset_index(drop=True)
    return out

def render_delete_form(df: pd.DataFrame, save_fn: Callable[[pd.DataFrame], None]):
    df = _with_pozycja(df)

    st.divider()
    st.subheader("🗑️ Usuń rekord")

    with st.form("delete_form"):
        option = st.radio(
            "Wybierz kryterium usuwania:",
            ["pozycja", "nr badania", "nr zamówienia"],
            horizontal=False
        )
        value = st.text_input(f"Podaj {option}")
        submitted = st.form_submit_button("Usuń", type="primary", use_container_width=True)

    if not submitted:
        return df, False

    if not value.strip():
        st.error(f"⚠ Musisz podać {option}, aby usunąć rekord.")
        return df, False

    # ---- USUWANIE PO POZYCJI: bez masek, po prostu iloc ----
    if option == "pozycja":
        try:
            pos = int(value.strip())
        except ValueError:
            st.error("Pozycja musi być liczbą całkowitą.")
            return df, False

        if pos < 1 or pos > len(df):
            st.error(f"Pozycja {pos} jest poza zakresem 1–{len(df)}.")
            return df, False

        # znajdź realny indeks wiersza o danej pozycji (pozycja jest 1-based)
        idx_to_drop = df.index[pos - 1]  # bo df jest już posortowany po 'pozycja'
        new_df = df.drop(index=idx_to_drop).copy()

    else:
        # warianty po kolumnach
        if option == "nr badania" and "nr badania" in df.columns:
            mask = df["nr badania"].astype(str).str.strip() == value.strip()
        elif option == "nr zamówienia" and "nr zamówienia" in df.columns:
            mask = df["nr zamówienia"].astype(str).str.strip() == value.strip()
        else:
            st.warning(f"Kolumna '{option}' nie istnieje w danych.")
            return df, False

        to_delete = int(mask.sum())
        if to_delete == 0:
            st.info("❕ Nie znaleziono pasujących rekordów.")
            return df, False

        new_df = df.loc[~mask].copy()

    # zapis bez pomocniczej 'pozycja'
    try:
        save_fn(new_df.drop(columns=["pozycja"], errors="ignore"))
        st.success("✅ Usunięto rekord.")
        # przeliczenie pozycji do dalszego wyświetlania
        return _with_pozycja(new_df.drop(columns=["pozycja"], errors="ignore")), True
    except Exception as e:
        st.error(f"❌ Błąd zapisu: {e}")
        return df, False
