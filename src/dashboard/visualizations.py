"""
Visualizaciones del dashboard: radar de estilo y comparación entre jugadores.
"""

import pandas as pd
import plotly.graph_objects as go

from data_loader import STYLE_METRICS


def _normalize_metrics(df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    out = df.copy()
    for m in metrics:
        min_v, max_v = df[m].min(), df[m].max()
        if max_v - min_v == 0:
            out[m] = 50
        else:
            out[m] = 100 * (df[m] - min_v) / (max_v - min_v)
    return out


def style_radar_chart(
    df_full: pd.DataFrame,
    player_name: str,
    compare_to: str | None = None,
    metrics: list[str] | None = None,
) -> go.Figure:
    metrics = metrics or [m for m in STYLE_METRICS if m in df_full.columns]
    df_norm = _normalize_metrics(df_full, metrics)

    fig = go.Figure()

    def add_trace(name: str, color: str):
        row = df_norm[df_norm["player_name"] == name]
        if row.empty:
            return
        values = row[metrics].values.flatten().tolist()
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
