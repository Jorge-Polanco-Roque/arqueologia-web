"""CLI mínima: ata ingesta -> almacén -> comparación.

  python -m arqueo.cli ingest usenet dumps/comp.lang.c.mbox
  python -m arqueo.cli ingest reddit dumps/programming_comments.zst
  python -m arqueo.cli compare --platform reddit --community programming
"""
from __future__ import annotations
import argparse
import os
from . import core, ingest, analyze


def main(argv=None):
    p = argparse.ArgumentParser(prog="arqueo")
    sub = p.add_subparsers(dest="cmd", required=True)

    pd = sub.add_parser("download", help="descarga una fuente a data/raw/ (crudo)")
    pd.add_argument("source", choices=["reddit", "hn"])
    pd.add_argument("--subreddit")               # reddit
    pd.add_argument("--year", type=int)          # reddit
    pd.add_argument("--kind", choices=["comments", "posts"], default="comments")
    pd.add_argument("--max", type=int, dest="max_items")   # tope simple (sesga al inicio del año)
    pd.add_argument("--per-month", type=int, dest="per_month")  # muestra estratificada por mes
    pd.add_argument("--years", default="2012,2022")        # hn

    pi = sub.add_parser("ingest", help="normaliza una fuente a JSONL")
    pi.add_argument("source", choices=["usenet", "reddit", "hn"])
    pi.add_argument("path")
    pi.add_argument("--lang", default="en")

    sub.add_parser("dashboard", help="genera data/dashboard.html (vista rápida)")
    sub.add_parser("report", help="genera data/report.html (análisis profundo)")
    sub.add_parser("ui", help="genera data/ui.html (UI gráfica con ECharts)")

    pc = sub.add_parser("compare", help="log-odds de un corte vs otro")
    pc.add_argument("--era-a", default="2012")
    pc.add_argument("--era-b", default="2022")
    pc.add_argument("--platform")
    pc.add_argument("--community")
    pc.add_argument("--top", type=int, default=30)

    a = p.parse_args(argv)

    if a.cmd == "download":
        if a.source == "reddit":
            from . import download_reddit
            n, out = download_reddit.to_file(a.subreddit, a.year, a.kind,
                                             max_items=a.max_items, per_month=a.per_month)
        else:
            from . import download_hn
            n, out = download_hn.download(years=tuple(int(y) for y in a.years.split(",")))
        print(f"{n} -> {out}")

    elif a.cmd == "ingest":
        gen = {"usenet": ingest.from_usenet_mbox, "reddit": ingest.from_reddit_dump,
               "hn": ingest.from_hn}[a.source]
        stem = os.path.splitext(os.path.basename(a.path))[0]
        out = f"data/normalized/{a.source}/{stem}.jsonl"
        n = core.write_jsonl(gen(a.path, lang=a.lang), out)
        print(f"{n} registros -> {out}")

    elif a.cmd == "dashboard":
        from . import dashboard
        print(f"dashboard -> {dashboard.build()}")

    elif a.cmd == "report":
        from . import report
        print(f"report -> {report.build()}")

    elif a.cmd == "ui":
        from . import ui
        print(f"ui -> {ui.build()}")

    elif a.cmd == "compare":
        con = core.db()
        res = analyze.compare_eras(con, era_a=a.era_a, era_b=a.era_b,
                                   platform=a.platform, community=a.community, top=a.top)
        print(f"\n== Más característico de {a.era_a} ==")
        for w, s in res["a_distinctive"]:
            print(f"  {s:+6.1f}  {w}")
        print(f"\n== Más característico de {a.era_b} ==")
        for w, s in res["b_distinctive"]:
            print(f"  {s:+6.1f}  {w}")


if __name__ == "__main__":
    main()
