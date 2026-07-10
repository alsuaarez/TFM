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

# Algunas ligas (ej. 1RFEF) se han exportado/traducido con nombres en español
# en vez de los nombres en inglés por defecto de Wyscout. Se homogeneizan
# aquí, igual que DICCIONARIO_COLUMNAS en los notebooks, para que ningún
# fichero se descarte en silencio solo por venir en otro idioma.
#
# IMPORTANTE: esto cubre las columnas de identidad (Player/Team/...) Y las
# de métricas (Defensive duels per 90, xA per 90...), que es justo lo que
# faltaba y causaba que varias métricas de POSITION_STYLE_PROFILES
# aparecieran como "sin variación real" (en realidad no faltaban, estaban
# en español y no se reconocían). Si detectas más columnas en español que no
# estén aquí, dime el nombre EXACTO tal como sale en tu Excel y lo añado.
COLUMN_ALIASES = {
    "Jugador": "Player",
    "Equipo": "Team",
    "Posicion": "Position", "Posición": "Position", "Posición específica": "Position",
    "Edad": "Age",
    "Valor de mercado": "Market value", "Valor_MEur": "Market value",
    "Vencimiento contrato": "Contract expires", "Fin_Contrato": "Contract expires",
    "Minutos jugados": "Minutes played", "Minutos": "Minutes played",
    "Pie": "Foot",

    # Métricas (mismos alias que DICCIONARIO_COLUMNAS en los notebooks)
    "Duelos_Defensivos_P90": "Defensive duels per 90", "Duelos defensivos/90": "Defensive duels per 90",
    "Interceptaciones_P90": "Interceptions per 90", "Interceptaciones/90": "Interceptions per 90",
    "Duelos_Aereos_P90": "Aerial duels per 90", "Duelos aéreos en los 90": "Aerial duels per 90",
    "Pases_Ultimo_Tercio_P90": "Passes to final third per 90", "Pases en el último tercio/90": "Passes to final third per 90",
    "Conducciones_Progresivas_P90": "Progressive runs per 90", "Carreras en progresión/90": "Progressive runs per 90",
    "Pases_Clave_P90": "Key passes per 90", "Jugadas claves/90": "Key passes per 90",
    "Regates_P90": "Dribbles per 90", "Regates/90": "Dribbles per 90",
    "Centros_P90": "Crosses per 90", "Centros/90": "Crosses per 90",
    "xA_P90": "xA per 90", "xA/90": "xA per 90",
    "Goles_P90": "Goals per 90", "Goles/90": "Goals per 90",
    "xG_P90": "xG per 90", "xG/90": "xG per 90",
    "Toques_Area_P90": "Touches in box per 90", "Toques en el área de penalti/90": "Touches in box per 90",
    "Remates_P90": "Shots per 90", "Remates/90": "Shots per 90",
    "Duelos_Ofensivos_P90": "Offensive duels per 90", "Duelos atacantes/90": "Offensive duels per 90",
    "Pases_Corto_Medio_P90": "Short / medium passes per 90",
    "Pases_Adelante_P90": "Forward passes per 90", "Pases hacia adelante/90": "Forward passes per 90",
    "Pases_Largos_P90": "Long passes per 90", "Pases largos/90": "Long passes per 90",
    "Goles_Encajados_P90": "Conceded goals per 90", "Goles encajados/90": "Conceded goals per 90",
    "Goles_Evitados_P90": "Prevented goals per 90", "Goles evitados/90": "Prevented goals per 90",
}

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

