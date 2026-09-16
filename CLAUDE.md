# Arqueología Web — estudio sociológico diacrónico de la internet

Estudio de cómo han cambiado las **interacciones humanas online** entre la web
temprana y la moderna: temas de interés, perspectivas (política, económica,
filosófica) y perfiles de personalidad. Perspectiva: **economista-sociólogo-
ingeniero de datos**. Inspiración: los "arqueólogos de internet".

## Parámetros del estudio (decididos)

| Eje | Decisión |
|-----|----------|
| Comparación | **Cortes decenales** (testigos de sondeo): 1992 · 2002 · 2012 · 2022. Híbrido por capas: 2012/2022 = within-platform limpio (Reddit+HN, causal-tentativo); 1992/2002 = pasado profundo (Usenet, capa descriptiva). Config en `core.SNAPSHOTS`. |
| Idioma foco | **Inglés** (máximos datos). Español = pista comparativa secundaria (campo `lang`). |
| Motor | **Híbrido**: NLP barato/local a escala + LLM (API) solo sobre muestras estratificadas para matiz. |
| Fuentes | Usenet (el "antes"), Reddit (el "después"), web/foros antiguos (Wayback), comunidades ES. HN como fuente limpia de refuerzo. |

## El confusor que define el rigor de todo (LÉEME)

Comparar **Usenet-1999 con Reddit-2020 NO mide "cómo cambiaron las personas"**.
Mezcla tres cosas inseparables si no se controlan:

1. **Plataforma** — Usenet ≠ Reddit en formato, moderación, incentivos.
2. **Población** — en 1999 estaban online académicos/técnicos/varones/occidentales;
   en 2020, todo el mundo. Un cambio de "ideología" o "personalidad" puede ser
   solo **quién está online**, no cómo piensa la gente.
3. **Era** — lo único que queremos aislar.

Reglas duras del proyecto:
- **Comparaciones válidas por defecto = dentro de la misma plataforma en el tiempo**
  (Usenet temprano vs tardío; Reddit 2008 vs 2023). El contraste entre plataformas
  se reporta **siempre etiquetado como confundido** y con `platform=` fijado.
- **Reponderación demográfica** cuando se compare entre plataformas (fase 7).
- **Anacronismo de modelos**: modelos NLP entrenados en texto moderno malinterpretan
  texto antiguo. El significado de las palabras cambia (ese cambio es *parte del objeto
  de estudio*, no ruido).
- **MBTI es psicométricamente débil**; inferirlo de texto lo es más. Se reporta
  **MBTI + Big Five (OCEAN)** en paralelo, con Big Five como medida principal y
  MBTI como el marco que pediste, ambos con incertidumbre explícita.

Si una salida del pipeline no puede separar estos confusores, se marca como
**descriptiva, no causal**. Nunca afirmamos "la gente cambió" cuando solo medimos
"el corpus cambió".

## Arquitectura

```
fuente cruda ──ingest──> JSONL normalizado ──DuckDB──> análisis ──> reporte
 (mbox, .zst)            data/normalized/<plat>/       (log-odds,
                         <Record por línea>            embeddings, LLM)
```

- **Unidad de análisis** = un mensaje/post (`Record`, ver `arqueo/core.py`). Es la
  única fuente de verdad del esquema; todo depende de ella.
- **Formato en disco** = JSONL (stdlib, cero deps para escribir). DuckDB lo consulta
  por glob. Parquet solo si el escaneo duele (`core.to_parquet`).
- **Almacén** = DuckDB sobre los JSONL. Sin servidor, SQL columnar, millones de filas
  en un portátil.
- **Motor híbrido**:
  - *Capa barata (sin deps ML)*: `analyze.log_odds` (Fightin' Words, Monroe et al.
    2008) — qué palabras/temas distinguen una era de otra. Es el caballo de batalla.
  - *Capa semántica (deps ML, import perezoso)*: embeddings (sentence-transformers),
    temas (BERTopic), **cambio semántico diacrónico** (word2vec por era + Procrustes,
    método HistWords) — el método "arqueológico" por excelencia.
  - *Capa matiz (LLM)*: Claude sobre muestras estratificadas para ideología,
    perspectiva y personalidad. Ver `PLAN.md` fases 5–6.

## Estructura del repo

```
CLAUDE.md            este archivo (charter + método)
PLAN.md              plan detallado por fases
requirements.txt     deps (núcleo vs ML opcional)
arqueo/
  core.py            esquema Record + eras + almacén DuckDB
  ingest.py          conectores: Usenet (mbox), Reddit (dumps .zst/.ndjson)
  analyze.py         comparación diacrónica (log-odds + hooks ML/LLM)
  cli.py             ata ingest -> store -> compare
data/                (gitignored) dumps crudos y JSONL normalizado
```

