"""Dashboard estático (HTML autocontenido, solo stdlib) con los análisis baratos.

Lee el JSONL normalizado, computa todo en Python puro y escribe un único .html
con gráficos de barras en CSS (sin servidor, sin deps). Ábrelo en el navegador.

    python -m arqueo.dashboard            # -> data/dashboard.html

Pensado como vista exploratoria: TODO resultado aquí es descriptivo y, con
muestras pequeñas, ilustrativo, no concluyente (ver banner del propio dashboard).
"""
from __future__ import annotations
import glob
import html
import json
import os
from collections import Counter
from datetime import datetime, timezone

from .analyze import tokenize, log_odds

# --- lexicones ilustrativos (se solapan a propósito; son un termómetro, no verdad) ---
LEXICONS = {
    "político": {"government", "election", "vote", "president", "policy", "congress",
                 "senate", "democrat", "republican", "democrats", "republicans", "law",
                 "rights", "war", "liberal", "conservative", "party", "campaign"},
    "económico": {"money", "tax", "taxes", "economy", "job", "jobs", "market", "debt",
                  "wage", "wages", "price", "prices", "inflation", "bank", "trade",
                  "poverty", "income", "budget", "cost", "wealth", "capitalism"},
    "filosófico": {"moral", "ethics", "truth", "meaning", "justice", "freedom", "god",
                   "belief", "reason", "value", "values", "society", "principle",
                   "wrong", "evil", "human", "faith"},
}
_POS = {"good", "great", "love", "best", "hope", "agree", "thanks", "happy", "win", "right"}
_NEG = {"bad", "hate", "worst", "wrong", "stupid", "corrupt", "fail", "lie", "lies", "war", "angry"}


def load(glob_pat="data/normalized/**/*.jsonl"):
    rows = []
    for p in glob.glob(glob_pat, recursive=True):
        with open(p, encoding="utf-8") as f:
            rows += [json.loads(l) for l in f if l.strip()]
    return rows


def by_era(rows):
    d = {}
    for r in rows:
        d.setdefault(r["era"], []).append(r)
    return dict(sorted(d.items()))


def summary(recs):
    ts = [r["ts"] for r in recs]
    fmt = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M")
    return {"comentarios": len(recs), "autores únicos": len(set(r["author"] for r in recs)),
            "coment/autor": round(len(recs) / (len(set(r['author'] for r in recs)) or 1), 2),
            "desde": fmt(min(ts)), "hasta": fmt(max(ts))}


def style(recs):
    toks_all, wl, cl = [], [], []
    q = caps = url = emo = pos = neg = 0
    for r in recs:
        t = r["text"]
        toks = tokenize(t)
        toks_all += toks
        wl.append(len(t.split()))
        cl.append(len(t))
        if "?" in t:
            q += 1
        if any(w.isupper() and len(w) >= 4 for w in t.split()):
            caps += 1
        if "http" in t.lower():
            url += 1
        if any(e in t for e in (":)", ":(", ":-)", ";)", ":D", "<3")) or any(ord(c) > 0x2600 for c in t):
            emo += 1
        s = set(w.lower() for w in t.split())
        pos += bool(s & _POS)
        neg += bool(s & _NEG)
    n = len(recs) or 1
    return {"palabras/coment": round(sum(wl) / n, 1), "chars/coment": round(sum(cl) / n),
            "riqueza léxica (TTR)": round(len(set(toks_all)) / (len(toks_all) or 1), 3),
            "% preguntas": round(100 * q / n, 1), "% grita (MAYÚS)": round(100 * caps / n, 1),
            "% con enlace": round(100 * url / n, 1), "% emoji/emoticón": round(100 * emo / n, 1),
            "% tono +": round(100 * pos / n, 1), "% tono −": round(100 * neg / n, 1)}


def lexicon_pct(recs, lex):
    n = len(recs) or 1
    return round(100 * sum(1 for r in recs if set(tokenize(r["text"])) & lex) / n, 1)


def minute_hist(recs):
    c = Counter(datetime.fromtimestamp(r["ts"], timezone.utc).strftime("%H:%M") for r in recs)
    return dict(sorted(c.items()))


