"""Reporte profundo standalone (HTML autocontenido, solo stdlib).

Más hondo que el dashboard: estructura de interacción, colocaciones (bigramas),
fundamentos morales, pronombres/encuadre (endogrupo-exogrupo), hedging/modales,
concentración de voz (Gini) y estacionalidad. Todo descriptivo.

    python -m arqueo.report            # -> data/report.html
"""
from __future__ import annotations
import glob
import html
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone

from .analyze import tokenize, log_odds
from .dashboard import load, by_era, summary, style, lexicon_pct, LEXICONS

# --- léxicos de análisis profundo (ilustrativos) ---
MFT = {
    "cuidado/daño": {"care", "harm", "suffer", "cruel", "protect", "hurt", "compassion", "victim", "kill", "abuse", "safe"},
    "justicia/trampa": {"fair", "unfair", "equal", "justice", "rights", "cheat", "fraud", "corrupt", "honest", "equality"},
    "lealtad/traición": {"loyal", "betray", "team", "nation", "patriot", "traitor", "together", "country", "treason"},
    "autoridad/subversión": {"authority", "law", "order", "respect", "obey", "tradition", "rebel", "chaos", "leader", "power"},
    "pureza/degradación": {"pure", "sacred", "disgust", "sin", "holy", "filthy", "decent", "degenerate", "clean"},
    "libertad/opresión": {"freedom", "liberty", "free", "oppress", "tyranny", "control", "force", "government"},
}
PRON = {
    "yo (I)": {"i", "me", "my", "mine", "myself", "i'm", "i've", "i'll", "id"},
    "nosotros (we)": {"we", "us", "our", "ours", "we're", "we've"},
    "tú (you)": {"you", "your", "yours", "you're", "u"},
    "ellos (they)": {"they", "them", "their", "theirs", "they're"},
}
HEDGE = {"maybe", "perhaps", "probably", "might", "seems", "guess", "suppose",
         "likely", "possibly", "apparently", "somewhat", "pretty"}
MODAL = {"should", "must", "need", "ought", "cannot", "shall", "have"}
PROFANITY = {"damn", "shit", "fuck", "fucking", "fucked", "crap", "hell", "ass",
             "bullshit", "stupid", "idiot", "moron", "dumb"}

_WORDS = re.compile(r"[a-z']+")


def bigrams(text):
    t = tokenize(text)
    return [f"{t[i]} {t[i+1]}" for i in range(len(t) - 1)]


def gini(counts):
    xs = sorted(counts)
    n, s = len(xs), sum(counts)
    if n == 0 or s == 0:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return round((2 * cum) / (n * s) - (n + 1) / n, 3)


def concentration(recs):
    per_author = Counter(r["author"] for r in recs)
    top1 = per_author.most_common(1)[0][1] if per_author else 0
    return {"autores únicos": len(per_author),
            "Gini de actividad": gini(list(per_author.values())),
            "% del autor más activo": round(100 * top1 / (len(recs) or 1), 1)}


def interaction(recs):
    top = sum(1 for r in recs if (r.get("parent_id") or "").startswith("t3_"))
    rep = sum(1 for r in recs if (r.get("parent_id") or "").startswith("t1_"))
    n = len(recs) or 1
    return {"% comenta el post (t3)": round(100 * top / n, 1),
            "% responde a otro (t1)": round(100 * rep / n, 1)}


def pronouns(recs):
    tot, words = Counter(), 0
    for r in recs:
        for w in _WORDS.findall(r["text"].lower()):
            words += 1
            for k, s in PRON.items():
                if w in s:
                    tot[k] += 1
    return {k: round(1000 * tot[k] / (words or 1), 1) for k in PRON}   # por mil palabras


def lex_pct_group(recs, group):
    return {name: lexicon_pct(recs, lex) for name, lex in group.items()}


def markers(recs):
    n = len(recs) or 1
    def frac(s):
        return round(100 * sum(1 for r in recs if set(tokenize(r["text"])) & s) / n, 1)
    return {"% con matización (hedging)": frac(HEDGE),
            "% con deber/necesidad (modales)": frac(MODAL),
            "% con lenguaje soez": frac(PROFANITY)}


def month_hist(recs):
    c = Counter(datetime.fromtimestamp(r["ts"], timezone.utc).strftime("%m") for r in recs)
    return {f"{m}": c.get(f"{m:02d}", 0) for m in range(1, 13)}


