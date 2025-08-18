import pandas as pd
import streamlit as st

def render_delete_form(df: pd.DataFrame, file_path: str):
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
            df.to_excel(file_path, index=False)

            # ⬇⬇⬇ unieważnij cache
            st.cache_data.clear()

            st.success(f"✅ Usunięto {n} rekord(y).")
            return df, True
        except Exception as e:
            st.error(f"❌ Błąd zapisu: {e}")
            return df, False

    return df, False