# Mapeo de posición -> familia. Distintas fuentes usan códigos Wyscout en
# inglés (CB, LCB...), abreviaturas en español (DFC, MCO...) o el nombre
# completo en español (Defensa central, Mediocentro...). Se listan aquí como
# sinónimos y se aplanan a un único diccionario alias->familia, para que
# "Central", "Defensa central", "DFC" y "CB" acaben todos en la misma
# familia "Central" en vez de aparecer como 4 categorías distintas.
#
# Nota sobre "DC": en tus datos significa "Delantero Centro", no "Defensa
# Central" (así lo confirmaste), por eso va en Delantero y no en Central.
POSITION_FAMILY_SYNONYMS = {
    "Portero": ["GK", "PT", "PORTERO"],
    "Lateral": ["LB", "RB", "LWB", "RWB", "LD", "RD", "LI", "RI",
                "LATERAL", "LATERAL DERECHO", "LATERAL IZQUIERDO"],
    "Central": ["CB", "LCB", "RCB", "LCB3", "RCB3", "DFC",
                "CENTRAL", "DEFENSA CENTRAL"],
    "Mediocentro defensivo": ["DMF", "LDMF", "RDMF", "MCD", "PIVOTE",
                              "MEDIOCENTRO DEFENSIVO"],
    "Mediocentro": ["CMF", "LCMF", "RCMF", "LCMF3", "RCMF3", "MC",
                     "CENTROCAMPISTA", "MEDIOCENTRO"],
    "Mediapunta": ["AMF", "LAMF", "RAMF", "MCO", "MEDIAPUNTA",
                    "MEDIOCENTRO OFENSIVO"],
    "Extremo": ["LW", "RW", "LWF", "RWF", "ED", "EI",
                "EXTREMO", "EXTREMO DERECHO", "EXTREMO IZQUIERDO"],
    "Delantero": ["CF", "SS", "DC", "DELANTERO", "DELANTERO CENTRO", "PUNTA"],
}

# Aplanado alias (en mayúsculas) -> familia canónica, para lookup directo.
POSITION_FAMILY_MAP = {
    alias.upper(): familia
    for familia, alias_list in POSITION_FAMILY_SYNONYMS.items()
    for alias in alias_list
}


def _normalize_foot(pie) -> str:
    """Unifica la lateralidad sin importar si viene en inglés o español
    (mismo criterio que normalizar_pie en los notebooks)."""
    pie_str = str(pie).lower().strip()
    if pie_str in ("right", "derecho"):
        return "diestro"
    if pie_str in ("left", "izquierdo"):
        return "zurdo"
    if pie_str in ("both", "ambidiestro"):
        return "ambidiestro"
    return "desconocido"


def _map_position_family(position_code: str) -> str:
    """Toma el primer código/nombre de posición (puede venir separado por
    comas si hay varias) y lo mapea a su familia canónica, sin importar si
    viene como código Wyscout (CB), abreviatura española (DFC) o nombre
    completo (Defensa central). Si no encuentra coincidencia exacta, prueba
    una coincidencia parcial (por si viene con matices, ej. "Central
    izquierdo"); si tampoco encaja, devuelve el texto tal cual en vez de
    fallar, para que datos nuevos no rompan la app."""
    if not isinstance(position_code, str) or not position_code.strip():
        return "Sin especificar"
    first_code = position_code.split(",")[0].strip().upper()

    if first_code in POSITION_FAMILY_MAP:
        return POSITION_FAMILY_MAP[first_code]

    # Fallback por coincidencia parcial, probando los alias más largos
    # primero para evitar falsos positivos con abreviaturas cortas.
    for alias in sorted(POSITION_FAMILY_MAP, key=len, reverse=True):
        if alias in first_code:
            return POSITION_FAMILY_MAP[alias]

    return first_code.title()


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

        raw = raw.rename(columns={k: v for k, v in COLUMN_ALIASES.items() if k in raw.columns})
        raw = raw.loc[:, ~raw.columns.duplicated()]  # ej. si un fichero trae 'Pie' Y 'Foot' a la vez

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