# --- render ---
def _bar(pct, color="#6aa9ff"):
    return f'<div class=bar><span style="width:{min(max(pct,0),100):.0f}%;background:{color}"></span></div>'


def _cmp_table(metric_by_era, unit=""):
    eras = list(metric_by_era)
    keys = list(next(iter(metric_by_era.values())))
    head = "".join(f"<th>{html.escape(e)}</th>" for e in eras)
    rows = ""
    for k in keys:
        vals = [metric_by_era[e][k] for e in eras]
        numeric = all(isinstance(v, (int, float)) for v in vals)
        mx = (max((abs(v) for v in vals), default=1) or 1) if numeric else 1
        cells = ""
        for v in vals:
            bar = _bar(100 * v / mx) if numeric else ""
            cells += f'<td class=era>{html.escape(str(v))}{unit if numeric else ""}{bar}</td>'
        rows += f"<tr><td>{html.escape(k)}</td>{cells}</tr>"
    return f"<table class=cmp><tr><th></th>{head}</tr>{rows}</table>"


def _logodds_block(eras, tok, label):
    ks = list(eras)
    a, b = ks[0], ks[-1]
    res = log_odds([r["text"] for r in eras[a]], [r["text"] for r in eras[b]], top=14, tok=tok)
    mx = max([abs(z) for _, z in res["a_distinctive"] + res["b_distinctive"]] or [1])
    col = lambda items, c: "".join(
        f'<tr><td class=w>{html.escape(w)}</td><td>{_bar(100*abs(z)/mx,c)}<span class=z>{z:+.1f}</span></td></tr>'
        for w, z in items)
    return (f'<h4>{label}</h4><div class=two>'
            f'<div><h5>Propio de {html.escape(a)}</h5><table>{col(res["a_distinctive"],"#6aa9ff")}</table></div>'
            f'<div><h5>Propio de {html.escape(b)}</h5><table>{col(res["b_distinctive"],"#ff8a5c")}</table></div></div>')


def build(glob_pat="data/normalized/**/*.jsonl", out="data/report.html"):
    rows = load(glob_pat)
    if not rows:
        raise SystemExit("No hay JSONL normalizado. Corre 'ingest' primero.")
    eras = by_era(rows)
    total = len(rows)

    S = {
        "resumen": _cmp_table({e: {**summary(r)} for e, r in eras.items()}),
        "conc": _cmp_table({e: concentration(r) for e, r in eras.items()}),
        "inter": _cmp_table({e: interaction(r) for e, r in eras.items()}),
        "uni": _logodds_block(eras, tokenize, "Unigramas distintivos"),
        "bi": _logodds_block(eras, bigrams, "Bigramas / colocaciones distintivas"),
        "persp": _cmp_table({e: lex_pct_group(r, LEXICONS) for e, r in eras.items()}, unit="%"),
        "mft": _cmp_table({e: lex_pct_group(r, MFT) for e, r in eras.items()}, unit="%"),
        "pron": _cmp_table({e: pronouns(r) for e, r in eras.items()}),
        "mark": _cmp_table({e: markers(r) for e, r in eras.items()}, unit="%"),
        "styl": _cmp_table({e: style(r) for e, r in eras.items()}),
        "month": _cmp_table({e: month_hist(r) for e, r in eras.items()}),
    }
    sizes = " · ".join(f"{e}: {len(r)}" for e, r in eras.items())
    doc = _TEMPLATE.format(total=total, sizes=html.escape(sizes), **S)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    return out


