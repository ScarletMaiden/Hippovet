import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    parasite_cols = ["Anoplocephala perfoliata", "Oxyuris equi", "Parascaris equorum", "Strongyloides spp"]
    
    # 1. Wybór pasożyta i Przełącznik widoczności zer
    # Układamy to w kolumnach dla porządku
    col_sel, col_toggle = st.columns([2, 2])
    
    with col_sel:
        parasite = st.selectbox("Wybierz pasożyta:", parasite_cols, index=0)
        
    with col_toggle:
        # Pusty odstęp, żeby wyrównać z selectboxem
        st.write("") 
        st.write("") 
        # DUŻY PRZEŁĄCZNIK (TOGGLE) - Czytelniejszy niż checkbox
        show_zeros = st.toggle("🟡 Pokaż wyniki ujemne (0)", value=True)

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

    # Agregacja
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

    # Podział na >0 i ==0
    df_pos = agg[agg["cases"] > 0].copy()
    df_pos["size"] = df_pos["cases"].clip(lower=1)
    
    df_zero = agg[agg["cases"] == 0].copy()
    
    max_cases = int(df_pos["cases"].max()) if not df_pos.empty else 0

    # === RYSOWANIE MAPY ===
    
    # Warstwa 1: Wyniki pozytywne (Czerwone)
    if not df_pos.empty:
        fig = px.scatter_mapbox(
            df_pos,
            lat="latitude",
            lon="longitude",
            size="size",
            color="cases",
            color_continuous_scale="Reds",  # Czerwona skala
            hover_name="Powiat",
            hover_data={"cases": True, "size": False},
            zoom=5,
            height=500,
        )
    else:
        fig = go.Figure(go.Scattermapbox(lat=[], lon=[]))
        fig.update_layout(
            mapbox_style="open-street-map",
            mapbox=dict(center=dict(lat=52.0, lon=19.0), zoom=5),
            height=500
        )

    # Warstwa 2: Wyniki zerowe (Żółte) - tylko jeśli włączony przełącznik
    if show_zeros and not df_zero.empty:
        fig.add_trace(go.Scattermapbox(
            lat=df_zero["latitude"],
            lon=df_zero["longitude"],
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=9,
                color='gold',
                opacity=0.9
            ),
            text=df_zero["Powiat"] + ": BRAK pasożytów",
            hoverinfo='text',
            name='Wynik ujemny (0)'  # To pojawi się w legendzie
        ))

    # Wygląd mapy i legendy
    fig.update_layout(
        mapbox_style="open-street-map",
        margin=dict(l=0, r=0, t=0, b=0),
        uirevision="fixed",
        
        # POPRAWA CZYTELNOŚCI LEGENDY
        legend=dict(
            yanchor="top",
            y=0.98,
            xanchor="left",
            x=0.02,
            font=dict(
                family="Arial",
                size=14,           # Duża czcionka
                color="black"      # Zawsze czarny tekst (nawet w trybie nocnym)
            ),
            bgcolor="white",       # Białe tło pod napisami
            bordercolor="gray",    # Ramka dookoła legendy
            borderwidth=1
        )
    )
    
    # Skala kolorów (tylko dla czerwonych punktów)
    if not df_pos.empty:
        fig.update_coloraxes(
            cmin=0,
            cmax=max_cases if max_cases > 0 else 1,
            colorbar=dict(
                title="Liczba<br>przypadków",
                tickfont=dict(color="black"), # Czarne cyfry na skali
                titlefont=dict(color="black"),
                bgcolor="rgba(255,255,255,0.8)", # Tło pod skalą
                tick0=0, 
                dtick=1 if max_cases < 10 else None
            )
        )

    st.plotly_chart(fig, use_container_width=True)
