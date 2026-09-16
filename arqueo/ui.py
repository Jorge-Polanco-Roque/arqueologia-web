"""UI editorial standalone con navegación por estratos (pestañas).

Pieza de investigación en papel ("Arqueología Web"). Secciones = estratos (pestañas);
gráficos = figuras numeradas con pie. Color como tesis: 2012 teal (pasado frío),
2022 terracota (presente cálido). Los léxicos de estilo/psicológicos van normalizados
por mil palabras (robustos a la longitud). Cuantitativo sobre el corpus (bots filtrados);
cualitativo sobre una muestra 20+20 leída a mano.

    python -m arqueo.ui            # -> data/ui.html
"""
from __future__ import annotations
import json
import os
import re

from .analyze import log_odds
from .dashboard import load, by_era, style, LEXICONS
from .report import concentration, interaction, pronouns, markers, month_hist, bigrams, MFT
from .deep import (group_pct, group_rate, pair, complexity, tense, formatting, top_terms,
                   trigrams, readability, lexdiv, hour_hist, length_buckets, polarization,
                   TOPICS, ENTITIES, COGNITION, EXPRESSION, VALUES, AFFECT, EMOTION, COGPROC, BIG5)
from .sig import battery

C12, C22 = "#006BA2", "#E3120B"   # azul / rojo Economist

BOT_AUTHORS = {"AutoModerator", "autotldr", "politicsmoderatorbot", "totesmessenger"}
BOT_MARK = re.compile(r"i am a bot|please contact|message compose|has been removed|"
                      r"your (comment|submission)|moderators of|beep boop", re.I)


def humans(rows):
    return [r for r in rows if r["author"] not in BOT_AUTHORS and not BOT_MARK.search(r["text"])]


QUAL_SCORES = {
    "cats": ["Deliberación", "Cita fuentes", "Profundidad", "Slang/informal",
             "Encuadre tribal", "Humor/ironía", "Afecto", "Civismo"],
    "2012": [8, 7, 8, 3, 4, 3, 5, 7], "2022": [5, 3, 6, 8, 8, 7, 8, 4],
}
QUOTES = {
    "2012": [
        ("khalilzad95", "Alfabetización legal", "The signing statement is Obama saying he will not enforce the law as Congress intended… TLDR: him promising not to enforce large parts of it."),
        ("cpolito87", "Cita jurisprudencia", "Almost every state has a 'single subject' provision… See People v. Dunigan… Dague v. Piper Aircraft."),
        ("nornerator", "Libertades civiles", "Nobody should ever be detained without trial!!! All people charged with a crime should be put on trial."),
        ("mjolle", "Civismo", "Thanks a lot for taking the time to write this post… how have you come across such knowledge, and where are you from?"),
    ],
    "2022": [
        ("stumblios", "Sátira tribal", "Republicans are Christians and Democrats are evil atheists… put an R by your name and be incapable of feeling shame."),
        ("BeTheDiaperChange", "Identidad/afecto", "AOC called out the Right and their incel behavior… these entitled man-babies… It is how we ended up in this mess."),
        ("cbr388", "Meme/humor", "You know, the Drizzle… bitten by a thirsty worm in a lab accident… he was able to manipulate the rain, and THAT is FRESH."),
        ("jayicon97", "Dunk/slang", "Nah thanks. I'll keep my foreign, while you ride around in some ugly shit box. Can't afford gas? Sounds like a you problem tbh."),
        ("Michigander_from_Oz", "Contraejemplo profundo", "The 'No Surprise Billing' rules… the arbiter presumes the insurance company's rate is correct, and the physician must prove otherwise…"),
    ],
}
LEAD = ("En una década, r/politics deja de ser un <em>foro deliberativo</em> —citar leyes, "
        "conceder puntos, discutir el debido proceso— y se vuelve un <em>muro expresivo</em>: "
        "dunk, ironía, identidad, moral tribal, slang y afecto. Lo que sigue es esa transición, "
        "leída en nueve estratos: de <strong>argumentar para convencer</strong> a "
        "<strong>expresar para pertenecer</strong>.")