_TEMPLATE = """<!doctype html><html lang=es><meta charset=utf-8>
<title>Arqueología Web — reporte profundo</title><style>
:root{{color-scheme:dark}}body{{background:#0d1117;color:#c9d1d9;font:14px/1.55 system-ui,sans-serif;margin:0;padding:26px;max-width:1080px;margin:auto}}
h1{{font-size:23px}}h2{{font-size:16px;border-bottom:1px solid #30363d;padding-bottom:6px;margin-top:38px}}
h4{{margin:.6em 0 .2em;font-size:14px;color:#c9d1d9}}h5{{margin:.3em 0;font-size:12px;color:#8b949e}}
.banner{{background:#0b2b26;border:1px solid #1f6f5c;color:#5fd0b0;padding:10px 14px;border-radius:8px;margin:14px 0}}
.toc{{color:#8b949e;font-size:13px;margin:10px 0 0}}.toc a{{color:#6aa9ff;text-decoration:none;margin-right:14px}}
table{{width:100%;border-collapse:collapse;margin:6px 0}}td,th{{text-align:left;padding:2px 8px;vertical-align:middle}}
th{{color:#8b949e;font-weight:600;font-size:12px}}.cmp td.era{{white-space:nowrap}}
.two{{display:flex;gap:26px}}.two>div{{flex:1}}
.bar{{display:inline-block;width:110px;height:9px;background:#21262d;border-radius:5px;overflow:hidden;margin-left:8px;vertical-align:middle}}
.bar span{{display:block;height:100%}}.z{{color:#6e7681;margin-left:6px;font-variant-numeric:tabular-nums}}
td.w{{font-family:ui-monospace,monospace;color:#e6edf3}}.note{{color:#6e7681;font-size:13px}}footer{{margin-top:44px;color:#6e7681;font-size:12px}}
</style>
<h1>🏺 Arqueología Web — reporte profundo</h1>
<div class=banner><b>{total} comentarios</b> ({sizes}). Análisis descriptivo, generador de hipótesis.
Corpus de r/politics con muestreo mensual estratificado; sigue siendo pequeño frente al universo del sub.</div>
<p class=toc><a href=#c1>Resumen</a><a href=#c2>Concentración de voz</a><a href=#c3>Interacción</a>
<a href=#c4>Léxico distintivo</a><a href=#c5>Perspectivas</a><a href=#c6>Fundamentos morales</a>
<a href=#c7>Pronombres/encuadre</a><a href=#c8>Marcadores</a><a href=#c9>Estilo</a><a href=#c10>Estacionalidad</a></p>

<h2 id=c1>1 · Resumen del corpus</h2>{resumen}

<h2 id=c2>2 · Concentración de voz</h2>
<p class=note>Gini de comentarios por autor (0 = todos igual, 1 = una voz domina). ¿Se concentró o democratizó el habla?</p>{conc}

<h2 id=c3>3 · Estructura de interacción</h2>
<p class=note>¿Se comenta el post (t3) o se conversa entre usuarios (t1)? Proxy de conversación vs reacción.</p>{inter}

<h2 id=c4>4 · Léxico distintivo (log-odds)</h2>{uni}{bi}

<h2 id=c5>5 · Perspectivas (ejes temáticos)</h2>
<p class=note>% de comentarios que activan cada eje. Lexicones ilustrativos y solapados.</p>{persp}

<h2 id=c6>6 · Fundamentos morales (Moral Foundations Theory)</h2>
<p class=note>Qué intuiciones morales se invocan. Marco de Haidt et al.; lexicón reducido.</p>{mft}

<h2 id=c7>7 · Pronombres y encuadre</h2>
<p class=note>Frecuencia por mil palabras. yo→individualismo; nosotros/ellos→endogrupo/exogrupo (polarización).</p>{pron}

<h2 id=c8>8 · Marcadores de registro</h2>
<p class=note>Matización (incertidumbre), modales (deber/necesidad) y lenguaje soez (crispación).</p>{mark}

<h2 id=c9>9 · Estilo</h2>{styl}

<h2 id=c10>10 · Estacionalidad (comentarios por mes)</h2>
<p class=note>Cobertura del muestreo mensual y picos del año (p.ej. ciclos electorales).</p>{month}

<footer>arqueo.report · descriptivo, no causal · sin dependencias externas</footer>
</html>"""


def _selfcheck():
    assert gini([1, 1, 1, 1]) == 0.0
    assert gini([0, 0, 0, 10]) > 0.6, gini([0, 0, 0, 10])
    assert bigrams("government tax war")[:1] == ["government tax"]
    recs = [{"text": "we must protect our freedom", "author": "a", "ts": 1, "parent_id": "t3_x"},
            {"text": "they betray the nation", "author": "b", "ts": 2, "parent_id": "t1_y"}]
    assert interaction(recs)["% comenta el post (t3)"] == 50.0
    assert pronouns(recs)["nosotros (we)"] > 0
    print("report OK")


if __name__ == "__main__":
    _selfcheck()
    try:
        print("->", build())
    except SystemExit as e:
        print(e)
