# Sistema de Scouting Analítico — UD Las Palmas 26/27

Trabajo de Fin de Máster (TFM) en Big Data aplicado al scouting en fútbol. El proyecto construye un pipeline completo para la UD Las Palmas orientado a la toma de decisiones de fichajes y planificación de plantilla de cara a la temporada 2026/27, siguiendo la metodología **CRISP-DM** y usando datos de **Wyscout**.

El pipeline se compone de **8 notebooks de Jupyter** interconectados y un **dashboard interactivo en Streamlit** que traslada esa lógica analítica a una herramienta de consulta visual.

---

## Índice

1. [Objetivo del proyecto](#objetivo-del-proyecto)
2. [Metodología (CRISP-DM)](#metodología-crisp-dm)
3. [Estructura del repositorio](#estructura-del-repositorio)
4. [Estructura de datos esperada](#estructura-de-datos-esperada)
5. [Pipeline de notebooks](#pipeline-de-notebooks)
6. [Dashboard Streamlit](#dashboard-streamlit)
7. [Instalación y requisitos](#instalación-y-requisitos)
8. [Decisiones técnicas clave](#decisiones-técnicas-clave)
9. [Limitaciones conocidas](#limitaciones-conocidas)
10. [Autor](#autor)

---

## Objetivo del proyecto

Dotar al departamento de scouting de la UD Las Palmas de un sistema reproducible que permita:

- Construir y filtrar una **base de mercado global** de jugadores viables para fichar.
- Evaluar el **talento de la cantera** con criterios homologables al primer equipo.
- Cuantificar el **estilo de juego** del primer equipo a partir de sus estadísticas de partido.
- Identificar **jugadores estadísticamente similares** a un perfil objetivo.
- Anticipar el **impacto de las salidas** de jugadores en el rendimiento del equipo.
- Preparar y proyectar la **plantilla 26/27**.

Todo el análisis se apoya en archivos descargados de Wyscout, que llegan en distintos idiomas y formatos según la fuente (ligas, 1RFEF, sub-23, filial, primer equipo), lo cual condiciona buena parte de las decisiones técnicas del proyecto (ver [Decisiones técnicas clave](#decisiones-técnicas-clave)).

---

## Metodología (CRISP-DM)

La memoria está estructurada según las fases de CRISP-DM, cada una mapeada a uno o varios notebooks:

| Fase CRISP-DM | Notebook(s) asociado(s) |
|---|---|
| Comprensión del negocio | Introducción / contexto (sin notebook propio) |
| Comprensión y preparación de los datos | `mercado.ipynb`, `estilo.ipynb` |
| Modelado | `cantera.ipynb`, `buscador_similitud.ipynb`, `captaciones.ipynb` |
| Evaluación | `sustituciones.ipynb` |
| Despliegue | `preparacion_2627.ipynb` + dashboard Streamlit |

---

## Estructura del repositorio

```
TFM/
├── src/
│   ├── notebooks/
│   │   ├── mercado.ipynb                # Construcción de la base de mercado global
│   │   ├── cantera.ipynb                # Evaluación de la cantera / filial
│   │   ├── estilo.ipynb                 # Perfil de estilo de juego del primer equipo
│   │   ├── buscador_similitud.ipynb     # Buscador de perfiles similares a jugadores propios
│   │   ├── captaciones.ipynb            # Detección de necesidades y scoring de candidatos
│   │   ├── sustituciones.ipynb          # Impacto de las salidas de jugadores
│   │   └── preparacion_2627.ipynb       # Construcción de la plantilla proyectada 26/27
│   │
│   └── dashboard/
│       ├── app.py                       # Dashboard Streamlit 
│       ├── data_loader.py               # Carga, limpieza y normalización de datos
│       ├── similarity_engine.py         # Motor de similitud jugador-jugador y encaje de estilo
│       └── visualizations.py            # Gráficos
│
├── data/                                 # exports de Wyscout, ver estructura abajo
```

> El dashboard se ejecuta desde la raíz del repo: `streamlit run src/dashboard/app.py`.

---

## Estructura de datos esperada

Ninguno de los notebooks ni el dashboard incluye los datos. Ambos asumen la misma jerarquía de carpetas, relativa a la raíz del proyecto:

```
data/
├── laspalmasb/
│   ├── Las Palmas Atletico 25_26...xlsx
│   ├── scores_cantera_2627.csv
│   └── Team Stats Las Palmas Atlé...xlsx
│
├── scout/
│   ├── 1rfef/
│   ├── ligas/
│   ├── sub_23/
│   ├── mercado_viable_2627.csv
│   └── mercado.csv
│
├── seleccion/
│   └── top_opciones_mercado_26...csv
│
└── udlaspalmas/
    ├── df_bajas_2627.csv
    ├── df_impacto_bajas.csv
    ├── df_plantilla_2627.csv
    ├── Individual Las Palmas 2526...xlsx
    ├── perfil_estilo_udlp.csv
    ├── Team Stats Las Palmas 232...xlsx
    ├── Team Stats Las Palmas 242...xlsx
    └── Team Stats Las Palmas.xlsx
```

Los notebooks **producen** varios de estos ficheros intermedios, que después consumen otros notebooks o el propio dashboard. Es decir, el orden de ejecución importa (ver siguiente sección).

**Nota sobre idiomas de columnas**: las distintas fuentes de Wyscout exportan a veces en inglés y a veces en español (p. ej. 1RFEF). Tanto los notebooks (`DICCIONARIO_COLUMNAS`) como el dashboard (`COLUMN_ALIASES` en `data_loader.py`) traducen y homogeneizan estas columnas para que ningún fichero se descarte en silencio por venir en el idioma "equivocado".

---

## Pipeline de notebooks

Orden recomendado de ejecución:

### 1. `preparacion_2627.ipynb` — Plantilla 26/27
Parte de la situación contractual actual (25/26) y construye la plantilla proyectada 26/27: aplica opciones de compra ejercidas, renovaciones y salidas, y exporta la plantilla base resultante (`df_plantilla_2627.csv`), que es el punto de partida para `sustituciones.ipynb` y `captaciones.ipynb`.

### 2. `sustituciones.ipynb` — Salidas del equipo
Identifica qué jugadores no continúan en el club, cuantifica el volumen de rendimiento perdido y visualiza el impacto por perfil de posición. Exporta los ficheros de bajas e impacto que alimentan `captaciones.ipynb`.

### 3. `estilo.ipynb` — Estilo del equipo
Limpia los exports de estadísticas por partido (Team Stats) de varias temporadas, calcula un Análisis de Componentes Principales y construye un perfil de estilo ponderado del primer equipo, con seguimiento de su evolución temporada a temporada. Exporta `perfil_estilo_udlp.csv`.

### 4. `cantera.ipynb` — Análisis de cantera
Carga los datos del filial, aplica un motor de evaluación homologado con el primer equipo y genera visualizaciones radar para detectar talento con proyección.

### 5. `captaciones.ipynb` — Modelo de captaciones
A partir de las necesidades detectadas por posición, define perfiles estadísticos objetivo y una función de scoring aplicada a los candidatos de mercado. Incluye aplicaciones concretas (DFC, mediocentro ofensivo) con visualización radar y una tabla consolidada de necesidades.

### 6. `mercado.ipynb` — Base de mercado global
Construye la base de datos global de mercado a partir de las carpetas `1rfef`, `ligas` y `sub_23`. Aplica un filtro de viabilidad y permite búsqueda por posición.

### 7. `buscador_similitud.ipynb` — Buscador de perfiles similares
Dado un jugador del club, busca los perfiles de mercado más parecidos usando z-score + similitud coseno sobre un vector de métricas por 90 minutos. Incluye una sección de decisión final que combina el score de encaje de estilo con el % de clonación estadística para producir un ranking de fichajes recomendados.

> **Corrección aplicada**: el filtrado original comparaba por código exacto de posición Wyscout (p. ej. "LCB"), lo que dejaba fuera a jugadores con códigos ligeramente distintos y devolvía resultados vacíos en silencio. Se corrigió para agrupar por **familia de posición** (regex sobre variantes: LCB/RCB/CB → "Central", etc.), con un filtro de pie dominante que además tiene *fallback*: si no hay candidatos con el mismo pie, se amplía la búsqueda al grupo completo en vez de devolver cero resultados.

### 8. `comparador.ipynb` — Comparar jugadores
Dado un jugador se compara con otro para buscar diferencias y similitudes. El uso correspondiente se haría cuando se requiera hacer un fichaje.

---

## Dashboard Streamlit

El dashboard (`app.py`) traslada el buscador de similitud y el perfil de estilo a una herramienta interactiva:

- **Carga de datos** (`data_loader.py`): unifica mercado, cantera, primer equipo y selecciones en un único DataFrame, homogeneizando idioma de columnas, familia de posición y pie dominante. Incluye un panel de **diagnóstico de carga** para depurar qué ficheros se han leído/descartado y por qué.
- **Ficha de jugador**: datos básicos + radar de estilo, con opción de comparar contra cualquier jugador del primer equipo.
- **Pestaña "Jugadores similares"**: llama a `similarity_engine.compute_similarity_scores()`, con la opción de restringir por familia de posición.
- **Pestaña "Encaje con el estilo UD Las Palmas"**: calcula un ranking de encaje táctico de cualquier jugador contra el perfil medio de estilo del primer equipo.

### Ejecución

```bash
streamlit run src/dashboard/app.py
```

### Correspondencia notebook → módulo del dashboard

| Notebook | Módulo del dashboard |
|---|---|
| `mercado.ipynb` / `cantera.ipynb` | `data_loader.py` (carga y unificación) |
| `estilo.ipynb` | `similarity_engine.compute_team_style_reference/compute_team_fit_scores` |
| `buscador_similitud.ipynb` | `similarity_engine.compute_similarity_scores` |
| — | `visualizations.py` (radar y gráfico de barras) |

El motor de similitud del dashboard (`similarity_engine.py`) usa **la misma metodología validada en los notebooks** (z-score por familia de posición + similitud coseno + filtro de pie con fallback), sustituyendo una versión previa basada en PCA + distancia euclídea sobre todas las posiciones a la vez, que mezclaba porteros con delanteros antes de filtrar.

---

## Instalación y requisitos

```bash
pip install pandas numpy matplotlib seaborn scikit-learn scipy streamlit plotly openpyxl
```

- Python 3.10+
- Jupyter Notebook / JupyterLab para los notebooks de análisis
- Streamlit para el dashboard

---

## Decisiones técnicas clave

- **Filtrado por familia de posición, no por código exacto**: los códigos Wyscout (LCB, RCB, CB...) o abreviaturas en español (DFC, MCO...) se agrupan en familias canónicas (`POSICIONES_BUSQUEDA` / `GRUPOS_POSICION` en notebooks, `POSITION_FAMILY_SYNONYMS` en el dashboard). El matching exacto devolvía resultados vacíos.
- **Normalización dentro de la familia de posición**: tanto para el radar de estilo como para la similitud, el z-score/min-max se calcula dentro del grupo de posición, nunca sobre el universo mixto completo, de lo contrario los valores colapsan cerca de 0 o el score degenera a ~100% para todos los candidatos.
- **Coincidencia exacta de nombres de columna**: los perfiles de métricas por posición dependen de que el nombre de columna coincida literalmente con el export de Wyscout. Se añadió detección de métricas "sin variación real" para hacer visibles estos fallos en vez de que corrompan el score en silencio.
- **Deduplicación de columnas tras cada renombrado**: al aplicar el diccionario de traducción de columnas, ficheros que ya traían tanto el nombre original como el traducido generaban columnas duplicadas. Se aplica `.loc[:, ~df.columns.duplicated()]` inmediatamente después de cada operación de renombrado, no solo al final.
- **Deduplicación de jugadores por nombre abreviado vs. completo**: en el primer equipo, un mismo jugador puede aparecer como "E. Loioidice" en un fichero y "Enzo Loioidice" en otro. Al ser una plantilla pequeña y conocida, se agrupa por apellido + equipo y se conserva el nombre más largo. Esta estrategia **no** se aplica al universo de mercado, donde agrupar solo por apellido arriesgaría fusionar a dos personas distintas.
- **Filtro de pie con fallback**: si restringir por pie dominante deja el grupo de candidatos vacío, se amplía automáticamente la búsqueda a todos los pies en vez de devolver cero resultados.

---

## Limitaciones conocidas

- Los datos de Wyscout no se versionan en el repositorio; es necesario colocar los exports manualmente en la estructura de `data/` descrita arriba.
- El perfil de estilo de equipo depende de que el fichero `Team Stats` conserve exactamente las columnas `Match` y `PPDA` para poder identificarlo por contenido.
- La deduplicación por apellido en el primer equipo asume una plantilla pequeña; no es una estrategia generalizable a bases de datos de miles de jugadores.
- El scoring de fichajes (`Score_Global`) pondera a partes iguales encaje de estilo y % de clonación estadística (50/50); es un criterio configurable, no una calibración validada estadísticamente.

---

## Autor

Alberto — TFM Big Data aplicado al scouting de fútbol, UD Las Palmas, temporada 26/27.
