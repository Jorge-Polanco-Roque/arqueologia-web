# PLAN — Arqueología Web

Plan por fases del estudio sociológico diacrónico. Cada fase: **objetivo · método ·
herramientas · salida · riesgos · criterio de "hecho"**. La columna vertebral de las
fases 1–3 ya está construida y con self-checks; el resto es expansión.

Perspectiva triple que atraviesa todo:
- **Economista** — incentivos de plataforma, bienes de atención, externalidades,
  señales de estatus. ¿Cambió la "economía de la conversación"?
- **Sociólogo** — normas, identidad, capital social, polarización, deriva de temas.
- **Ingeniero de datos** — corpus reproducibles, esquema estable, muestreo honesto,
  controles de sesgo. Sin esto, lo anterior es opinión.

---

## Fase 0 — Fundamentos metodológicos  *(hacer ANTES de tocar datos)*

**Objetivo.** Fijar preguntas, hipótesis falsables y la estrategia de confusores.
Sin esto el proyecto produce gráficos bonitos sin poder de afirmación.

**Preguntas de investigación (draft).**
1. ¿Cambiaron los *temas de interés* entre eras dentro de una misma comunidad?
2. ¿Cambió la *perspectiva* (política/económica/filosófica) expresada?
3. ¿Cambió el *significado* de palabras clave (deriva semántica)?
4. ¿Cambió la *distribución de personalidades* (MBTI/Big Five) inferidas?
5. ¿Cuánto de (1–4) es **era** y cuánto es **quién está online** (población)?

**Hipótesis de ejemplo (falsables).**
- H1: la fracción de mensajes con marcadores políticos sube de early→modern *dentro
  de comunidades no políticas* (politización de lo cotidiano).
- H2: la longitud media y complejidad léxica por mensaje baja de early→modern.
- H3: la deriva semántica es mayor en términos tecnológicos que en términos morales.

**Estrategia de confusores (la parte crítica — ver CLAUDE.md).**
- Diseño primario = **within-platform over time** (comparación válida).
- Diseño secundario = between-platform con **reponderación** (fase 7), siempre
  etiquetado como confundido.
- Todo resultado se clasifica **descriptivo** vs **causal-tentativo**.

**Salida.** `docs/research_questions.md` con hipótesis, medidas y qué evidencia las
confirmaría/refutaría.
**Riesgo.** Saltarse esta fase → HARKing (hipótesis inventadas tras ver los datos).
**Hecho cuando.** Cada pregunta tiene una medida operacional y un test.

---

## Fase 1 — Ingesta multi-fuente  *(base construida)*

**Objetivo.** Normalizar cada fuente al esquema `Record` (`arqueo/core.py`).
**Método.** Una función por fuente que produce `Record`s → `write_jsonl`.
**Herramientas.** `arqueo/ingest.py`.
- [x] Usenet (mbox) — `from_usenet_mbox`
- [x] Reddit (ndjson/.gz/.zst) — `from_reddit_dump`
- [ ] Hacker News — BigQuery `bigquery-public-data.hacker_news` → ndjson → mismo lector.
- [ ] Web/foros antiguos — Wayback CDX API + `trafilatura` para extraer texto de HTML.
- [ ] Comunidades ES — Menéame API / scraping de foros; `lang="es"`.

**Diseño de emparejamiento (clave para validez).** Para cada tema, buscar la comunidad
más comparable en cada era: p.ej. `comp.lang.c` (Usenet, early) ↔ `r/C_Programming`
(Reddit, modern); `talk.politics` ↔ `r/politics`. Documentar los pares en
`docs/community_pairs.md` — son las unidades del contraste.

**Salida.** `data/normalized/<plataforma>/<archivo>.jsonl`.
**Riesgos.** (a) Dedup: Usenet cross-posting y reposts de Reddit. (b) Bots: filtrar
autores con firmas de bot en modern. (c) Codificación: texto antiguo en latin-1.
**Hecho cuando.** Los pares de comunidades están ingeridos y `compare` corre sobre ellos.

---

## Fase 2 — Almacenamiento y muestreo  *(base construida)*

**Objetivo.** Consultar millones de filas en portátil y muestrear sin sesgo.
**Herramientas.** `arqueo/core.py` (`db()`, `to_parquet()`).
- [x] Vista DuckDB `corpus` sobre glob de JSONL.
- [ ] **Muestreo estratificado** por (plataforma × comunidad × era × año) — no muestrear
  uniforme: modern tiene 1000× más volumen y aplastaría a early. Añadir
  `analyze.stratified_sample(con, per_cell=N)`.
