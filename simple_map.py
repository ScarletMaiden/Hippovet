import re
import pandas as pd
import plotly.express as px
import streamlit as st
import pgeocode

nomi = pgeocode.Nominatim("PL")

def _norm_code(x) -> str | None:
    if x is None:
        return None
    s = re.sub(r"\D", "", str(x))
    if len(s) != 5:
        return None
    return f"{s[:2]}-{s[2:]}"

def _postal_to_coords(series: pd.Series) -> pd.DataFrame:
    codes = series.map(_norm_code).dropna().unique().tolist()
    if not codes:
        return pd.DataFrame(columns=["code_norm", "latitude", "longitude"])
    look = nomi.query_postal_code(codes)
    if isinstance(look, pd.Series):
        look = look.to_frame().T
    out = pd.DataFrame({
        "code_norm": look["postal_code"].astype(str),
        "latitude": look["latitude"],
        "longitude": look["longitude"],
    })
    return out.dropna(subset=["latitude", "longitude"]).drop_duplicates(subset=["code_norm"])

def render_simple_map(df: pd.DataFrame):
    st.subheader("🗺️ Prosta mapa punktowa (agregacja po powiecie)")

    parasite_cols = ["Anoplocephala perfoliata", "Oxyuris equi", "Parascaris equorum", "Strongyloides spp"]
    parasite = st.selectbox("Wybierz pasożyta:", parasite_cols, index=0)

    if "Kod-pocztowy" not in df.columns:
        st.info("Brak kolumny 'Kod-pocztowy' – mapa niedostępna.")
        return
    if "Powiat" not in df.columns:
        st.info("Brak kolumny 'Powiat' – uzupełnij ją przed rysowaniem mapy.")
        return

    dtmp = df.copy()
    dtmp[parasite] = pd.to_numeric(dtmp[parasite], errors="coerce").fillna(0).astype(int)
    dtmp["code_norm"] = dtmp["Kod-pocztowy"].map(_norm_code)
    coords = _postal_to_coords(dtmp["code_norm"])
    if coords.empty:
        st.info("Brak współrzędnych dla kodów pocztowych.")
        return

    m = (
        dtmp.merge(coords, on="code_norm", how="inner")
            .loc[lambda x: x["Powiat"].astype(str).str.strip() != ""]
    )
    if m.empty:
        st.info("Brak danych do pokazania na mapie.")
        return

    agg = (
        m.groupby("Powiat", dropna=True)
         .agg(cases=(parasite, "sum"),
              latitude=("latitude", "mean"),
              longitude=("longitude", "mean"))
         .reset_index()
    )

    remove_zero = st.checkbox("Usuń powiaty z 0 przypadków", value=True)
    if remove_zero:
        agg = agg[agg["cases"] > 0]

    if agg.empty:
        st.info("Brak danych do pokazania na mapie.")
        return
    agg["size"] = agg["cases"].clip(lower=1)
    max_cases = int(agg["cases"].max()) if len(agg) else 0

    fig = px.scatter_mapbox(
        agg,
        lat="latitude",
        lon="longitude",
        size="size",
        color="cases",
        color_continuous_scale="Blues", 
        hover_name="Powiat",
        hover_data={"cases": True},
        zoom=5,
        height=500,
    )
    fig.update_layout(
        mapbox_style="open-street-map",
        margin=dict(l=0, r=0, t=0, b=0),
        uirevision="fixed",
    )
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)

    fig.update_coloraxes(
        cmin=0,
        cmax=max_cases if max_cases > 0 else 1,
        colorbar=dict(title="przypadki", tick0=0, dtick=1, tickformat="d")
    )

    st.plotly_chart(fig, use_container_width=True)

