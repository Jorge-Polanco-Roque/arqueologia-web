"""Batería de contrastes 2012 vs 2022 sobre el corpus, con test real y FDR.

Cada métrica se contrasta con el test adecuado a su naturaleza:
- densidad por token y presencia por comentario  -> z de dos proporciones + Cohen's h
- métricas continuas por comentario              -> Mann-Whitney U + Cliff's delta
Luego se corrige por comparaciones múltiples (Benjamini-Hochberg) y el veredicto
se decide por TAMAÑO DE EFECTO, no por p (con n grande casi todo sale p<0.05).
"""
from __future__ import annotations
from collections import Counter

from .analyze import tokenize
from .deep import (raw_tokens, _W, EXPRESSION, COGPROC, COGNITION, TOPICS, ENTITIES, _WE, _THEY)
from .stats import two_proportion, mann_whitney, bh_fdr, mag_h, mag_delta


def _tokcount(recs):
    c, tot = Counter(), 0
    for r in recs:
        for w in _W.findall(r["text"].lower()):
            c[w] += 1
            tot += 1
    return c, tot


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return 0
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def _ttr(recs):
    out = []
    for r in recs:
        t = tokenize(r["text"])
        if len(t) >= 10:
            out.append(len(set(t)) / len(t))
    return out


def _pred(lex):
    return lambda s: bool(raw_tokens(s) & lex)


def _verdict(q, mag):
    if q >= 0.05:
        return "no significativo"
    return f"significativo · efecto {mag}"


def battery(ra, rb):
    ca, ta = _tokcount(ra)
    cb, tb = _tokcount(rb)
    rows = []

    def add(name, unit, ea, eb, eff, mag, p, ci):
        rows.append({"name": name, "unit": unit, "a": ea, "b": eb, "eff": eff,
                     "mag": mag, "p": p, "ci": ci})

    # densidad por mil tokens
    for name, lex in [("Slang", EXPRESSION["slang"]), ("Insultos", EXPRESSION["insultos"]),
                      ("Profanidad", EXPRESSION["profanidad"]), ("Absolutismo", COGPROC["absolutismo"]),
                      ("Exogrupo (ellos)", _THEY), ("Endogrupo (nosotros)", _WE),
                      ("Razonamiento", COGNITION["razonamiento"]), ("Evidencia", COGNITION["evidencia"])]:
        xa = sum(ca[w] for w in lex)
        xb = sum(cb[w] for w in lex)
        t = two_proportion(xa, ta, xb, tb)   # h: positivo = mayor en 2022
        add(name, "‰ tokens", round(xa / ta * 1000, 2), round(xb / tb * 1000, 2),
            t["h"], mag_h(t["h"]), t["p"], (round(t["ci"][0] * 1000, 2), round(t["ci"][1] * 1000, 2)))

    # presencia por comentario (%)
    for name, pred in [("Preguntas (?)", lambda s: "?" in s),
                       ("MAYÚSCULAS", lambda s: any(w.isupper() and len(w) >= 4 for w in s.split())),
                       ("Enlace", lambda s: "http" in s.lower()),
                       ("Negrita (**)", lambda s: "**" in s),
                       ("Tema: guerra/militar", _pred(TOPICS["guerra/militar"])),
                       ("Tema: ley/derechos", _pred(TOPICS["ley/derechos"])),
                       ("Tema: economía", _pred(TOPICS["economía"])),
                       ("Menciona a Trump", _pred(ENTITIES["Trump"])),
                       ("Menciona a Obama", _pred(ENTITIES["Obama"]))]:
        xa = sum(1 for r in ra if pred(r["text"]))
        xb = sum(1 for r in rb if pred(r["text"]))
        t = two_proportion(xa, len(ra), xb, len(rb))
        add(name, "% coment.", round(xa / len(ra) * 100, 1), round(xb / len(rb) * 100, 1),
            t["h"], mag_h(t["h"]), t["p"], (round(t["ci"][0] * 100, 1), round(t["ci"][1] * 100, 1)))

    # continuas por comentario (Mann-Whitney; eff = -cliff para que + sea "mayor en 2022")
    wa = [len(r["text"].split()) for r in ra]
    wb = [len(r["text"].split()) for r in rb]
    mw = mann_whitney(wa, wb)
    add("Palabras/comentario (mediana)", "palabras", _median(wa), _median(wb),
        -mw["cliff"], mag_delta(mw["cliff"]), mw["p"], None)
    ta_, tb_ = _ttr(ra), _ttr(rb)
    mw2 = mann_whitney(ta_, tb_)
    add("TTR/comentario (mediana)", "ratio", round(_median(ta_), 3), round(_median(tb_), 3),
        -mw2["cliff"], mag_delta(mw2["cliff"]), mw2["p"], None)

    for r, q in zip(rows, bh_fdr([r["p"] for r in rows])):
        r["q"] = q
        r["sig"] = q < 0.05
        r["verdict"] = _verdict(q, r["mag"])
    rows.sort(key=lambda r: abs(r["eff"]), reverse=True)
    return rows


if __name__ == "__main__":
    import sys, json
    from .dashboard import load, by_era
    from .ui import humans
    eras = {e: humans(r) for e, r in by_era(load()).items()}
    ks = list(eras)
    rows = battery(eras[ks[0]], eras[ks[-1]])
    w = max(len(r["name"]) for r in rows)
    print(f"{'métrica':<{w}}  {'2012':>8} {'2022':>8}  {'efecto':>7} {'p':>9} {'q(FDR)':>8}  veredicto")
    print("-" * (w + 60))
    for r in rows:
        pfmt = f"{r['p']:.1e}" if r['p'] < 0.001 else f"{r['p']:.3f}"
        qfmt = f"{r['q']:.1e}" if r['q'] < 0.001 else f"{r['q']:.3f}"
        print(f"{r['name']:<{w}}  {r['a']:>8} {r['b']:>8}  {r['eff']:>+7.3f} {pfmt:>9} {qfmt:>8}  {r['verdict']}")
