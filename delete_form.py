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

    mask = pd.Series(False, index=df.index)

    if option == "pozycja":
        mask = df["pozycja"].astype(str).str.strip() == value.strip()
    elif option == "nr badania" and "nr badania" in df.columns:
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

    try:
        save_fn(new_df.drop(columns=["pozycja"], errors="ignore"))
        st.success(f"✅ Usunięto {to_delete} rekord(ów).")

        return _with_pozycja(new_df.drop(columns=["pozycja"], errors="ignore")), True
    except Exception as e:
        st.error(f"❌ Błąd zapisu: {e}")
        return df, False