- [ ] Tabla de **metadatos de corpus**: nº mensajes, autores únicos, rango temporal por
  celda. Es el denominador de todo porcentaje.

**Salida.** Muestras balanceadas reproducibles (semilla fija).
**Riesgo.** Comparar volúmenes crudos entre eras = medir el crecimiento de internet,
no el cambio de conducta. Siempre normalizar por nº de mensajes/autores.
**Hecho cuando.** Existe un sampler con celdas balanceadas y semilla.

---

## Fase 3 — Capa barata: temas y léxico a escala  *(base construida)*

**Objetivo.** Qué cambió en *de qué se habla*, sin coste ML.
**Herramientas.** `arqueo/analyze.py`.
- [x] **Fightin' Words** (`log_odds`) — términos que distinguen era A de B con z-score.
- [x] `compare_eras` sobre DuckDB con aviso de confusores.
- [ ] **Lexicones** contadores a escala: político (partidos, issues), económico (mercado,
  trabajo, cripto), filosófico (moral, sentido, religión). Fracción de mensajes que
  activa cada lexicón por era → serie temporal.
- [ ] Métricas de estilo: longitud, riqueza léxica (TTR), legibilidad, % preguntas,
  emojis/emoticonos (`:-)` early vs 😀 modern).

**Salida.** `reports/lexico_por_era.csv` + tablas de términos distintivos por par.
**Riesgo.** Los lexicones envejecen: "cloud" no significaba lo mismo en 2001. Cruzar
con fase 4 (deriva semántica) antes de interpretar.
**Hecho cuando.** Series por era de cada lexicón + top términos por par de comunidades.

---

## Fase 4 — Capa semántica: temas finos y deriva de significado

**Objetivo.** El corazón "arqueológico": cómo el *significado* cambió, no solo la
frecuencia.
**Método.**
- **BERTopic dinámico** sobre embeddings (`analyze.embed`) para temas emergentes y su
  peso por era — más fino que lexicones fijos.
- **Cambio semántico diacrónico** (`analyze.semantic_change`, método HistWords):
  word2vec por era + alineación Procrustes → distancia coseno de cada palabra entre eras.
  Palabras con mayor deriva = arqueología pura ("troll", "based", "meme", "friend",
  "cloud", "viral").
**Herramientas.** sentence-transformers, BERTopic, gensim (import perezoso, ya esbozado).
**Salida.** `reports/deriva_semantica.csv` (ranking de deriva) + mapas de temas por era.
**Riesgos.** (a) Vocabulario desalineado entre eras → filtrar a términos compartidos con
`min_count`. (b) Frecuencia baja infla el ruido del coseno → cortar por conteo.
**Hecho cuando.** Ranking de deriva estable bajo dos semillas + inspección manual de 20
palabras top confirma que el método captura cambios reales.

---

## Fase 5 — Perspectivas: política, económica, filosófica

**Objetivo.** Medir la *postura*, no solo el tema (híbrido: escala + LLM).
**Método (2 capas).**
- *Escala (barata):* clasificadores de sentimiento/stance (HF `cardiffnlp/*`) +
  lexicones morales (MFT — Moral Foundations) sobre todo el corpus.
- *Matiz (LLM):* Claude sobre **muestra estratificada** (~2–5k mensajes/celda) con rúbrica
  fija: eje económico izq/der, eje autoritario/libertario, marco filosófico dominante,
  optimismo/pesimismo tecnológico. Salida estructurada (JSON), 3 réplicas + voto para
  reducir varianza del juez.
**Herramientas.** `anthropic` SDK; nuevo `arqueo/perspective.py`.
**Salida.** `reports/perspectivas_por_era.csv` con IC bootstrap.
**Riesgos.** (a) El LLM tiene sesgo de época (entrenado en texto moderno) → validar contra
un set anotado a mano de 200 mensajes; reportar acuerdo (κ). (b) Coste → solo muestra,
nunca el corpus completo.
**Hecho cuando.** κ(humano, LLM) ≥ 0.6 en el set de validación y series con IC.

---

## Fase 6 — Personalidad: MBTI + Big Five

