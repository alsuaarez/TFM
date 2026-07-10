"""
Motor de similitud entre jugadores.

Migrado desde buscador_similitud.ipynb / comparador_estilo_plantilla.ipynb:
para cada familia de posición se usa un perfil de 5 métricas específicas
(POSITION_STYLE_PROFILES), z-score (StandardScaler) + similitud coseno, con
filtro opcional de pie dominante (con fallback si deja el grupo vacío).

Antes esta función usaba PCA genérico sobre las 20 métricas de STYLE_METRICS
para todas las posiciones a la vez, lo que mezclaba porteros con delanteros
antes incluso de filtrar por posición. Se sustituye para que el dashboard use
la misma metodología, ya validada, que el resto del TFM.
"""

import numpy as np
import pandas as pd
import streamlit as st
from scipy.spatial.distance import cdist
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from data_loader import STYLE_METRICS, TEAM_TO_PLAYER_METRIC_MAP

# Perfil de 5 métricas + pesos por cada position_family (mismas familias que
# devuelve POSITION_FAMILY_MAP en data_loader.py). Es el equivalente en
# columnas en inglés de PERFILES_OBJETIVO en los notebooks; la única
# diferencia es que aquí "Mediocentro" y "Mediocentro defensivo" van
# separados porque data_loader.py ya distingue esas dos familias.
POSITION_STYLE_PROFILES = {
    "Portero": {
        "metricas": ["Short / medium passes per 90", "Forward passes per 90",
                     "Long passes per 90", "Conceded goals per 90", "Prevented goals per 90"],
        "pesos": [0.15, 0.15, 0.15, 0.25, 0.30],
    },
    "Central": {
        "metricas": ["Defensive duels per 90", "Interceptions per 90", "Aerial duels per 90",
                     "Passes to final third per 90", "Progressive runs per 90"],
        "pesos": [0.30, 0.25, 0.20, 0.15, 0.10],
    },
    "Lateral": {
        "metricas": ["Progressive runs per 90", "Crosses per 90", "Passes to final third per 90",
                     "Defensive duels per 90", "Interceptions per 90"],
        "pesos": [0.25, 0.20, 0.25, 0.15, 0.15],
    },
    "Mediocentro defensivo": {
        "metricas": ["Defensive duels per 90", "Interceptions per 90", "Passes to final third per 90",
                     "Forward passes per 90", "Progressive runs per 90"],
        "pesos": [0.30, 0.25, 0.20, 0.15, 0.10],
    },
    "Mediocentro": {
        "metricas": ["Passes to final third per 90", "Forward passes per 90", "Defensive duels per 90",
                     "Interceptions per 90", "Progressive runs per 90"],
        "pesos": [0.30, 0.20, 0.25, 0.15, 0.10],
    },
    "Mediapunta": {
        "metricas": ["Passes to final third per 90", "Key passes per 90", "Progressive runs per 90",
                     "Dribbles per 90", "xA per 90"],
        "pesos": [0.30, 0.25, 0.20, 0.15, 0.10],
    },
    "Extremo": {
        "metricas": ["Dribbles per 90", "Progressive runs per 90", "Crosses per 90",
                     "xA per 90", "Touches in box per 90"],
        "pesos": [0.30, 0.25, 0.15, 0.15, 0.15],
    },
    "Delantero": {
        "metricas": ["Goals per 90", "xG per 90", "Touches in box per 90",
                     "Shots per 90", "Offensive duels per 90"],
        "pesos": [0.35, 0.25, 0.20, 0.10, 0.10],
    },
}