METHOD = (
    "<h3>Datos</h3><p>Comentarios de <code>r/politics</code> descargados de la API pública de "
    "Arctic Shift (sucesor de Pushshift). Dos cortes: primer trimestre de 2012 y de 2022, con "
    "muestreo mensual estratificado. Tras filtrar bots y avisos de moderación quedan 3.772 "
    "comentarios en 2012 y 5.333 en 2022.</p>"
    "<h3>Preprocesamiento</h3><ul>"
    "<li>Normalización a un esquema común; limpieza de citas y firmas.</li>"
    "<li>Exclusión de autores bot (AutoModerator, etc.) y de plantillas de moderación.</li>"
    "<li>Tokenización con y sin palabras vacías según la métrica.</li></ul>"
    "<h3>Análisis descriptivo</h3><ul>"
    "<li><b>Léxico distintivo</b>: log-odds con prior de Dirichlet (Monroe et al., «Fightin' Words»).</li>"
    "<li><b>Temas, valores, emociones y rasgos</b>: léxicos ilustrativos estilo LIWC y Moral Foundations (Haidt et al.).</li>"
    "<li><b>Densidades</b> (slang, insultos, pronombres…): normalizadas <b>por mil palabras</b> para neutralizar la longitud.</li></ul>"
    "<h3>Inferencia estadística</h3><ul>"
    "<li>Proporciones: <b>z de dos proporciones</b> con IC 95% y tamaño de efecto <b>Cohen's h</b>.</li>"
    "<li>Continuas: <b>Mann-Whitney U</b> (aprox. normal, corrección por empates) y <b>Cliff's δ</b>.</li>"
    "<li>Comparaciones múltiples: corrección <b>Benjamini-Hochberg (FDR)</b>.</li>"
    "<li>Con n≈9.000 casi todo sale significativo: el veredicto lo decide el <b>tamaño de efecto</b>.</li></ul>"
    "<h3>Límites</h3><ul>"
    "<li>Una sola comunidad y solo el primer trimestre: <b>descriptivo, no causal</b>.</li>"
    "<li>Confusores no controlados: plataforma, composición de la población y agenda noticiosa.</li>"
    "<li>Léxicos ilustrativos; el «Big Five» es un <b>proxy léxico</b>, no un instrumento validado.</li>"
    "<li>Comparar 2012 vs 2022 mezcla <i>época</i> con <i>quién estaba online</i>.</li></ul>")


