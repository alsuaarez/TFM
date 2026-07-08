"""
Carga de datos para el dashboard, apoyada en tu estructura real de /data.

Reparto asumido de carpetas:
    data/scout        -> base de mercado externo (candidatos a fichaje)
    data/laspalmasb    -> filial (cantera)
    data/udlaspalmas   -> primer equipo: contiene DOS tipos de fichero
                           distintos que NO deben mezclarse:
                             - "Individual_*.xlsx"  -> stats por jugador
                             - "Team_Stats_*.xlsx"   -> stats por partido
                                (usado solo para construir el perfil de
                                estilo objetivo del equipo, no es una
                                tabla de jugadores)
    data/seleccion     -> jugadores de selecciones (opcional)

Cada carpeta puede contener uno o varios ficheros de jugadores; se
concatenan todos los que empiecen por "Individual". Los ficheros
"Team_Stats" se cargan aparte con `load_team_match_stats()`.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

# TFM/src/dashboard/data_loader.py -> sube 2 niveles hasta TFM/
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

DATA_SOURCES = {
    "mercado": DATA_DIR / "scout",
    "cantera": DATA_DIR / "laspalmasb",
    "primer_equipo": DATA_DIR / "udlaspalmas",
    "seleccion": DATA_DIR / "seleccion",
}

# --- Columnas reales del export "Individual" de Wyscout --------------------
REQUIRED_COLUMNS = [
    "Player",
    "Team",
    "Position",
    "Age",
    "Market value",
    "Contract expires",
    "Minutes played",
]

# Subconjunto de las 115 columnas usado para el PCA de estilo jugador-vs-jugador.
# Ajusta/amplía libremente; están agrupadas por bloque para que sea fácil
# quitar o añadir por fase de juego.
STYLE_METRICS = [
    # Construcción / pase
    "Passes per 90",
    "Accurate passes, %",
    "Progressive passes per 90",
    "Accurate progressive passes, %",
    "Passes to final third per 90",
    "Accurate passes to final third, %",
    "Key passes per 90",
    "Through passes per 90",
    "Average pass length, m",
    # Ataque
    "xG per 90",
    "xA per 90",
    "Dribbles per 90",
    "Successful dribbles, %",
    "Touches in box per 90",
    "Progressive runs per 90",
    "Crosses per 90",
    # Defensa
    "Successful defensive actions per 90",
    "Defensive duels per 90",
    "Defensive duels won, %",
    "Interceptions per 90",
    "Aerial duels won, %",
]

# --- Mapeo de nombres de estilo de EQUIPO (Team_Stats) a su equivalente
# de jugador (Individual). Usado por compute_team_fit_scores() en
# similarity_engine.py. "Possession, %" y "PPDA" no tienen equivalente
# individual limpio, así que se dejan solo para contexto, no para el
# cálculo de encaje.
TEAM_TO_PLAYER_METRIC_MAP = {
    "Defensive duels won %": "Defensive duels won, %",
    "Lateral passes accurate %": "Accurate lateral passes, %",
    "Passes to final third accurate %": "Accurate passes to final third, %",
    "Progressive passes accurate %": "Accurate progressive passes, %",
    "Long pass %": "Accurate long passes, %",  # proxy aproximado, revisar
    "Average pass length": "Average pass length, m",
}

TEAM_CONTEXT_ONLY_METRICS = ["Possession, %", "PPDA"]

# Mapeo de códigos de posición de Wyscout a familias de posición.
# Esta es la corrección que documentas en tu TFM: filtrar por familia
# (p. ej. cualquier central) en vez de por código exacto (p. ej. "LCB"),
# que dejaba jugadores sin candidatos comparables.
POSITION_FAMILY_MAP = {
    "GK": "Portero",
    "CB": "Central", "LCB": "Central", "RCB": "Central", "LCB3": "Central", "RCB3": "Central",
    "LB": "Lateral", "RB": "Lateral", "LWB": "Lateral", "RWB": "Lateral",
    "DMF": "Mediocentro defensivo", "LDMF": "Mediocentro defensivo", "RDMF": "Mediocentro defensivo",
    "CMF": "Mediocentro", "LCMF": "Mediocentro", "RCMF": "Mediocentro", "LCMF3": "Mediocentro", "RCMF3": "Mediocentro",
    "AMF": "Mediapunta", "LAMF": "Mediapunta", "RAMF": "Mediapunta",
    "LW": "Extremo", "RW": "Extremo", "LWF": "Extremo", "RWF": "Extremo",
    "CF": "Delantero", "SS": "Delantero",
}


def _map_position_family(position_code: str) -> str:
    """Toma el primer código de posición (Wyscout separa varios con coma) y
    lo mapea a su familia. Si el código no está en el mapa, lo devuelve tal
    cual en vez de fallar, para que aparezcan datos nuevos sin romper la app."""
    if not isinstance(position_code, str) or not position_code.strip():
        return "Sin especificar"
    first_code = position_code.split(",")[0].strip()
    return POSITION_FAMILY_MAP.get(first_code, first_code)


# Tus ficheros de data/scout ya vienen pre-divididos por posición
# (CENTRALES.xlsx, LD.xlsx, MCO.xlsx...). Cuando el nombre del fichero
# coincide con esta lista, se usa como familia directamente — es más
# fiable que derivarla del código de Wyscout, porque ya la decidiste tú
# al organizar las carpetas.
FILENAME_POSITION_FAMILY = {
    "centrales": "Central",
    "centrocampistas": "Mediocentro",
    "delanteros": "Delantero",
    "extremos": "Extremo",
    "ld": "Lateral",
    "li": "Lateral",
    "mco": "Mediapunta",
    "porteros": "Portero",
}

# Nombres limpios, en el orden exacto en que Wyscout exporta el informe
# "Team Stats" (46 columnas fijas). Si tu export tiene otro orden o nº
# de columnas, esto lo detecta y avisa en vez de fallar en silencio.
TEAM_STATS_CLEAN_COLUMNS = [
    "Date", "Match", "Competition", "Duration", "Team", "Scheme", "xG",
    "Shots total", "Shots on target", "Shots on target %",
    "Possession, %",
    "Recoveries total", "Recoveries low", "Recoveries medium", "Recoveries high",
    "Shots outside box total", "Shots outside box on target", "Shots outside box on target %",
    "Positional attacks total", "Positional attacks with shots", "Positional attacks with shots %",
    "Counterattacks total", "Counterattacks with shots", "Counterattacks with shots %",
    "Touches in penalty area", "Conceded goals",
    "Shots against total", "Shots against on target", "Shots against on target %",
    "Defensive duels total", "Defensive duels won", "Defensive duels won %",
    "Fouls",
    "Lateral passes total", "Lateral passes accurate", "Lateral passes accurate %",
    "Passes to final third total", "Passes to final third accurate", "Passes to final third accurate %",
    "Progressive passes total", "Progressive passes accurate", "Progressive passes accurate %",
    "Average passes per possession", "Long pass %", "Average pass length", "PPDA",
]


def _read_any(path: Path) -> pd.DataFrame:
    if path.suffix == ".csv":
        return pd.read_csv(path)
    if path.suffix in (".parquet", ".pq"):
        return pd.read_parquet(path)
    if path.suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    raise ValueError(f"Formato no soportado: {path.suffix}")


def _iter_data_files(folder: Path) -> list[Path]:
    """Busca ficheros de datos en cualquier subcarpeta (recursivo), para
    que da igual cuántos niveles tengas (scout/1rfef/, scout/ligas/x/, etc.).
    Ignora los ficheros temporales de Excel (~$...)."""
    if not folder.exists():
        return []
    return [
        f
        for f in folder.rglob("*")
        if f.suffix in (".csv", ".parquet", ".pq", ".xlsx", ".xls")
        and not f.name.startswith("~$")
    ]


def _is_player_file(df: pd.DataFrame) -> bool:
    return "Player" in df.columns


def _is_team_stats_file(df: pd.DataFrame) -> bool:
    return "Match" in df.columns and "PPDA" in df.columns


def _load_player_files(folder: Path, source_label: str) -> pd.DataFrame:
    """
    Carga todos los ficheros de jugadores dentro de `folder`, sin importar
    su nombre ni en qué subcarpeta estén: se identifican por tener columna
    'Player' (los ficheros de Team_Stats se descartan automáticamente aquí
    porque no la tienen).

    La liga se deriva de las subcarpetas intermedias entre `folder` y el
    fichero: scout/1rfef/CENTRALES.xlsx -> liga "1rfef".
    Si el fichero está directamente en `folder` (sin subcarpeta, como en
    udlaspalmas), la liga toma el propio source_label.
    """
    frames = []
    for f in _iter_data_files(folder):
        try:
            raw = _read_any(f)
        except Exception as e:
            st.warning(f"No se pudo leer {f}: {e}")
            continue

        if not _is_player_file(raw):
            continue  # es Team_Stats u otro fichero no reconocido: se ignora aquí

        raw = raw.copy()
        raw["source"] = source_label

        rel_parts = f.relative_to(folder).parts[:-1]  # subcarpetas, sin el nombre de fichero
        raw["league"] = "/".join(rel_parts) if rel_parts else source_label

        stem_key = f.stem.strip().lower()
        if stem_key in FILENAME_POSITION_FAMILY:
            raw["_family_from_filename"] = FILENAME_POSITION_FAMILY[stem_key]

        frames.append(raw)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


@st.cache_data
def load_players() -> pd.DataFrame:
    """
    Carga y unifica jugadores de mercado + cantera + primer equipo (+ selección).
    Detecta ficheros de jugadores por contenido (columna 'Player'), no por
    nombre, así que da igual cómo los llames o en qué subcarpeta estén.
    """
    frames = [_load_player_files(folder, label) for label, folder in DATA_SOURCES.items()]
    frames = [f for f in frames if not f.empty]

    if not frames:
        st.error(
            "No se ha podido cargar ningún fichero de jugadores (con columna "
            "'Player'). Revisa las rutas en DATA_SOURCES dentro de data_loader.py."
        )
        st.stop()

    df = pd.concat(frames, ignore_index=True)

    # position_family: prioridad al nombre de fichero (scout ya viene
    # pre-clasificado por carpeta/fichero de posición); si no aplica, se
    # deriva del código de posición de Wyscout.
    derived_family = (
        df["Position"].apply(_map_position_family) if "Position" in df.columns else "Sin especificar"
    )
    if "_family_from_filename" in df.columns:
        df["position_family"] = df["_family_from_filename"].fillna(derived_family)
        df = df.drop(columns=["_family_from_filename"])
    else:
        df["position_family"] = derived_family

    # Alias en minúsculas/snake_case para las partes de app.py que ya
    # asumían nombres genéricos (player_name, team, age...).
    rename_map = {
        "Player": "player_name",
        "Team": "team",
        "Age": "age",
        "Minutes played": "minutes_played",
        "Market value": "market_value",
        "Contract expires": "contract_expiry",
        "Position": "position",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # 'league' ya viene rellenada por _load_player_files a partir de la
    # carpeta; esto es solo un colchón por si algún frame la trajera vacía.
    if "league" not in df.columns:
        df["league"] = "Sin especificar"

    expected_after_rename = [rename_map.get(c, c) for c in REQUIRED_COLUMNS]
    missing = [c for c in expected_after_rename if c not in df.columns]
    if missing:
        st.warning(f"Columnas esperadas no encontradas en tus datos: {missing}")

    return df


def _clean_team_stats(raw: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia el export 'Team Stats' de Wyscout: descarta las filas de
    cabecera-resumen y renombra las columnas 'Unnamed: X' a nombres
    legibles según el patrón fijo total/acertado/porcentaje.
    """
    if len(raw.columns) != len(TEAM_STATS_CLEAN_COLUMNS):
        st.warning(
            f"Un fichero de Team_Stats tiene {len(raw.columns)} columnas, se "
            f"esperaban {len(TEAM_STATS_CLEAN_COLUMNS)}. Revisa "
            "TEAM_STATS_CLEAN_COLUMNS en data_loader.py — puede que tu export "
            "tenga un formato distinto."
        )
        return raw

    df = raw.copy()
    df.columns = TEAM_STATS_CLEAN_COLUMNS
    df = df[df["Match"].notna()].reset_index(drop=True)
    return df


