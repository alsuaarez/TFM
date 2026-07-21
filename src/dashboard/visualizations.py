"""
Visualizaciones del dashboard: radar de estilo y comparación entre jugadores.
"""

import pandas as pd
import plotly.graph_objects as go

from data_loader import STYLE_METRICS


def _normalize_row(df_reference: pd.DataFrame, row_raw: pd.Series, metrics: list[str]) -> dict:
    """
    Normaliza un jugador a 0-100 por métrica, usando min/max de
    `df_reference` como escala. Se pasa la fila cruda en vez de pre-normalizar
    todo el dataframe para poder usar la misma escala de referencia tanto en
    el jugador buscado como en el de comparación, aunque este último no esté
    dentro de `df_reference`.
    """
    out = {}
    for m in metrics:
        min_v, max_v = df_reference[m].min(), df_reference[m].max()
        valor = row_raw.get(m)
        if pd.isna(valor):
            out[m] = 0
        elif max_v - min_v == 0:
            out[m] = 50
        else:
            normalizado = 100 * (valor - min_v) / (max_v - min_v)
            out[m] = min(max(normalizado, 0), 100) 
    return out


def style_radar_chart(
    df_full: pd.DataFrame,
    player_name: str,
    compare_to: str | None = None,
    metrics: list[str] | None = None,
) -> go.Figure:
    metrics = metrics or [m for m in STYLE_METRICS if m in df_full.columns]

    target_rows = df_full[df_full["player_name"] == player_name]
    if target_rows.empty:
        return go.Figure()
    target_raw = target_rows.iloc[0]

    # Normalizar dentro de la misma familia de posición del jugador buscado,
    # no contra todo el universo: mezclar porteros con delanteros aplasta
    # casi todas las métricas cerca de 0 salvo 1-2 ejes. 
    # Si el grupo es demasiado pequeño para ser representativo, se
    # usa el universo completo como respaldo.
    familia = target_raw.get("position_family") if "position_family" in df_full.columns else None
    universo_ref = df_full
    if familia:
        candidato_universo = df_full[df_full["position_family"] == familia]
        if len(candidato_universo) >= 5:
            universo_ref = candidato_universo

    fig = go.Figure()

    def add_trace(name: str, color: str):
        rows = df_full[df_full["player_name"] == name]
        if rows.empty:
            return
        valores_norm = _normalize_row(universo_ref, rows.iloc[0], metrics)
        values = [valores_norm[m] for m in metrics]
        values.append(values[0])
        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=metrics + [metrics[0]],
                fill="toself",
                name=name,
                line=dict(color=color),
                opacity=0.6,
            )
        )

    add_trace(player_name, "#1f77b4")
    if compare_to:
        add_trace(compare_to, "#d62728")

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        margin=dict(l=40, r=40, t=40, b=40),
    )
    return fig


def similarity_bar_chart(similar_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=similar_df["similarity_score"],
            y=similar_df["player_name"],
            orientation="h",
            marker=dict(color=similar_df["similarity_score"], colorscale="Blues"),
        )
    )
    fig.update_layout(
        xaxis_title="Score de similitud",
        yaxis=dict(autorange="reversed"),
        margin=dict(l=10, r=10, t=30, b=10),
        height=max(300, 28 * len(similar_df)),
    )
    return fig
