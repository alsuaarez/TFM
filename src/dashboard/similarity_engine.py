"""
Motor de similitud entre jugadores (PCA + distancia euclidiana).

Si ya tienes esta lógica construida en scouting/buscador_similitud.ipynb,
lo ideal es extraer esas funciones a un .py e importarlas aquí en vez de
duplicar la implementación. Esta versión es funcional standalone mientras
tanto.
"""

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from scipy.spatial.distance import cdist

from data_loader import STYLE_METRICS, TEAM_TO_PLAYER_METRIC_MAP


@st.cache_data
def compute_pca_profile(df: pd.DataFrame, n_components: int = 5):
    metrics_present = [m for m in STYLE_METRICS if m in df.columns]
    if len(metrics_present) < 2:
        raise ValueError(
            "No hay suficientes métricas de estilo presentes en los datos. "
            "Revisa STYLE_METRICS en data_loader.py."
        )

    X = df[metrics_present].fillna(df[metrics_present].median())
    X_scaled = StandardScaler().fit_transform(X)

    pca = PCA(n_components=min(n_components, len(metrics_present)))
    components = pca.fit_transform(X_scaled)

    out = df.copy()
    for i in range(components.shape[1]):
        out[f"pc_{i+1}"] = components[:, i]

    return out, pca


def compute_similarity_scores(
    df_with_pca: pd.DataFrame,
    target_player: str,
    same_position_family: bool = True,
    top_n: int = 15,
) -> pd.DataFrame:
    """
    Distancia euclidiana en el espacio de componentes principales.
    same_position_family=True aplica la corrección por familia de posición
    que identificaste en tu TFM (en vez de posición exacta).
    """
    pc_cols = [c for c in df_with_pca.columns if c.startswith("pc_")]

    target_row = df_with_pca[df_with_pca["player_name"] == target_player]
    if target_row.empty:
        raise ValueError(f"Jugador objetivo '{target_player}' no encontrado.")

    candidates = df_with_pca[df_with_pca["player_name"] != target_player].copy()

    if same_position_family and "position_family" in df_with_pca.columns:
        target_family = target_row.iloc[0]["position_family"]
        candidates = candidates[candidates["position_family"] == target_family]

    if candidates.empty:
        return candidates

    target_vector = target_row[pc_cols].values
    candidate_vectors = candidates[pc_cols].values

    distances = cdist(target_vector, candidate_vectors, metric="euclidean")[0]
    candidates["distance"] = distances

    max_dist = candidates["distance"].max() or 1
    candidates["similarity_score"] = (
        100 * (1 - candidates["distance"] / max_dist)
    ).round(1)

    candidates = candidates.sort_values("similarity_score", ascending=False)

    display_cols = [
        c
        for c in [
            "player_name",
            "team",
            "league",
            "position",
            "age",
            "market_value",
            "similarity_score",
        ]
        if c in candidates.columns
    ]

    return candidates[display_cols].head(top_n).reset_index(drop=True)


def compute_team_style_reference(
    team_stats_df: pd.DataFrame, team_name: str = "Las Palmas"
) -> pd.Series:
    """
    Reduce el fichero Team_Stats (una fila por partido) a un único vector
    de referencia: la media de cada métrica de estilo SOLO en los partidos
    del propio equipo (filtra las filas donde Team == team_name, que
    también incluyen las estadísticas del rival en cada partido).
    """
    own_matches = team_stats_df[team_stats_df["Team"] == team_name]
    if own_matches.empty:
        raise ValueError(
            f"No se encontraron filas con Team == '{team_name}' en Team_Stats."
        )

    metric_cols = list(TEAM_TO_PLAYER_METRIC_MAP.keys())
    metric_cols = [c for c in metric_cols if c in own_matches.columns]
    return own_matches[metric_cols].mean()


def compute_team_fit_scores(
    df_players: pd.DataFrame,
    team_reference: pd.Series,
    same_position_family: str | None = None,
    top_n: int = 20,
) -> pd.DataFrame:
    """
    Puntúa cada jugador por cercanía a un perfil de estilo de EQUIPO fijo
    (team_reference, viene de compute_team_style_reference()).

    Metodología: para cada métrica emparejada equipo->jugador
    (TEAM_TO_PLAYER_METRIC_MAP), estandarizamos la columna de jugadores
    con la media/desviación de la propia población de jugadores, y
    expresamos el valor objetivo del equipo en esa misma escala
    estandarizada. La distancia euclidiana en ese espacio compartido da
    el "encaje táctico" de cada jugador con el estilo del primer equipo.
    """
    df = df_players.copy()

    if same_position_family and "position_family" in df.columns:
        df = df[df["position_family"] == same_position_family]

    if df.empty:
        return df

    z_cols = []
    for team_metric, player_col in TEAM_TO_PLAYER_METRIC_MAP.items():
        if player_col not in df.columns or team_metric not in team_reference.index:
            continue
        mean, std = df[player_col].mean(), df[player_col].std()
        if std == 0 or pd.isna(std):
            continue
        z_col = f"z_{player_col}"
        df[z_col] = (df[player_col] - mean) / std
        target_z = (team_reference[team_metric] - mean) / std
        df[f"target_{z_col}"] = target_z
        z_cols.append(z_col)

    if not z_cols:
        raise ValueError(
            "Ninguna métrica de TEAM_TO_PLAYER_METRIC_MAP está presente en "
            "los datos de jugadores. Revisa los nombres de columna."
        )

    player_vectors = df[z_cols].fillna(0).values
    target_vector = np.array([df[f"target_{c}"].iloc[0] for c in z_cols]).reshape(1, -1)

    distances = cdist(target_vector, player_vectors, metric="euclidean")[0]
    df["team_fit_distance"] = distances

    max_dist = df["team_fit_distance"].max() or 1
    df["team_fit_score"] = (100 * (1 - df["team_fit_distance"] / max_dist)).round(1)

    df = df.sort_values("team_fit_score", ascending=False)

    display_cols = [
        c
        for c in [
            "player_name",
            "team",
            "position",
            "position_family",
            "age",
            "source",
            "team_fit_score",
        ]
        if c in df.columns
    ]
    return df[display_cols].head(top_n).reset_index(drop=True)
