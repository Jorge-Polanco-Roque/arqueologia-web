<div align="center">

# 🏺 Arqueología Web

**Un estudio sociológico diacrónico de cómo cambió la conversación en internet.**

*Excavando r/politics como quien lee estratos de sedimento: qué se decía, cómo se pensaba y cómo se expresaba la gente en 2012 frente a 2022.*

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-columnar-FFF000?logo=duckdb&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-aislado-2496ED?logo=docker&logoColor=white)
![Estadística](https://img.shields.io/badge/estad%C3%ADstica-z%20·%20Mann–Whitney%20·%20FDR-006BA2)
![UI](https://img.shields.io/badge/UI-offline%20·%20ECharts-E3120B)
![Núcleo](https://img.shields.io/badge/deps%20núcleo-stdlib%20%2B%20duckdb-59636b)

</div>

---

> [!NOTE]
> **Hallazgo principal (Q1 2012 vs Q1 2022, ~9.100 comentarios).** De 19 métricas contrastadas, **17 son significativas** tras corrección FDR — pero con **n≈9.000 la significancia es barata**. Al mirar el **tamaño de efecto**, solo **4** cambios son no triviales, y el único de magnitud media es *de quién* se habla (**Trump**, Cohen's *h*=0.53). Los cambios de estilo —más slang, más insultos, más encuadre tribal— son **reales y consistentes en dirección, pero de efecto pequeño-a-trivial**. La conclusión honesta: en esta muestra la diferencia grande y fiable es de **agenda**, no de **psicología**.

---

## 📖 Qué es esto

Un pipeline reproducible de **ingeniería de datos + lingüística computacional + inferencia estadística** que compara dos "cortes de sondeo" de una misma comunidad a lo largo del tiempo, y presenta los resultados en una **interfaz editorial** (estética *The Economist*) que funciona **100 % offline**.

El diseño está pensado desde tres miradas —**economista, sociólogo e ingeniero de datos**— con una obsesión transversal: **separar la señal del artefacto**. Cada afirmación se acompaña de su test, su tamaño de efecto y sus límites.

## 🧭 El pipeline

```
  DESCARGA            INGESTA               ALMACÉN            ANÁLISIS                    PRESENTACIÓN
 ─────────────      ────────────────      ─────────────      ───────────────────────     ──────────────────
  Reddit API    →    normalización    →    DuckDB        →    log-odds (Fightin' Words)    UI editorial
  (Arctic Shift)     a `Record`            sobre JSONL        léxicos LIWC · MFT           (report/ui.html)
  BigQuery (HN)      (JSONL, bots           por glob          densidades ‰ palabras        + batería estadística
  Usenet (mbox)       filtrados)                              z · Mann–Whitney · FDR       (tests + tamaño de efecto)
```

Todo el **núcleo** (esquema, ingesta, log-odds, métricas, estadística) corre con **la librería estándar de Python + DuckDB**. Las capas pesadas (embeddings, LLM) son opcionales y se importan de forma perezosa.

## ✨ Características

- **Descarga estratificada y reproducible** desde la API pública de Arctic Shift (Reddit) y BigQuery (Hacker News), con reintentos y muestreo mensual para evitar sesgos temporales.
- **Esquema único** (`Record`) al que se normaliza cualquier fuente → todo el análisis es agnóstico del origen.
- **Análisis lingüístico** — término distintivo por **log-odds con prior de Dirichlet** (Monroe et al.), léxicos temáticos, de valores, emocionales y de estilo tipo **LIWC**, **Moral Foundations** (Haidt et al.), pronombres, complejidad, legibilidad Flesch y polarización.
- **Perfil psicológico** con proxies léxicos (Big Five, procesamiento cognitivo) **normalizados por mil palabras** para neutralizar el confusor de longitud.
- **Inferencia estadística profesional en Python puro**: z de dos proporciones (Cohen's *h*), Mann–Whitney U con corrección por empates (Cliff's δ) y **Benjamini–Hochberg (FDR)** — con veredicto guiado por **tamaño de efecto**, no por *p*.
- **UI editorial offline** — un solo HTML autocontenido, ECharts vendorizado (sin CDN, sin dependencia de terceros), tipografía y paleta *The Economist*, navegación por estratos y sección de metodología.
- **Aislamiento total** vía Docker: descarga, análisis y visualización sin tocar tu Python del sistema.

## 🚀 Inicio rápido

### Con Docker (recomendado)

```bash
docker compose build
docker compose up                                  # corre los self-checks + smoke test

# descargar (muestreo estratificado por mes) y comparar
docker compose run --rm arqueo python -m arqueo.cli download reddit --subreddit politics --year 2012 --per-month 2000
docker compose run --rm arqueo python -m arqueo.cli download reddit --subreddit politics --year 2022 --per-month 2000
docker compose run --rm arqueo python -m arqueo.cli ingest  reddit data/raw/reddit/politics_2012_comments.ndjson
docker compose run --rm arqueo python -m arqueo.cli ingest  reddit data/raw/reddit/politics_2022_comments.ndjson
docker compose run --rm arqueo python -m arqueo.cli ui                       # -> data/ui.html
```

### En local

```bash
pip install -r requirements-core.txt        # duckdb + zstandard bastan para el núcleo
python -m arqueo.cli ui                      # genera data/ui.html
python -m arqueo.sig                         # imprime la batería estadística
open data/ui.html
```

### Verificación

```bash
python -m arqueo.core && python -m arqueo.ingest && python -m arqueo.analyze \
  && python -m arqueo.deep && python -m arqueo.stats && python -m arqueo.smoke
```

## 🧩 Módulos

| Módulo | Responsabilidad |
|---|---|
| `core.py` | Esquema `Record`, cortes temporales, almacén DuckDB sobre JSONL |
| `ingest.py` | Conectores → `Record`: Usenet (mbox), Reddit (.zst/.ndjson), Hacker News |
| `download_reddit.py` | Descarga vía API Arctic Shift (stdlib), muestreo mensual estratificado |
| `download_hn.py` | Descarga de Hacker News desde BigQuery |
| `analyze.py` | Comparación diacrónica: log-odds (Fightin' Words) con prior de Dirichlet |
| `deep.py` | Léxicos temáticos/psicológicos/de estilo + legibilidad, tiempo verbal, polarización |
| `stats.py` | Tests en Python puro: proporciones, Mann–Whitney, Cohen's *h*, Cliff's δ, FDR |
| `sig.py` | Batería de contrastes 2012 vs 2022 con corrección por comparaciones múltiples |
| `ui.py` | Interfaz editorial (ECharts vendorizado, estética *The Economist*) |
| `dashboard.py` / `report.py` | Vistas HTML alternativas (rápida y profunda) |
| `cli.py` | Punto de entrada: `download · ingest · compare · dashboard · report · ui` |
| `smoke.py` | Test end-to-end (ingesta → DuckDB → comparación) |

## 🔬 Metodología y rigor

- **Diseño**: cortes de sondeo (una comunidad a lo largo del tiempo) para aislar el efecto **época**, minimizando el confusor de plataforma.
- **Limpieza**: exclusión de bots y avisos de moderación; densidades normalizadas **por mil palabras** para que las comparaciones no dependan de la longitud del comentario.
- **Honestidad estadística**: con *n* grande casi todo es significativo; el proyecto **lidera con el tamaño de efecto** y aplica **corrección FDR**. Nada se afirma como "grande" solo por su *p*.
- **Trazabilidad**: cada módulo trae un `self-check` ejecutable; los resultados se reproducen con un comando.

## ⚠️ Límites (leer antes de citar)

- **Descriptivo, no causal.** Una sola comunidad y, por ahora, solo el primer trimestre de cada año.
- Comparar 2012 con 2022 mezcla **época** con **quién estaba online** (composición de la población) y con la **agenda noticiosa** del momento.
- Los léxicos son **ilustrativos**; el "Big Five" es un **proxy léxico**, no un instrumento psicométrico validado.
- Los datos crudos y las visualizaciones generadas **no se versionan** (`data/` está en `.gitignore`); se reconstruyen desde el pipeline.

## 🗺️ Hoja de ruta

- [ ] Descarga del **año completo** (potencia estadística sobre las 30+ figuras).
- [ ] Múltiples comunidades y **reponderación demográfica** (fase 7 del `PLAN.md`).
- [ ] Capa semántica: BERTopic dinámico y cambio de significado diacrónico (HistWords).
- [ ] Capa de matiz por **LLM** sobre muestras estratificadas (ideología, personalidad).
- [ ] Estrato profundo de **Usenet** (1992 · 2002) como "pasado profundo".

## 📚 Referencias

- Monroe, Colaresi & Quinn (2008), *Fightin' Words* — comparación léxica con prior de Dirichlet.
- Graham, Haidt et al. — *Moral Foundations Theory*.
- Pennebaker et al. — *LIWC* (categorías psicolingüísticas).
- Benjamini & Hochberg (1995) — control del *False Discovery Rate*.

---

<div align="center">
<sub>Proyecto de investigación privado · datos de fuentes públicas usados con fines analíticos · seudónimos hasheables antes de cualquier publicación.</sub>
</div>