def build(glob_pat="data/normalized/**/*.jsonl", out="data/ui.html"):
    rows = load(glob_pat)
    if not rows:
        raise SystemExit("No hay JSONL normalizado. Corre 'ingest' primero.")
    eras = {e: humans(r) for e, r in by_era(rows).items()}
    ks = list(eras)
    a, b = ks[0], ks[-1]
    ra, rb = eras[a], eras[b]

    def famv(F, topn=None, rate=False):
        fn = group_rate if rate else group_pct
        A, B = fn(ra, F), fn(rb, F)
        cats = list(F)
        if topn:
            cats = sorted(cats, key=lambda k: max(A[k], B[k]), reverse=True)[:topn]
        return {"cats": cats, "a": [A[k] for k in cats], "b": [B[k] for k in cats]}

    def lo(tok):
        r = log_odds([x["text"] for x in ra], [x["text"] for x in rb], top=12, tok=tok)
        return {"a": r["a_distinctive"], "b": r["b_distinctive"]}

    sa, sb = style(ra), style(rb)
    ma, mb = markers(ra), markers(rb)
    reg = {"cats": ["Hedging", "Modales", "Soez", "% preguntas", "% MAYÚS"],
           "a": [ma["% con matización (hedging)"], ma["% con deber/necesidad (modales)"],
                 ma["% con lenguaje soez"], sa["% preguntas"], sa["% grita (MAYÚS)"]],
           "b": [mb["% con matización (hedging)"], mb["% con deber/necesidad (modales)"],
                 mb["% con lenguaje soez"], sb["% preguntas"], sb["% grita (MAYÚS)"]]}
    expr = famv(EXPRESSION, rate=True)
    CRISPA = {"insultos": EXPRESSION["insultos"], "profanidad": EXPRESSION["profanidad"], "absolutismo": COGPROC["absolutismo"]}

    P = lambda **k: k
    sections = [
        {"title": "De qué se hablaba", "panels": [
            P(id="terms", kind="tornado", title="El vocabulario que separa las épocas",
              desc=f"Log-odds (z-score). Hacia {a} en teal; hacia {b} en terracota.", h=380,
              uni=lo(None), bi=lo(bigrams), tri=lo(trigrams)),
            P(id="topics", kind="barh", unit="%", title="Temas: qué asuntos se tocaban",
              desc="% de comentarios que activan cada tema (léxicos ilustrativos).", **famv(TOPICS)),
            P(id="entities", kind="barh", unit="%", title="¿De quién se hablaba?",
              desc="% que menciona a cada figura pública (top 12).", **famv(ENTITIES, topn=12)),
        ]},
        {"title": "Conceptos predominantes", "panels": [
            P(id="top12", kind="rank", color=C12, h=360, title=f"Lo que dominaba en {a}",
              desc="Palabras de contenido más frecuentes (sin palabras vacías).", items=top_terms(ra, 16)),
            P(id="top22", kind="rank", color=C22, h=360, title=f"Lo que dominaba en {b}",
              desc="Palabras de contenido más frecuentes (sin palabras vacías).", items=top_terms(rb, 16)),
        ]},
        {"title": "Cómo pensaban", "panels": [
            P(id="cognition", kind="radar", title="Estilo cognitivo (por mil palabras)",
              desc="Razonamiento y evidencia frente a certeza absoluta y duda.", **famv(COGNITION, rate=True)),
            P(id="complexity", kind="barh", title="Complejidad del texto",
              desc="Palabra larga, longitud de frase y subordinación (comas).", **pair(complexity(ra), complexity(rb))),
            P(id="readability", kind="barh", title="Legibilidad (Flesch)",
              desc="Facilidad de lectura: mayor = más fácil. Con sus componentes.", **pair(readability(ra), readability(rb))),
            P(id="tense", kind="barh", title="Orientación temporal",
              desc="Palabras de pasado frente a futuro (por mil).", **pair(tense(ra), tense(rb))),
        ]},
        {"title": "Perfil psicológico", "panels": [
            P(id="emotion", kind="barh", title="Emociones expresadas (por mil palabras)",
              desc="Densidad de carga emocional, estilo LIWC. Normalizado por longitud.", **famv(EMOTION, rate=True)),
            P(id="big5", kind="radar", title="Big Five (proxy léxico, por mil palabras)",
              desc="Marcadores correlacionados; aproximado, no es instrumento validado.", **famv(BIG5, rate=True)),
            P(id="cogproc", kind="radar", title="Procesamiento cognitivo (por mil palabras)",
              desc="Insight, causación, tentativo, diferenciación y absolutismo.", **famv(COGPROC, rate=True)),
        ]},
        {"title": "Cómo se expresaban", "panels": [
            P(id="expr", kind="radar", title="Registro expresivo (por mil palabras)",
              desc="Slang, insultos, ironía y profanidad.", **expr),
            P(id="reg", kind="barh", unit="%", title="Marcadores de registro",
              desc="Matización, deber, lenguaje soez, preguntas y gritos.", **reg),
            P(id="lexdiv", kind="barh", title="Diversidad léxica",
              desc="TTR medio por comentario y rareza de vocabulario (hapax).", **pair(lexdiv(ra), lexdiv(rb))),
            P(id="format", kind="barh", title="Forma y formato",
              desc="Negrita, enlaces, TL;DR/EDIT, exclamación y emoji.", **pair(formatting(ra), formatting(rb))),
        ]},
        {"title": "Valores e identidad", "panels": [
            P(id="mft", kind="radar", title="Fundamentos morales",
              desc="Intuiciones morales invocadas (marco de Haidt et al.).", **famv(MFT)),
            P(id="values", kind="barh", unit="%", title="Valores invocados",
              desc="Libertad, seguridad, igualdad, tradición, progreso, nación.", **famv(VALUES)),
            P(id="pron", kind="barh", title="Pronombres y encuadre",
              desc="Por mil palabras. yo → individual; nosotros/ellos → endogrupo/exogrupo.", **pair(pronouns(ra), pronouns(rb))),
            P(id="affect", kind="barh", unit="%", title="Optimismo frente a pesimismo",
              desc="Afecto colectivo hacia el futuro.", **famv(AFFECT)),
            P(id="persp", kind="barh", unit="%", title="Perspectiva temática",
              desc="Político, económico, filosófico.", **famv(LEXICONS)),
        ]},
        {"title": "Polarización y crispación", "panels": [
            P(id="pol", kind="barh", title="Encuadre nosotros / ellos",
              desc="Densidad de exogrupo/endogrupo (por mil) y % de exogrupo dentro del par.", **pair(polarization(ra), polarization(rb))),
            P(id="crispa", kind="barh", title="Crispación (por mil palabras)",
              desc="Insultos, profanidad y lenguaje absolutista ('all/never/everyone').", **famv(CRISPA, rate=True)),
        ]},
        {"title": "Interacción y estructura", "panels": [
            P(id="inter", kind="stack", title="¿Reacción o conversación?",
              desc="Comenta el post (t3) frente a responde a otro usuario (t1).",
              segs=["comenta el post", "responde a otro"],
              rows=[{"name": a, "vals": [interaction(ra)["% comenta el post (t3)"], interaction(ra)["% responde a otro (t1)"]]},
                    {"name": b, "vals": [interaction(rb)["% comenta el post (t3)"], interaction(rb)["% responde a otro (t1)"]]}]),
            P(id="length", kind="barh", unit="%", title="Distribución de longitud",
              desc="% de comentarios por tramo de palabras.", **pair(length_buckets(ra), length_buckets(rb))),
            P(id="hour", kind="line", title="Ritmo horario (UTC)",
              desc="% de comentarios por hora del día.",
              cats=[f"{h:02d}" for h in range(24)], a=list(hour_hist(ra).values()), b=list(hour_hist(rb).values())),
            P(id="gini", kind="bar", title="Concentración de voz (Gini)",
              desc="0 = todos hablan por igual · 1 = una voz domina.",
              cats=["Gini"], a=[concentration(ra)["Gini de actividad"]], b=[concentration(rb)["Gini de actividad"]]),
            P(id="mensual", kind="line", title="Estacionalidad de la muestra",
              desc="Comentarios por mes. La muestra solo cubre el primer trimestre.",
              cats=[f"{m:02d}" for m in range(1, 13)], a=list(month_hist(ra).values()), b=list(month_hist(rb).values())),
        ]},
    ]

    sigrows = battery(ra, rb)
    sections.insert(0, {"title": "¿Hay diferencia significativa?", "panels": [
        P(id="effects", kind="effects", h=540, title="Tamaño de efecto por métrica (2012 → 2022)",
          desc="Barra = Cohen's h (proporciones) o Cliff's δ (continuas). Sólido = efecto real; tenue = significativo pero trivial; casi transparente = no significativo (FDR). Con n≈9k casi todo da p<0.05, así que manda el efecto, no la p.",
          rows=sigrows),
        P(id="sigtable", kind="table", title="Detalle: test, p, q (FDR) y veredicto",
          desc="z de dos proporciones (densidad/presencia) o Mann-Whitney U (continuas); corrección Benjamini-Hochberg. En negrita, los pocos efectos no triviales.",
          rows=sigrows),
    ]})

    data = {"meta": {"a": a, "b": b, "na": len(ra), "nb": len(rb)},
            "cards": [
                {"label": "Comentarios humanos", "a": len(ra), "b": len(rb)},
                {"label": "Autores únicos", "a": concentration(ra)["autores únicos"], "b": concentration(rb)["autores únicos"]},
                {"label": "Palabras por comentario", "a": sa["palabras/coment"], "b": sb["palabras/coment"]},
                {"label": "Comentarios en MAYÚSCULAS %", "a": sa["% grita (MAYÚS)"], "b": sb["% grita (MAYÚS)"]},
                {"label": "Slang (x1000 palabras)", "a": expr["a"][0], "b": expr["b"][0]},
                {"label": "Insultos (x1000 palabras)", "a": expr["a"][1], "b": expr["b"][1]},
            ],
            "sections": sections, "lead": LEAD, "method": METHOD,
            "qual": {"scores": QUAL_SCORES, "quotes": QUOTES}}
    doc = _TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    return out