**Objetivo.** ¿Cambió la *distribución de personalidades* expresadas? (Lo que pediste —
el marco es **MBTI**, p.ej. ENTP.)
**Advertencia de rigor (en CLAUDE.md).** MBTI es psicométricamente débil; inferirlo de
texto lo es más. **Big Five (OCEAN) es la medida principal**; MBTI se reporta en paralelo
como el marco pedido. Ambos con incertidumbre explícita. Nunca se afirma la personalidad
de un individuo; solo la **distribución agregada** por era.
**Método.**
- *Escala:* clasificadores de rasgos a partir de texto (modelos Big Five basados en
  transformers; MBTI vía clasificador estilo dataset Kaggle MBTI, con su sesgo declarado).
- *Matiz:* Claude sobre muestra con rúbrica Big Five por faceta + mapeo aproximado a MBTI.
**Herramientas.** `arqueo/personality.py`.
**Salida.** `reports/personalidad_por_era.csv`: distribución de tipos/rasgos + test de
diferencia entre eras.
**Riesgos (grandes).** (a) Confusor de población domina aquí: un cambio en "extroversión"
puede ser solo que en early escribían más introvertidos técnicos. **Aplicar fase 7 SÍ o SÍ
antes de interpretar.** (b) Circularidad: si el clasificador aprende marcadores de época,
mide época, no personalidad. Validar con hold-out temporal.
**Hecho cuando.** Distribución por era con controles de población y una sección honesta de
"qué NO podemos concluir".

---

## Fase 7 — Comparación diacrónica y control de confusores

**Objetivo.** Separar **era** de **plataforma** y **población**. Es lo que convierte
descripción en (tentativa) inferencia.
**Método.**
- **Within-platform trends:** repetir todas las medidas dentro de una sola plataforma a lo
  largo del tiempo (Usenet early vs tardío; Reddit 2008→2023). Si la tendencia within
  coincide con la between, gana robustez.
- **Reponderación / post-estratificación:** reponderar la muestra early para igualar la
  composición modern en covariables observables (comunidad, actividad, proxies demográficos)
  con `statsmodels`. La diferencia que sobrevive a la reponderación es menos atribuible a
  "quién está online".
- **Placebo / negative controls:** medidas que NO deberían cambiar por era (p.ej. saludos)
  sirven de control; si "cambian", el pipeline tiene fugas.
**Herramientas.** `arqueo/compare.py`, scipy/statsmodels.
**Salida.** `reports/efecto_era_ajustado.md` — efecto crudo vs ajustado por medida.
**Riesgo.** Confusores no observados (nunca eliminables). Declararlos como límite duro.
**Hecho cuando.** Cada afirmación principal tiene efecto crudo + ajustado + control placebo.

---

## Fase 8 — Reporte y visualización

**Objetivo.** Contar la historia de forma reproducible.
**Método.** Notebooks + figuras estáticas (Plotly). Un informe por pregunta de la fase 0.
Estructura: pregunta → medida → gráfico within + between → efecto ajustado → interpretación
con sus límites.
**Salida.** `reports/informe.md` + figuras. Opcional: dashboard ligero (streamlit) si hay
público. *ponytail: no construir dashboard hasta que haya resultados que enseñar.*
**Hecho cuando.** Un lector reproduce cada figura desde los datos normalizados con un comando.

---

## Fase 9 — Validación y límites

**Objetivo.** Que el estudio sea creíble y honesto.
**Checklist.**
- Sesgo de supervivencia declarado por fuente.
- Sets de validación anotados a mano para cada clasificador (κ reportado).
- Análisis de sensibilidad: ¿los resultados aguantan otra definición de era? ¿otra muestra?
- Sección "amenazas a la validez" explícita (plataforma, población, anacronismo de modelos,
  MBTI débil).
- Reproducibilidad: semillas fijas, versiones de modelos ancladas, datos hasheados.
**Hecho cuando.** Un escéptico puede leer los límites y saber exactamente qué NO afirmamos.

---

## Orden de ataque sugerido (ruta corta primero)

1. Fase 0 (medio día de escritura, ahorra semanas).
2. Ingerir **un par de comunidades** (p.ej. `comp.lang.c` ↔ `r/C_Programming`).
3. Correr fase 3 (`compare`) — primer resultado real en horas.
4. Añadir fase 4 (deriva semántica) sobre ese par — el gancho "arqueológico".
5. Solo entonces escalar fuentes (HN, ES, Wayback) y subir a fases 5–7.

No construir 5–8 antes de que un par de comunidades dé señal en 3–4. YAGNI.