@st.cache_data
def load_team_match_stats() -> pd.DataFrame:
    """
    Busca y limpia el/los fichero(s) de estadísticas de equipo dentro de
    data/udlaspalmas, identificándolos por contenido (columnas 'Match' +
    'PPDA'), no por nombre de fichero.
    """
    folder = DATA_SOURCES["primer_equipo"]
    frames = []
    for f in _iter_data_files(folder):
        try:
            raw = _read_any(f)
        except Exception as e:
            st.warning(f"No se pudo leer {f}: {e}")
            continue
        if _is_team_stats_file(raw):
            frames.append(_clean_team_stats(raw))

    if not frames:
        st.warning(
            f"No se encontró ningún fichero de estadísticas de equipo "
            f"(con columnas 'Match'/'PPDA') en {folder}. Si ya lo tienes "
            "descargado, confirma que está copiado en esa carpeta."
        )
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def get_player_row(df: pd.DataFrame, player_name: str) -> pd.Series:
    match = df[df["player_name"] == player_name]
    if match.empty:
        raise ValueError(f"Jugador '{player_name}' no encontrado.")
    return match.iloc[0]


def filter_players(
    df: pd.DataFrame,
    league: str | None = None,
    position_family: str | None = None,
    source: str | None = None,
    max_age: int | None = None,
) -> pd.DataFrame:
    out = df.copy()
    if league and league != "Todas":
        out = out[out["league"] == league]
    if position_family and position_family != "Todas":
        out = out[out["position_family"] == position_family]
    if source and source != "Todos":
        out = out[out["source"] == source]
    if max_age:
        out = out[out["age"] <= max_age]
    return out