_TEMPLATE = r"""<!doctype html><html lang=es><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Arqueología Web — r/politics, 2012 y 2022</title>
<script src="../vendor/echarts.min.js"></script>
<style>
:root{
 --paper:#ffffff;--ink:#121212;--sec:#59636b;--faint:#9aa7ad;--rule:#d9d9d9;--red:#E3120B;--c1:#006BA2;--c2:#E3120B;
 --serif:Georgia,"Times New Roman",serif;
 --sans:"Helvetica Neue",Helvetica,Arial,"Liberation Sans",sans-serif;
 --mono:"SF Mono",ui-monospace,Menlo,monospace;
}
.tab{width:52px;height:9px;background:var(--red);margin:0 auto 16px}
*{box-sizing:border-box}html{-webkit-font-smoothing:antialiased}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.6}
.wrap{max-width:1060px;margin:0 auto;padding:52px 28px 80px}
.read{max-width:720px;margin:0 auto;text-align:center}
.eyebrow{font-size:12px;letter-spacing:.22em;text-transform:uppercase;color:var(--c2);font-weight:600}
h1{font-family:var(--serif);font-weight:600;font-size:clamp(38px,6vw,60px);line-height:1.02;letter-spacing:-.01em;margin:.28em 0 .1em}
.dek{font-family:var(--serif);font-style:italic;font-size:20px;color:var(--sec);margin:0 0 24px}
.lead{font-family:var(--serif);font-size:19px;line-height:1.6;margin:22px auto 8px;max-width:600px}
.lead em{font-style:italic;color:var(--sec)}.lead strong{font-weight:600;color:var(--ink)}
.key{display:flex;gap:22px;align-items:center;justify-content:center;margin:20px 0 4px;font-size:13px;color:var(--sec)}
.key b{font-weight:600}.sw{display:inline-block;width:22px;height:3px;vertical-align:middle;margin-right:7px}
.strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));border-top:1.5px solid var(--ink);border-bottom:1.5px solid var(--ink);margin:30px 0 0}
.num{display:flex;flex-direction:column;padding:16px 18px 16px 0;border-right:1px solid var(--rule)}.num:last-child{border-right:0}
.num .l{font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:var(--sec);line-height:1.3;min-height:2.6em}
.num .v{font-family:var(--serif);font-size:27px;margin-top:10px;letter-spacing:-.01em;white-space:nowrap}
.num .v .a{color:var(--c1)}.num .v .arw{color:var(--faint);margin:0 6px;font-size:18px}.num .v .b{color:var(--c2)}
.num .d{font-size:12px;color:var(--sec);margin-top:auto;padding-top:10px;font-variant-numeric:tabular-nums}
.burger{position:fixed;top:18px;left:18px;z-index:30;width:44px;height:44px;border:0;background:var(--ink);color:#fff;font-size:17px;cursor:pointer;border-radius:0;display:flex;align-items:center;justify-content:center}
.burger:hover{background:var(--red)}
.drawer{position:fixed;top:0;left:0;height:100vh;width:264px;max-width:84vw;background:#fff;border-right:1px solid var(--rule);transform:translateX(-100%);transition:transform .22s ease;z-index:35;overflow-y:auto}
.drawer.open{transform:none;box-shadow:2px 0 22px rgba(0,0,0,.14)}
.drawerhd{display:flex;align-items:center;justify-content:space-between;padding:20px 20px 14px;border-bottom:1.5px solid var(--ink)}
.drawerhd span{font-family:var(--mono);font-size:10.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--red)}
.dclose{background:transparent;border:0;color:var(--sec);font-size:23px;line-height:1;cursor:pointer;padding:0 2px}.dclose:hover{color:var(--red)}
.subhd{font-family:var(--mono);font-size:9.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--faint);padding:16px 20px 6px;margin-top:6px;border-top:1px solid var(--rule)}
#menu{padding:6px 0 24px}
#menu button{display:flex;align-items:baseline;gap:10px;width:100%;text-align:left;background:transparent;border:0;border-left:3px solid transparent;padding:9px 20px;font-family:var(--sans);font-size:13.5px;color:var(--sec);cursor:pointer;line-height:1.25}
#menu button .n{font-family:var(--mono);font-size:10px;color:var(--faint);width:18px;flex:none}
#menu button:hover{color:var(--ink);background:#f6f6f6}
#menu button.on{color:var(--ink);font-weight:700;border-left-color:var(--red);background:#fbf1ef}#menu button.on .n{color:var(--red)}
.backdrop{position:fixed;inset:0;background:rgba(0,0,0,.3);opacity:0;pointer-events:none;transition:opacity .22s;z-index:34}
.backdrop.open{opacity:1;pointer-events:auto}
@media(min-width:1120px){.burger,.backdrop,.dclose{display:none}.drawer{transform:none;box-shadow:none}.wrap{margin-left:264px}}
.prose{max-width:700px}.prose h3{font-family:var(--sans);font-weight:700;font-size:15px;margin:22px 0 6px;color:var(--ink)}
.prose p,.prose li{font-size:14.5px;line-height:1.65;color:#333}.prose ul{padding-left:18px;margin:6px 0}
.prose code{font-family:var(--mono);font-size:12.5px;background:#f2f2f2;padding:1px 5px}
section.sec{margin-top:26px}
.kicker{font-size:11.5px;letter-spacing:.24em;text-transform:uppercase;color:var(--c2);font-weight:600}
section.sec>h2{font-family:var(--serif);font-weight:600;font-size:29px;letter-spacing:-.01em;margin:6px 0 0}
section.sec>.srule{border:0;border-top:1.5px solid var(--ink);margin:12px 0 22px}
.figs{display:grid;grid-template-columns:repeat(auto-fit,minmax(430px,1fr));gap:34px 40px}
figure.fig{margin:0}figure.fig.wide{grid-column:1/-1}
.figtop{display:flex;align-items:baseline;gap:10px;border-top:1px solid var(--rule);padding-top:10px}
.fignum{font-family:var(--mono);font-size:11px;letter-spacing:.06em;color:var(--c2);text-transform:uppercase;white-space:nowrap;padding-top:2px}
figure.fig h3{font-family:var(--sans);font-weight:700;font-size:16px;letter-spacing:-.01em;margin:0;line-height:1.22}
.chart{height:300px;margin-top:6px}
figcaption{font-size:12.5px;color:var(--sec);font-style:italic;max-width:620px;margin-top:4px}
.tablewrap{overflow-x:auto;margin-top:8px}
table.stat{width:100%;border-collapse:collapse;font-size:12.5px}
table.stat th{text-align:right;font-family:var(--sans);font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;color:var(--sec);border-bottom:1.5px solid var(--ink);padding:7px 12px 7px 0;white-space:nowrap}
table.stat th:first-child,table.stat td:first-child{text-align:left}
table.stat td{padding:6px 12px 6px 0;border-bottom:1px solid var(--rule);font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
table.stat tr.real td{color:var(--ink)}table.stat tr.real td:first-child{font-weight:700}
table.stat tr.triv td{color:var(--sec)}table.stat tr.ns td{color:var(--faint)}
.tabs{float:right;margin-top:8px}.tabs button{background:transparent;color:var(--sec);border:1px solid var(--rule);
 padding:3px 10px;cursor:pointer;font-family:var(--sans);font-size:11px;letter-spacing:.03em;text-transform:uppercase;margin-left:5px}
.tabs button.on{color:#fff;background:var(--c2);border-color:var(--c2)}
.voices{display:grid;grid-template-columns:1fr 1fr;gap:34px 40px;margin-top:8px}
.voices h4{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;margin:0 0 14px}
.q12 h4{color:var(--c1)}.q22 h4{color:var(--c2)}
blockquote{margin:0 0 18px;padding:2px 0 2px 18px;border-left:2px solid var(--rule)}
.q12 blockquote{border-left-color:var(--c1)}.q22 blockquote{border-left-color:var(--c2)}
blockquote .tag{font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--faint)}
blockquote .txt{font-family:var(--serif);font-size:16px;line-height:1.5;margin:6px 0}
blockquote .who{font-family:var(--mono);font-size:11.5px;color:var(--sec)}
footer{margin-top:56px;border-top:1px solid var(--rule);padding-top:16px;font-size:12px;color:var(--faint);max-width:680px}
@media(max-width:760px){.voices{grid-template-columns:1fr}.wrap{padding:34px 20px 60px}}
</style></head><body>
<button id=burger class=burger aria-label="Abrir menú de estratos">☰</button>
<aside id=drawer class=drawer><div class=drawerhd><span>Estratos</span><button class=dclose id=dclose aria-label="Cerrar menú">×</button></div><nav id=menu></nav></aside>
<div id=backdrop class=backdrop></div>
<div class=wrap>
<div class=read>
<div class=tab></div>
<div class=eyebrow>Arqueología digital · un estudio diacrónico</div>
<h1 id=h1></h1><div class=dek id=dek></div><p class=lead id=lead></p>
</div>
<div class=key><span><span class=sw style="background:#006BA2"></span><b id=k1></b> · pasado</span>
<span><span class=sw style="background:#E3120B"></span><b id=k2></b> · presente</span></div>
<div class=strip id=strip></div>
<div id=sections></div>
<footer id=foot></footer>
</div>
<script>
const DATA=__DATA__;const A=DATA.meta.a,B=DATA.meta.b;
const P={c:['#006BA2','#E3120B'],ink:'#121212',sec:'#59636b',grid:'#e4e4e4'};
const charts=[],tors={},secCharts={};let curList=null;
function mk(id){const c=echarts.init(document.getElementById(id));charts.push(c);if(curList)curList.push(c);return c;}
const ax=()=>({axisLabel:{color:P.sec,fontSize:11},axisLine:{lineStyle:{color:P.grid}},splitLine:{lineStyle:{color:P.grid,type:'solid'}},axisTick:{show:false}});
const TIP=()=>({backgroundColor:'#ffffff',borderColor:'#d9d9d9',textStyle:{color:P.ink}});
const base=extra=>Object.assign({backgroundColor:'transparent',tooltip:TIP(),grid:{left:4,right:18,bottom:2,top:14,containLabel:true},textStyle:{fontFamily:'Inter,system-ui,sans-serif'}},extra);
function grouped(id,cats,a,b,unit){mk(id).setOption(base({tooltip:Object.assign({trigger:'axis'},TIP()),
  xAxis:Object.assign({type:'category',data:cats},ax()),yAxis:Object.assign({type:'value',axisLabel:{color:P.sec,fontSize:11,formatter:'{value}'+(unit||'')}},ax()),
  series:[{name:A,type:'bar',data:a,itemStyle:{color:P.c[0]},barMaxWidth:26},{name:B,type:'bar',data:b,itemStyle:{color:P.c[1]},barMaxWidth:26}]}));}
function groupedH(id,cats,a,b,unit){const o=cats.map((c,i)=>[c,a[i],b[i]]).reverse();
  mk(id).setOption(base({tooltip:Object.assign({trigger:'axis'},TIP()),
  yAxis:Object.assign({type:'category',data:o.map(x=>x[0])},ax()),
  xAxis:Object.assign({type:'value',axisLabel:{color:P.sec,fontSize:11,formatter:'{value}'+(unit||'')}},ax()),
  series:[{name:A,type:'bar',data:o.map(x=>x[1]),itemStyle:{color:P.c[0]},barMaxWidth:11},
   {name:B,type:'bar',data:o.map(x=>x[2]),itemStyle:{color:P.c[1]},barMaxWidth:11}]}));}
function radar(id,cats,a,b){const mx=Math.max(...a,...b)*1.2||1;mk(id).setOption(base({grid:undefined,
  radar:{indicator:cats.map(n=>({name:n,max:+mx.toFixed(1)})),radius:'62%',center:['50%','55%'],
   axisName:{color:P.sec,fontSize:11},splitLine:{lineStyle:{color:P.grid}},splitArea:{areaStyle:{color:['rgba(0,0,0,0)']}},axisLine:{lineStyle:{color:P.grid}}},
  series:[{type:'radar',symbolSize:3,data:[
   {value:a,name:A,itemStyle:{color:P.c[0]},lineStyle:{color:P.c[0],width:2},areaStyle:{color:'rgba(0,107,162,.12)'}},
   {value:b,name:B,itemStyle:{color:P.c[1]},lineStyle:{color:P.c[1],width:2},areaStyle:{color:'rgba(227,18,11,.10)'}}]}]}));}
function lines(id,cats,a,b){mk(id).setOption(base({tooltip:Object.assign({trigger:'axis'},TIP()),
  xAxis:Object.assign({type:'category',data:cats,boundaryGap:false},ax()),yAxis:Object.assign({type:'value'},ax()),
  series:[{name:A,type:'line',smooth:true,data:a,itemStyle:{color:P.c[0]},lineStyle:{width:2},areaStyle:{color:'rgba(0,107,162,.08)'}},
   {name:B,type:'line',smooth:true,data:b,itemStyle:{color:P.c[1]},lineStyle:{width:2},areaStyle:{color:'rgba(227,18,11,.07)'}}]}));}
function stack(id,segs,rows){mk(id).setOption(base({tooltip:Object.assign({trigger:'axis'},TIP()),
  legend:{data:segs,textStyle:{color:P.sec},top:0,right:0,icon:'rect',itemHeight:9},grid:{left:4,right:18,top:34,bottom:2,containLabel:true},
  xAxis:Object.assign({type:'value',max:100,axisLabel:{color:P.sec,fontSize:11,formatter:'{value}%'}},ax()),yAxis:Object.assign({type:'category',data:rows.map(r=>r.name)},ax()),
  series:segs.map((s,i)=>({name:s,type:'bar',stack:'s',barMaxWidth:34,data:rows.map(r=>r.vals[i]),itemStyle:{color:i?'#c2ced4':P.c[1]},label:{show:true,color:i?P.ink:'#fff',formatter:'{c}%'}}))}));}
function rank(id,items,color){const o=items.slice().reverse();mk(id).setOption(base({tooltip:Object.assign({trigger:'axis'},TIP()),
  grid:{left:4,right:26,top:6,bottom:2,containLabel:true},
  yAxis:Object.assign({type:'category',data:o.map(x=>x[0]),axisLabel:{color:P.ink,fontFamily:'SF Mono,ui-monospace,monospace',fontSize:11.5}},ax()),
  xAxis:Object.assign({type:'value',show:false},ax()),
  series:[{type:'bar',data:o.map(x=>x[1]),barMaxWidth:13,itemStyle:{color:color},label:{show:true,position:'right',color:P.sec,fontSize:11}}]}));}
function tornado(p,kind){['uni','bi','tri'].forEach(k=>{const el=document.getElementById(k[0]+'_'+p.id);if(el)el.classList.toggle('on',k==kind);});
  const d=p[kind],items=[...d.a,...d.b].sort((x,y)=>x[1]-y[1]);
  mk(p.id).setOption(base({tooltip:Object.assign({trigger:'axis'},TIP()),grid:{left:4,right:20,top:6,bottom:2,containLabel:true},
   xAxis:Object.assign({type:'value'},ax()),yAxis:Object.assign({type:'category',data:items.map(x=>x[0]),axisLabel:{color:P.ink,fontFamily:'SF Mono,ui-monospace,monospace',fontSize:11.5}},ax()),
   series:[{type:'bar',barMaxWidth:13,data:items.map(x=>({value:+x[1].toFixed(1),itemStyle:{color:x[1]>=0?P.c[0]:P.c[1]}}))}]}));}
function effects(id,rows){const o=rows.slice().reverse();const fp=x=>x<1e-3?x.toExponential(1):x.toFixed(3);
  mk(id).setOption(base({tooltip:Object.assign({trigger:'item',formatter:pt=>{const r=o[pt.dataIndex];
    return `${r.name}<br/>efecto ${(r.eff>=0?'+':'')+r.eff.toFixed(3)} · ${r.mag}<br/>${r.a}${r.unit?' '+r.unit:''} → ${r.b}<br/>p=${fp(r.p)} · q=${fp(r.q)}<br/><b>${r.verdict}</b>`;}},TIP()),
   grid:{left:4,right:36,top:6,bottom:2,containLabel:true},
   xAxis:Object.assign({type:'value'},ax()),
   yAxis:Object.assign({type:'category',data:o.map(r=>r.name),axisLabel:{color:P.ink,fontSize:11}},ax()),
   series:[{type:'bar',barMaxWidth:12,data:o.map(r=>({value:+r.eff.toFixed(3),
     itemStyle:{color:r.eff>=0?P.c[1]:P.c[0],opacity:r.sig?(r.mag=='insignificante'?0.34:1):0.12}})),
     label:{show:true,position:'right',color:P.sec,fontSize:10,formatter:pt=>o[pt.dataIndex].mag}}]}));}
function table(id,rows){const fp=x=>x<1e-3?x.toExponential(1):x.toFixed(3);
  const cls=r=>r.sig?(r.mag=='insignificante'?'triv':'real'):'ns';
  document.getElementById(id).innerHTML='<table class=stat><thead><tr><th>Métrica</th><th>2012</th><th>2022</th><th>Efecto</th><th>Magnitud</th><th>p</th><th>q (FDR)</th><th>Veredicto</th></tr></thead><tbody>'+
   rows.map(r=>`<tr class=${cls(r)}><td>${r.name}</td><td>${r.a}</td><td>${r.b}</td><td>${(r.eff>=0?'+':'')+r.eff.toFixed(3)}</td><td>${r.mag}</td><td>${fp(r.p)}</td><td>${fp(r.q)}</td><td>${r.verdict}</td></tr>`).join('')+'</tbody></table>';}
window.tog=(id,kind)=>tornado(tors[id],kind);
function draw(p){
 if(p.kind=='effects')return effects(p.id,p.rows);
 if(p.kind=='table')return table(p.id,p.rows);
 if(p.kind=='bar')grouped(p.id,p.cats,p.a,p.b,p.unit);
 else if(p.kind=='barh')groupedH(p.id,p.cats,p.a,p.b,p.unit);
 else if(p.kind=='radar')radar(p.id,p.cats,p.a,p.b);
 else if(p.kind=='line')lines(p.id,p.cats,p.a,p.b);
 else if(p.kind=='stack')stack(p.id,p.segs,p.rows);
 else if(p.kind=='rank')rank(p.id,p.items,p.color);
 else if(p.kind=='tornado'){tors[p.id]=p;tornado(p,'uni');}
}
const NSEC=DATA.sections.length;
function setDrawer(o){document.getElementById('drawer').classList.toggle('open',o);document.getElementById('backdrop').classList.toggle('open',o);}
function drawSection(i){curList=secCharts[i]=[];
 if(i<NSEC)DATA.sections[i].panels.forEach(draw);
 else if(i==NSEC)radar('qual',DATA.qual.scores.cats,DATA.qual.scores['2012'],DATA.qual.scores['2022']);
 curList=null;}
function show(i){for(let s=0;s<=NSEC+1;s++){const el=document.getElementById('sec'+s);if(el)el.style.display=s==i?'':'none';}
 const m=document.getElementById('menu');if(m)[...m.querySelectorAll('button')].forEach((b,j)=>b.classList.toggle('on',j==i));
 setDrawer(false);window.scrollTo(0,0);
 if(!secCharts[i])drawSection(i);else secCharts[i].forEach(c=>c.resize());}
function render(){
 document.getElementById('h1').textContent='Arqueología Web';
 document.getElementById('dek').textContent=`Cómo cambió la conversación en r/politics entre ${A} y ${B}`;
 document.getElementById('lead').innerHTML=DATA.lead;
 document.getElementById('k1').textContent=A;document.getElementById('k2').textContent=B;
 document.getElementById('strip').innerHTML=DATA.cards.map(c=>{const d=c.a?Math.round((c.b-c.a)/c.a*100):0;const s=d>0?'+':'';
   return `<div class=num><div class=l>${c.label}</div><div class=v><span class=a>${c.a}</span><span class=arw>→</span><span class=b>${c.b}</span></div><div class=d>${s}${d}%</div></div>`;}).join('');
 const root=document.getElementById('sections');let n=0;
 DATA.sections.forEach((sec,i)=>{
   const s=document.createElement('section');s.className='sec';s.id='sec'+i;s.style.display='none';
   const g=`<div class=kicker>Estrato ${String(i+1).padStart(2,'0')}</div><h2>${sec.title}</h2><hr class=srule><div class=figs>`+
    sec.panels.map(p=>{n++;const wide=/tornado|rank|stack|effects|table/.test(p.kind)?' wide':'';
     const tabs=p.kind=='tornado'?`<div class=tabs><button id=u_${p.id} class=on onclick="tog('${p.id}','uni')">Palabras</button><button id=b_${p.id} onclick="tog('${p.id}','bi')">Bigramas</button><button id=t_${p.id} onclick="tog('${p.id}','tri')">Trigramas</button></div>`:'';
     const body=p.kind=='table'?`<div id=${p.id} class=tablewrap></div>`:`<div class=chart id=${p.id} style="height:${p.h||300}px"></div>`;
     return `<figure class="fig${wide}">${tabs}<div class=figtop><span class=fignum>Fig ${n}</span><h3>${p.title}</h3></div>${body}<figcaption>${p.desc||''}</figcaption></figure>`;
    }).join('')+'</div>';
   s.innerHTML=g;root.appendChild(s);
 });
 const coda=document.createElement('section');coda.className='sec';coda.id='sec'+NSEC;coda.style.display='none';
 const vq=(g,cls)=>`<div class="${cls}"><h4>${g}</h4>`+DATA.qual.quotes[g].map(q=>`<blockquote><div class=tag>${q[1]}</div><div class=txt>“${q[2]}”</div><div class=who>u/${q[0]}</div></blockquote>`).join('')+'</div>';
 coda.innerHTML=`<div class=kicker>Coda</div><h2>Lectura cualitativa</h2><hr class=srule>
   <div class=figs><figure class="fig wide"><div class=figtop><span class=fignum>Radar</span><h3>Cómo se leen las voces (muestra 20+20, subjetivo)</h3></div>
   <div class=chart id=qual style=height:340px></div><figcaption>Valoración del autor sobre la muestra leída; no es una medida automática.</figcaption></figure></div>
   <div class=voices>${vq('2012','q12')}${vq('2022','q22')}</div>`;
 root.appendChild(coda);
 const meth=document.createElement('section');meth.className='sec';meth.id='sec'+(NSEC+1);meth.style.display='none';
 meth.innerHTML=`<div class=kicker>Apéndice</div><h2>Metodología</h2><hr class=srule><div class=prose>${DATA.method}</div>`;
 root.appendChild(meth);
 const labels=DATA.sections.map(s=>s.title).concat(['Coda','Metodología']);
 document.getElementById('menu').innerHTML=labels.map((t,i)=>
   (i==NSEC?'<div class=subhd>Apéndice</div>':'')+
   `<button onclick="show(${i})"><span class=n>${i<NSEC?String(i+1).padStart(2,'0'):'—'}</span><span>${t}</span></button>`).join('');
 document.getElementById('burger').onclick=()=>setDrawer(!document.getElementById('drawer').classList.contains('open'));
 document.getElementById('backdrop').onclick=()=>setDrawer(false);
 document.getElementById('dclose').onclick=()=>setDrawer(false);
 document.getElementById('foot').textContent=`Cuantitativo sobre ${DATA.meta.na}+${DATA.meta.nb} comentarios de r/politics (bots filtrados), primer trimestre. Cualitativo sobre una muestra de 20+20 leída a mano. Descriptivo, no causal; una sola comunidad; léxicos ilustrativos. Generado por arqueo.ui.`;
 show(0);
}
render();addEventListener('resize',()=>{const v=document.querySelector('.sec:not([style*="none"])');charts.forEach(c=>c.resize());});
</script></body></html>"""


if __name__ == "__main__":
    try:
        print("->", build())
    except SystemExit as e:
        print(e)