# --- render (barras CSS, sin JS) ---
def _bar(pct, color="#6aa9ff"):
    return f'<div class="bar"><span style="width:{min(pct,100):.0f}%;background:{color}"></span></div>'


def _kv_table(d):
    return "".join(f"<tr><td>{html.escape(str(k))}</td><td class=v>{html.escape(str(v))}</td></tr>" for k, v in d.items())


def _metric_bars(metric_by_era, maxv, unit="%"):
    eras = list(metric_by_era)
    keys = list(next(iter(metric_by_era.values())))
    rows = ""
    for k in keys:
        cells = ""
        for e in eras:
            v = metric_by_era[e][k]
            cells += f'<td class=era>{v}{unit}{_bar(100*v/maxv if maxv else 0)}</td>'
        rows += f"<tr><td>{html.escape(k)}</td>{cells}</tr>"
    head = "".join(f"<th>{html.escape(e)}</th>" for e in eras)
    return f"<table class=cmp><tr><th></th>{head}</tr>{rows}</table>"


def build(glob_pat="data/normalized/**/*.jsonl", out="data/dashboard.html"):
    rows = load(glob_pat)
    if not rows:
        raise SystemExit("No hay JSONL normalizado. Corre 'ingest' primero.")
    eras = by_era(rows)
    total = len(rows)

    # 1. resumen
    sum_tbl = "".join(f"<div class=card><h3>{html.escape(e)}</h3><table class=kv>{_kv_table(summary(r))}</table></div>"
                      for e, r in eras.items())

    # 2. términos distintivos (log-odds) entre el primer y último corte
    logodds_html = "<p class=note>Se necesitan ≥2 cortes.</p>"
    if len(eras) >= 2:
        ks = list(eras)
        a, b = ks[0], ks[-1]
        res = log_odds([r["text"] for r in eras[a]], [r["text"] for r in eras[b]], top=12)
        mx = max([abs(z) for _, z in res["a_distinctive"] + res["b_distinctive"]] or [1])
        col = lambda items, c: "".join(
            f'<tr><td class=w>{html.escape(w)}</td><td>{_bar(100*abs(z)/mx, c)}<span class=z>{z:+.1f}</span></td></tr>'
            for w, z in items)
        logodds_html = (
            f'<div class=two><div><h4>Propio de {html.escape(a)}</h4><table>{col(res["a_distinctive"], "#6aa9ff")}</table></div>'
            f'<div><h4>Propio de {html.escape(b)}</h4><table>{col(res["b_distinctive"], "#ff8a5c")}</table></div></div>')

    # 3. perspectivas (lexicones)
    persp = {e: {name: lexicon_pct(r, lex) for name, lex in LEXICONS.items()} for e, r in eras.items()}
    persp_html = _metric_bars(persp, maxv=max(max(d.values()) for d in persp.values()) or 1)

    # 4. estilo / registro
    styl = {e: style(r) for e, r in eras.items()}
    # normaliza cada fila a su propio máximo para que la barra sea legible
    styl_keys = list(next(iter(styl.values())))
    styl_html = "<table class=cmp><tr><th></th>" + "".join(f"<th>{html.escape(e)}</th>" for e in styl) + "</tr>"
    for k in styl_keys:
        mx = max(styl[e][k] for e in styl) or 1
        styl_html += f"<tr><td>{html.escape(k)}</td>" + "".join(
            f'<td class=era>{styl[e][k]}{_bar(100*styl[e][k]/mx)}</td>' for e in styl) + "</tr>"
    styl_html += "</table>"

    # 5. distribución temporal (expone el sesgo de muestreo)
    temp_html = ""
    for e, r in eras.items():
        h = minute_hist(r)
        mx = max(h.values()) or 1
        bars = "".join(f'<tr><td class=w>{html.escape(m)}</td><td>{_bar(100*c/mx)}<span class=z>{c}</span></td></tr>'
                       for m, c in h.items())
        temp_html += f"<div><h4>{html.escape(e)}</h4><table>{bars}</table></div>"
    temp_html = f"<div class=two>{temp_html}</div>"

    span = f"{min(r['ts'] for r in rows)}..{max(r['ts'] for r in rows)}"
    doc = _TEMPLATE.format(total=total, eras=len(eras), logodds=logodds_html, persp=persp_html,
                           summary=sum_tbl, styl=styl_html, temp=temp_html)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    return out


