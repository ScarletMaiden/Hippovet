import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go  # Dodajemy to do obsługi żółtych kropek
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
    # Wybór pasożyta (bez zmian)
    parasite_cols = ["Anoplocephala perfoliata", "Oxyuris equi", "Parascaris equorum", "Strongyloides spp"]
    
    # Tworzymy kolumny (3 obok siebie) dla lepszego wyglądu selectboxa
    c1, c2 = st.columns([1, 3])
    with c1:
        st.write("") # Pusty odstęp, żeby wyrównać z nagłówkiem
        st.markdown("**Wybierz pasożyta:**")
    with c2:
        parasite = st.selectbox("", parasite_cols, index=0, label_visibility="collapsed")

    # Sprawdzenie kolumn (bez zmian)
    if "Kod-pocztowy" not in df.columns:
        st.info("Brak kolumny 'Kod-pocztowy' – mapa niedostępna.")
        return
    if "Powiat" not in df.columns:
        st.info("Brak kolumny 'Powiat' – uzupełnij ją przed rysowaniem mapy.")
        return

    # Przygotowanie danych
    dtmp = df.copy()
    dtmp[parasite] = pd.to_numeric(dtmp[parasite], errors="coerce").fillna(0).astype(int)
    dtmp["code_norm"] = dtmp["Kod-pocztowy"].map(_norm_code)
    
    # Pobranie współrzędnych
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

    # Agregacja po powiecie
    agg = (
        m.groupby("Powiat", dropna=True)
         .agg(cases=(parasite, "sum"),
              latitude=("latitude", "mean"),
              longitude=("longitude", "mean"))
         .reset_index()
    )

    if agg.empty:
        st.info("Brak danych.")
        return

    # === TUTAJ ZMIANA: DZIELIMY DANE NA DWA ZBIORY ===
    
    # 1. Zbiór pozytywny (tam gdzie są przypadki > 0)
    df_pos = agg[agg["cases"] > 0].copy()
    df_pos["size"] = df_pos["cases"].clip(lower=1) # Rozmiar kropki zależny od liczby przypadków

    # 2. Zbiór zerowy (tam gdzie cases == 0)
    df_zero = agg[agg["cases"] == 0].copy()
    
    # Ustalmy max_cases do skali kolorów
    max_cases = int(df_pos["cases"].max()) if not df_pos.empty else 0

    # === RYSOWANIE ===
    
    # KROK 1: Rysujemy mapę bazową dla wyników pozytywnych (czerwona skala)
    if not df_pos.empty:
        fig = px.scatter_mapbox(
            df_pos,
            lat="latitude",
            lon="longitude",
            size="size",
            color="cases",
            # Zmieniamy skalę na Reds (czerwienie)
            color_continuous_scale="Reds", 
            hover_name="Powiat",
            hover_data={"cases": True, "size": False},
            zoom=5,
            height=500,
        )
    else:
        # Jeśli nie ma żadnych pozytywnych przypadków, tworzymy pustą mapę
        fig = go.Figure(go.Scattermapbox(lat=[], lon=[]))
        fig.update_layout(
            mapbox_style="open-street-map",
            mapbox=dict(center=dict(lat=52.0, lon=19.0), zoom=5),
            margin=dict(l=0, r=0, t=0, b=0),
            height=500
        )

    # KROK 2: Dokładamy żółte kropki dla wyników zerowych
    if not df_zero.empty:
        fig.add_trace(go.Scattermapbox(
            lat=df_zero["latitude"],
            lon=df_zero["longitude"],
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=9,             # Stały rozmiar dla zer
                color='gold',       # Kolor ZŁOTY/ŻÓŁTY
                opacity=0.9
            ),
            text=df_zero["Powiat"] + ": 0 przypadków", # Co widać po najechaniu
            hoverinfo='text',
            name='0 przypadków'     # Legenda
        ))

    # Konfiguracja wyglądu mapy
    fig.update_layout(
        mapbox_style="open-street-map",
        margin=dict(l=0, r=0, t=0, b=0),
        uirevision="fixed",
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.8)"
        )
    )
    
    # Ustawienia skali kolorów (tylko jeśli są pozytywne wyniki)
    if not df_pos.empty:
        fig.update_coloraxes(
            cmin=0,
            cmax=max_cases if max_cases > 0 else 1,
            colorbar=dict(title="Liczba<br>przypadków", tick0=0, dtick=1 if max_cases < 10 else None)
        )

    st.plotly_chart(fig, use_container_width=True)