def _diagnose_source_files(folder: Path, source_label: str) -> list[dict]:
    """
    Igual que _load_player_files pero sin filtrar nada: recorre cada
    fichero encontrado en `folder` y explica qué se hizo con él (cargado
    como jugadores, cargado como Team_Stats, o descartado y por qué).
    Pensado para depurar casos como "1rfef no aparece": aquí verás el
    fichero, sus columnas reales, y el motivo exacto del descarte.
    """
    registros = []
    for f in _iter_data_files(folder):
        rel = f.relative_to(folder)
        try:
            raw = _read_any(f)
        except Exception as e:
            registros.append({
                "source": source_label, "archivo": str(rel),
                "estado": "ERROR AL LEER", "detalle": str(e), "columnas": "",
            })
            continue

        columnas_originales = list(raw.columns)
        raw = raw.rename(columns={k: v for k, v in COLUMN_ALIASES.items() if k in raw.columns})
        raw = raw.loc[:, ~raw.columns.duplicated()]
        alias_aplicado = list(raw.columns) != columnas_originales

        columnas_preview = ", ".join(str(c) for c in raw.columns[:8]) + (
            " ..." if len(raw.columns) > 8 else ""
        )

        if _is_player_file(raw):
            rel_parts = rel.parts[:-1]
            liga = "/".join(rel_parts) if rel_parts else source_label
            nota_alias = " (columnas traducidas vía COLUMN_ALIASES)" if alias_aplicado else ""
            registros.append({
                "source": source_label, "archivo": str(rel),
                "estado": "OK - cargado como jugadores",
                "detalle": f"liga='{liga}', {len(raw)} filas{nota_alias}",
                "columnas": columnas_preview,
            })
        elif _is_team_stats_file(raw):
            registros.append({
                "source": source_label, "archivo": str(rel),
                "estado": "OK - cargado como Team_Stats (no es tabla de jugadores)",
                "detalle": f"{len(raw)} filas", "columnas": columnas_preview,
            })
        else:
            registros.append({
                "source": source_label, "archivo": str(rel),
                "estado": "DESCARTADO",
                "detalle": "No tiene columna 'Player' (jugadores) ni 'Match'+'PPDA' (Team_Stats). "
                            "Revisa si el nombre de columna es distinto (ej. 'Jugador', espacios, "
                            "encoding) o si hay filas de cabecera antes de la fila real de títulos.",
                "columnas": columnas_preview,
            })
    return registros


