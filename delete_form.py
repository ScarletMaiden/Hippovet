from typing import Callable
import pandas as pd
import streamlit as st

def render_delete_form(df: pd.DataFrame, save_fn: Callable[[pd.DataFrame], None]):
    order_id = st.text_input("Podaj nr badania do usunięcia", key="delete_id")
    delete_btn = st.button("Usuń rekord", type="primary", use_container_width=True)

    if delete_btn and order_id:
        mask = df["nr badania"].astype(str) == order_id.strip()
        n = int(mask.sum())
        if n == 0:
            st.warning("Nie znaleziono rekordu o podanym numerze.")
            return df, False

        df = df.loc[~mask].copy()

        try:
            # 🔄 ZAPIS DO GOOGLE SHEETS
            save_fn(df)

            st.success(f"✅ Usunięto {n} rekord(y).")
            return df, True
        except Exception as e:
            st.error(f"❌ Błąd zapisu: {e}")
            return df, False

    return df, False