## Cómo correr

```bash
pip install -r requirements.txt              # duckdb basta para el núcleo

# 1. Ingesta (normaliza a data/normalized/<fuente>/<archivo>.jsonl)
python -m arqueo.cli ingest usenet dumps/comp.lang.c.mbox
python -m arqueo.cli ingest reddit dumps/programming_comments.zst

# 2. Comparación diacrónica DENTRO de una plataforma (válida)
python -m arqueo.cli compare --platform reddit --community programming

# Auto-tests de cada módulo (ponytail: cada uno trae su self-check)
python -m arqueo.core && python -m arqueo.ingest && python -m arqueo.analyze
```

## De dónde salen los datos (VERIFICADO 2026-09-16)

- **Reddit** ✅ FÁCIL. Pushshift restringido desde ~2023; el sucesor es **Arctic Shift**
  (arctic-shift.photon-reddit.com + GitHub ArthurHeitmann/arctic_shift). Cobertura
  ~2005-06 → feb-2026, ~2.5 B posts. Dos formatos: **Parquet en HuggingFace**
  (`open-index/arctic`, ~261 GB, DuckDB lo lee directo, sin ingester) y **.zst NDJSON**
  por subreddit (formato idéntico a Pushshift → compatible con `ingest.from_reddit_dump`).
  Espejo estable: **Academic Torrents** (colecciones de u/RaiderBDev, 2005-06→2025, ~3.4 TB;
  scripts en github.com/Watchful1/PushshiftDumps). Verificar ToS antes de publicar datos.
- **Hacker News** ✅ FÁCIL. `bigquery-public-data.hacker_news`, activo, completo desde 2006,
  actualizado a diario. Primer TB/mes gratis. Una sola comunidad → buen control within-platform.
- **Usenet** ⚠️ DIFÍCIL (ver nota estratégica). El **UTZOO Wiseman fue RETIRADO de
  archive.org en 2020** por demandas legales. **Google Groups es read-only desde
  feb-2024, sin descarga masiva.** Quedan: colecciones `usenet`, `usenet-ee`,
  `usenethistorical` en archive.org (completitud incierta) y visores web
  (UsenetArchives.com, Narkive, Newsgrouper) que sirven para *leer*, no para bulk.
  Adquisición oportunista y sucia, no un pipeline limpio.
- **Web/foros antiguos** ✅ MEDIO. Wayback **CDX API** (`web.archive.org/cdx/search/cdx?url=...
  &output=json&from=&to=`) da capturas por URL/fecha; extraer texto del HTML con `trafilatura`.
  Common Crawl solo si hace falta escala masiva.
- **Comunidades ES** ⚠️ MEDIO. Sin dumps oficiales limpios. Menéame: hay dataset en Zenodo
  (rec. 4243128, 2020) + scraping propio. ForoCoches: solo scraping (Apify/propio).

### Nota estratégica (cambia una premisa del diseño)

El "antes" NO tiene por qué ser Usenet. `early` = 1990–2007 y **Reddit llega a 2005-06 y HN
a 2006** → hay datos `early` *dentro de Reddit y de HN*. Eso permite el diseño primario
(within-platform: Reddit 2005-07 vs Reddit 2015+; HN 2006-08 vs HN 2020+) con fuentes
**limpias y masivas**, sin depender de la adquisición difícil de Usenet. **Usenet pasa a ser
el "pasado profundo" opcional (arqueología pura 1981–2000), no un requisito del contraste.**
Ruta recomendada: arrancar con Reddit+HN; sumar Usenet como bonus cuando haya señal.

## Ética y datos

- Autores = seudónimos. **Hashear `author` antes de publicar** cualquier dataset.
- Reportar sesgo de supervivencia: lo archivado ≠ representativo de su era.
- No re-identificar individuos. El objeto es el agregado, no la persona.

## Convenciones (ponytail activo)

- Añadir fuente = una función que produce `Record`s + reusar `core.write_jsonl`.
  No frameworks de plugins; copia el patrón de `ingest.py`.
- Lógica no trivial deja **un self-check ejecutable** (`_selfcheck()` bajo `__main__`).
- Deps ML se importan **dentro de la función**, no al top: el núcleo corre sin ellas.
- Toda comparación entre plataformas imprime el aviso de confusores. No se silencia.

## Estado

Columna vertebral funcional (esquema, ingesta Usenet+Reddit, almacén, log-odds
diacrónico) con self-checks. Capas semántica/LLM y fuentes restantes: pendientes,
detalladas en `PLAN.md`.