@st.cache_data
def get_load_diagnostics() -> pd.DataFrame:
    """
    Diagnóstico completo de todas las fuentes (DATA_SOURCES): un registro
    por cada fichero encontrado, cargado o no, con el motivo. Úsalo en un
    expander del sidebar para ver de un vistazo por qué falta una liga.
    """
    registros = []
    for label, folder in DATA_SOURCES.items():
        if not folder.exists():
            registros.append({
                "source": label, "archivo": "(carpeta no existe)",
                "estado": "CARPETA NO ENCONTRADA", "detalle": str(folder), "columnas": "",
            })
            continue
        registros.extend(_diagnose_source_files(folder, label))
    return pd.DataFrame(registros)


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
    # .copy() desfragmenta el DataFrame: sin esto, las columnas nuevas que
    # se añaden a partir de aquí (position_family, foot...) sobre un
    # DataFrame ya "cosido" de varios concat generan el PerformanceWarning
    # de pandas por fragmentación interna.
    df = df.copy()

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
        "Foot": "foot",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    df = df.loc[:, ~df.columns.duplicated()]  # protección extra tras el rename final

    # Normalizar el pie (mismo criterio que normalizar_pie en los notebooks):
    # unifica 'right'/'derecho' -> 'diestro', etc. Si la columna no existe en
    # ningún fichero, el motor de similitud simplemente omite ese filtro.
    if "foot" in df.columns:
        df["foot"] = df["foot"].apply(_normalize_foot)

    # 'league' ya viene rellenada por _load_player_files a partir de la
    # carpeta; esto es solo un colchón por si algún frame la trajera vacía.
    if "league" not in df.columns:
        df["league"] = "Sin especificar"

    # Limpiar espacios sobrantes en nombre/equipo ANTES de deduplicar y de
    # cualquier búsqueda por nombre: "Mika Marmol " y "Mika Marmol" (o con
    # mayúsculas distintas en el equipo) se tratarían como jugadores
    # distintos y ni se deduplican ni se encuentran bien en las búsquedas.
    if "player_name" in df.columns:
        df["player_name"] = df["player_name"].astype(str).str.strip()
    if "team" in df.columns:
        df["team"] = df["team"].astype(str).str.strip()

    expected_after_rename = [rename_map.get(c, c) for c in REQUIRED_COLUMNS]
    missing = [c for c in expected_after_rename if c not in df.columns]
    if missing:
        st.warning(f"Columnas esperadas no encontradas en tus datos: {missing}")

    # Deduplicar: el mismo jugador puede aparecer en más de un fichero si tu
    # carpeta data/scout está organizada a la vez por posición (CENTRALES.xlsx)
    # y por liga (1rfef.xlsx) y ambas cubren a los mismos jugadores. Se
    # considera duplicado el mismo jugador+equipo dentro del mismo origen
    # (mercado/cantera/primer_equipo/seleccion); si aparece también en otro
    # origen distinto (ej. filial promocionado al primer equipo) se conserva,
    # porque ahí sí son dos situaciones reales distintas.
    clave_duplicado = [c for c in ["player_name", "team", "source"] if c in df.columns]
    if clave_duplicado:
        antes = len(df)
        df = df.drop_duplicates(subset=clave_duplicado, keep="first").reset_index(drop=True)
        eliminados = antes - len(df)
        if eliminados:
            st.info(
                f"Se han detectado y eliminado {eliminados} filas duplicadas "
                f"(mismo jugador + equipo + origen repetido en varios ficheros). "
                f"Total tras deduplicar: {len(df)} jugadores."
            )

    # Segunda pasada, SOLO para 'primer_equipo': el mismo jugador puede
    # aparecer con el nombre abreviado ("E. Loioidice") en un fichero y
    # completo ("Enzo Loioidice") en otro — no son duplicados exactos, así
    # que la deduplicación de arriba no los pilla. Como la plantilla del
    # primer equipo es pequeña y conocida (~25 jugadores), es seguro agrupar
    # por apellido + equipo aquí; en 'mercado' NO se hace esto porque con
    # miles de jugadores sí podría fusionar por error a dos personas
    # distintas con el mismo apellido.
    if "source" in df.columns and "player_name" in df.columns:
        es_primer_equipo = df["source"] == "primer_equipo"
        if es_primer_equipo.any():
            df_pe = df[es_primer_equipo].copy()
            df_resto = df[~es_primer_equipo]

            df_pe["_apellido"] = df_pe["player_name"].str.split().str[-1].str.lower()
            df_pe["_longitud_nombre"] = df_pe["player_name"].str.len()
            # keep="first" tras ordenar por longitud descendente -> se
            # conserva el nombre completo ("Enzo Loioidice") en vez del
            # abreviado ("E. Loioidice").
            antes_pe = len(df_pe)
            df_pe = df_pe.sort_values("_longitud_nombre", ascending=False)
            clave_pe = [c for c in ["team", "_apellido"] if c in df_pe.columns]
            df_pe = df_pe.drop_duplicates(subset=clave_pe, keep="first")
            eliminados_pe = antes_pe - len(df_pe)
            df_pe = df_pe.drop(columns=["_apellido", "_longitud_nombre"])

            df = pd.concat([df_resto, df_pe], ignore_index=True)
            if eliminados_pe:
                st.info(
                    f"Primer equipo: {eliminados_pe} jugador(es) aparecían con "
                    "nombre abreviado y completo a la vez; se ha conservado la "
                    "versión con el nombre completo."
                )

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