_TEMPLATE = """<!doctype html><html lang=es><meta charset=utf-8>
<title>Arqueología Web — dashboard</title><style>
:root{{color-scheme:dark}}body{{background:#0d1117;color:#c9d1d9;font:14px/1.5 system-ui,sans-serif;margin:0;padding:24px;max-width:1100px;margin:auto}}
h1{{font-size:22px}}h2{{font-size:16px;border-bottom:1px solid #30363d;padding-bottom:6px;margin-top:34px}}
h3,h4{{margin:.4em 0;font-size:13px;color:#8b949e;font-weight:600}}
.banner{{background:#2d1b00;border:1px solid #7a5200;color:#e3b341;padding:10px 14px;border-radius:8px;margin:14px 0}}
.cards{{display:flex;gap:14px;flex-wrap:wrap}}.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px 16px;min-width:210px}}
table{{width:100%;border-collapse:collapse}}td,th{{text-align:left;padding:2px 8px;vertical-align:middle}}th{{color:#8b949e;font-weight:600}}
.kv td.v{{text-align:right;color:#e6edf3}}.cmp td.era{{white-space:nowrap}}.two{{display:flex;gap:26px}}.two>div{{flex:1}}
.bar{{display:inline-block;width:120px;height:9px;background:#21262d;border-radius:5px;overflow:hidden;margin-left:8px;vertical-align:middle}}
.bar span{{display:block;height:100%}}.z{{color:#6e7681;margin-left:6px;font-variant-numeric:tabular-nums}}
td.w{{font-family:ui-monospace,monospace;color:#e6edf3}}.note{{color:#6e7681}}footer{{margin-top:40px;color:#6e7681;font-size:12px}}
</style>
<h1>🏺 Arqueología Web — dashboard exploratorio</h1>
<div class=banner><b>Muestra pequeña / ilustrativa.</b> {total} comentarios en {eras} corte(s).
Todo aquí es <b>descriptivo</b>; con este volumen no hay poder estadístico. El diseño válido exige
muestreo estratificado en el tiempo y volumen (ver PLAN.md fase 2 / 7).</div>

<h2>1 · Resumen del corpus por corte</h2><div class=cards>{summary}</div>

<h2>2 · Términos distintivos (log-odds, Fightin' Words)</h2>
<p class=note>Qué palabras caracterizan a cada corte frente al otro (z-score; stopwords filtradas).</p>{logodds}

<h2>3 · Perspectivas (lexicones) — % de comentarios que activan cada eje</h2>
<p class=note>Lexicones ilustrativos y solapados; termómetro, no medida definitiva.</p>{persp}

<h2>4 · Estilo y registro</h2>
<p class=note>Barra normalizada a su propio máximo entre cortes (compara forma, no magnitud absoluta).</p>{styl}

<h2>5 · Distribución temporal de la muestra</h2>
<p class=note>Expone el sesgo de muestreo: si todo cae en pocos minutos, NO es una muestra del año.</p>{temp}

<footer>Generado por arqueo.dashboard · datos en data/normalized · sin dependencias externas</footer>
</html>"""


def _selfcheck():
    recs = [{"text": "government tax war good", "author": "a", "ts": 1325376000},
            {"text": "HELLO money economy?", "author": "b", "ts": 1325376060}]
    s = style(recs)
    assert s["% preguntas"] == 50.0 and s["% grita (MAYÚS)"] == 50.0, s
    assert lexicon_pct(recs, LEXICONS["económico"]) == 100.0   # tax + money/economy
    assert 0 < s["riqueza léxica (TTR)"] <= 1
    print("dashboard OK")


if __name__ == "__main__":
    _selfcheck()
    try:
        print("->", build())
    except SystemExit as e:
        print(e)