def compute_similarity_scores(
    df: pd.DataFrame,
    target_player: str,
    same_position_family: bool = True,
    top_n: int = 15,
) -> pd.DataFrame:
    """
    Similitud jugador-vs-jugador: z-score + coseno sobre el perfil de
    métricas de la familia de posición del jugador objetivo (en vez de PCA
    genérico). same_position_family=True aplica la corrección de filtrado
    por familia (en vez de código exacto) documentada en el TFM.
    """
    target_row = df[df["player_name"] == target_player]
    if target_row.empty:
        raise ValueError(f"Jugador objetivo '{target_player}' no encontrado.")
    target_row = target_row.iloc[0]

    target_family = target_row.get("position_family")
    perfil = POSITION_STYLE_PROFILES.get(target_family)
    metricas = perfil["metricas"] if perfil else STYLE_METRICS
    metricas = [m for m in metricas if m in df.columns]
    if len(metricas) < 2:
        raise ValueError(
            f"No hay suficientes métricas definidas para la familia '{target_family}'. "
            "Revisa POSITION_STYLE_PROFILES en similarity_engine.py."
        )

    candidates = df[df["player_name"] != target_player].copy()
    if same_position_family and "position_family" in df.columns:
        candidates = candidates[candidates["position_family"] == target_family]

    if candidates.empty:
        return candidates

    # Filtro de pie con fallback: si no hay candidatos con el mismo pie
    # dentro de esta familia de posición, se mantiene el grupo completo en
    # vez de devolver un resultado vacío (mismo criterio que en el notebook).
    if "foot" in df.columns and target_row.get("foot") not in (None, "desconocido"):
        mismo_pie = candidates[candidates["foot"] == target_row["foot"]]
        if not mismo_pie.empty:
            candidates = mismo_pie
        else:
            st.caption(
                f"Aviso: no hay candidatos con pie '{target_row['foot']}' en esta "
                "familia de posición; se amplía la búsqueda a todos los pies."
            )

    # Se rellenan los NaN de cada lado ANTES de concatenar (no después):
    # concatenar con columnas todo-NaN dispara un FutureWarning de pandas
    # y además distorsiona el StandardScaler si se hiciera al revés.
    metricas_candidatos = candidates[metricas].apply(pd.to_numeric, errors="coerce")
    medianas = metricas_candidatos.median()
    metricas_candidatos = metricas_candidatos.fillna(medianas).fillna(0)  # fillna(0): caso límite
    # en el que TODOS los candidatos de la familia tienen NaN en una métrica
    # (mediana también NaN); sin este último fillna, cosine_similarity falla.

    valor_target = pd.to_numeric(target_row[metricas], errors="coerce").fillna(medianas).fillna(0)

    # Descartar métricas sin variación real dentro de este grupo de
    # candidatos (columna que no existe con ese nombre exacto en tus datos
    # reales, o que queda a 0 para casi todos tras el fillna). Con muy pocas
    # métricas con varianza de verdad, la similitud coseno degenera y da
    # ~100% a todo el mundo — este filtro es lo que evita ese caso.
    desviaciones = metricas_candidatos.std()
    metricas_validas = [m for m in metricas if desviaciones.get(m, 0) > 1e-9]
    metricas_descartadas = [m for m in metricas if m not in metricas_validas]

    if metricas_descartadas:
        st.caption(
            f"Aviso: {len(metricas_descartadas)} métrica(s) del perfil de "
            f"'{target_family}' sin variación real en tus datos (revisa si el "
            f"nombre de columna coincide exactamente con tu export de Wyscout): "
            f"{metricas_descartadas}. Cálculo hecho solo con: {metricas_validas}."
        )

    if len(metricas_validas) < 2:
        raise ValueError(
            f"Solo quedan {len(metricas_validas)} métrica(s) con variación real "
            f"para la familia '{target_family}' — no es suficiente para calcular "
            f"una similitud fiable. Revisa los nombres de columna en "
            f"POSITION_STYLE_PROFILES contra tu export real de Wyscout."
        )

    metricas_candidatos = metricas_candidatos[metricas_validas]
    valor_target = valor_target[metricas_validas]

    X = pd.concat([valor_target.to_frame().T, metricas_candidatos], ignore_index=True)

    X_scaled = StandardScaler().fit_transform(X)
    similitudes = cosine_similarity(X_scaled[[0]], X_scaled)[0]

    candidates = candidates.reset_index(drop=True)
    candidates["similarity_score"] = (similitudes[1:] * 100).round(1)
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
