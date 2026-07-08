"""
Dashboard de scouting — UD Las Palmas
Buscar cualquier jugador (mercado, cantera o primer equipo), ver su ficha,
y compararlo o buscar similares dentro de su familia de posición.

Ejecutar desde la raíz del repo (TFM/):
    streamlit run src/dashboard/app.py
"""

import streamlit as st

from data_loader import load_players, filter_players, get_player_row, load_team_match_stats
from similarity_engine import (
    compute_pca_profile,
    compute_similarity_scores,
    compute_team_style_reference,
    compute_team_fit_scores,
)
from visualizations import style_radar_chart, similarity_bar_chart

st.set_page_config(page_title="Scouting Dashboard — UD Las Palmas", layout="wide")

st.title("Sistema de identificación y comparación de jugadores")
st.caption("UD Las Palmas · Temporada 26/27")

# --- Carga de datos --------------------------------------------------------
df = load_players()

try:
    df_pca, pca_model = compute_pca_profile(df)
except ValueError as e:
    st.error(str(e))
    st.stop()

# --- Sidebar: filtros de búsqueda ------------------------------------------
st.sidebar.header("Filtros de búsqueda")

leagues = ["Todas"] + sorted(df["league"].dropna().unique().tolist())
families = ["Todas"] + sorted(df["position_family"].dropna().unique().tolist())
sources = ["Todos"] + sorted(df["source"].dropna().unique().tolist())

f_league = st.sidebar.selectbox("Liga", leagues)
f_family = st.sidebar.selectbox("Familia de posición", families)
f_source = st.sidebar.selectbox(
    "Origen", sources, help="mercado / cantera / primer_equipo / seleccion"
)
f_max_age = st.sidebar.slider("Edad máxima", 16, 40, 32)

filtered = filter_players(
    df, league=f_league, position_family=f_family, source=f_source, max_age=f_max_age
)

st.sidebar.markdown(f"**{len(filtered)}** jugadores tras el filtro")

# --- Selección de jugador ---------------------------------------------------
player_options = sorted(filtered["player_name"].unique().tolist())
if not player_options:
    st.warning("Ningún jugador cumple los filtros seleccionados.")
    st.stop()

selected_player = st.selectbox("Buscar jugador", player_options)

# --- Ficha del jugador -------------------------------------------------------
row = get_player_row(df, selected_player)

col_info, col_radar = st.columns([1, 1.4])

with col_info:
    st.subheader(row["player_name"])
    st.write(f"**Equipo:** {row['team']}")
    st.write(f"**Liga:** {row['league']}")
    st.write(f"**Posición:** {row['position']} ({row['position_family']})")
    st.write(f"**Edad:** {row['age']}")
    st.write(f"**Minutos jugados:** {row['minutes_played']}")
    st.write(f"**Origen:** {row['source']}")
    if "market_value" in row:
        st.write(f"**Valor de mercado:** {row['market_value']}")
    if "contract_expiry" in row:
        st.write(f"**Fin de contrato:** {row['contract_expiry']}")

with col_radar:
    st.markdown("**Perfil de estilo**")
    compare_target = st.selectbox(
        "Comparar contra (opcional)",
        ["Ninguno"] + [p for p in player_options if p != selected_player],
    )
    compare_to = None if compare_target == "Ninguno" else compare_target
    fig = style_radar_chart(df, selected_player, compare_to=compare_to)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

tab_similares, tab_encaje = st.tabs(
    ["Jugadores similares", "Encaje con el estilo UD Las Palmas"]
)

# --- Tab 1: jugadores similares (jugador vs jugador) ------------------------
with tab_similares:
    st.subheader(f"Jugadores con estilo similar a {selected_player}")

    same_family = st.checkbox(
        "Restringir a la misma familia de posición",
        value=True,
        help="Corrige el filtrado demasiado estricto identificado en el motor inicial.",
    )
    top_n = st.slider("Número de candidatos a mostrar", 5, 30, 10, key="topn_similares")

    similar_df = compute_similarity_scores(
        df_pca, selected_player, same_position_family=same_family, top_n=top_n
    )

    if similar_df.empty:
        st.info("No se han encontrado candidatos con los filtros actuales.")
    else:
        col_table, col_chart = st.columns([1.2, 1])
        with col_table:
            st.dataframe(similar_df, use_container_width=True, hide_index=True)
        with col_chart:
            st.plotly_chart(similarity_bar_chart(similar_df), use_container_width=True)

# --- Tab 2: encaje con el perfil de estilo del equipo -----------------------
with tab_encaje:
    st.subheader("Ranking de encaje táctico con el estilo del primer equipo")
    st.caption(
        "El perfil objetivo se calcula como la media de las métricas de "
        "estilo de Las Palmas en Team_Stats. Cada jugador se puntúa por "
        "cercanía a ese vector de referencia, no contra otro jugador."
    )

    team_stats_df = load_team_match_stats()

    if team_stats_df.empty:
        st.warning(
            "No se ha podido cargar Team_Stats_*.xlsx desde data/udlaspalmas."
        )
    else:
        try:
            team_reference = compute_team_style_reference(team_stats_df, team_name="Las Palmas")
        except ValueError as e:
            st.error(str(e))
            team_reference = None

        if team_reference is not None:
            family_options = ["Todas"] + sorted(
                df["position_family"].dropna().unique().tolist()
            )
            fit_family = st.selectbox(
                "Filtrar por familia de posición", family_options, key="fit_family"
            )
            fit_family_arg = None if fit_family == "Todas" else fit_family
            fit_top_n = st.slider("Número de jugadores a mostrar", 5, 40, 15, key="topn_encaje")

            try:
                fit_df = compute_team_fit_scores(
                    df, team_reference, same_position_family=fit_family_arg, top_n=fit_top_n
                )
                st.dataframe(fit_df, use_container_width=True, hide_index=True)
            except ValueError as e:
                st.error(str(e))

            with st.expander("Ver perfil de referencia del equipo (valores medios)"):
                st.dataframe(team_reference.rename("Las Palmas (media)"))
