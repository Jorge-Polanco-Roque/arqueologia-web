"""Conectores de ingesta. Cada uno normaliza una fuente -> Record.

Patrón para añadir fuente: escribe una función que produzca Records y reúsa
core.write_jsonl. Empezamos con las dos elegidas: Usenet (el "antes") y Reddit
(el "después"). Wayback/foros ES: mismo patrón, ver PLAN.md fase 1.
"""
from __future__ import annotations
import gzip
import email
import email.utils
import html
import re
from .core import Record

_HTML_TAG = re.compile(r"<[^>]+>")


def _iter_mbox(path: str):
    """Itera mensajes de un mbox (plano o .gz) por streaming, dividiendo en la
    línea envoltorio 'From '. No carga el archivo entero -> soporta volcados de GB."""
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="latin-1", errors="replace") as f:
        buf = None
        for line in f:
            if line.startswith("From "):          # delimitador de mensaje (no la cabecera 'From:')
                if buf is not None:
                    yield email.message_from_string("".join(buf))
                buf = []                           # descarta la línea envoltorio
            elif buf is not None:
                buf.append(line)
        if buf:
            yield email.message_from_string("".join(buf))


def from_usenet_mbox(path: str, lang: str = "en"):
    """Usenet en mbox plano o .gz (dumps de archive.org / Giganews, Google Groups)."""
    for msg in _iter_mbox(path):
        parsed = email.utils.parsedate_tz(msg.get("Date", ""))
        if not parsed:
            continue
        ts = email.utils.mktime_tz(parsed)
        refs = (msg.get("References", "") or "").split()
        yield Record(
            id=msg.get("Message-ID", "") or "",
            platform="usenet",
            community=(msg.get("Newsgroups", "") or "").split(",")[0].strip(),
            author=email.utils.parseaddr(msg.get("From", ""))[1] or "anon",
            ts=ts,
            text=_body(msg),
            lang=lang,
            parent_id=refs[-1] if refs else None,
        )


def _body(msg) -> str:
    if msg.is_multipart():
        for p in msg.walk():
            if p.get_content_type() == "text/plain":
                payload = p.get_payload(decode=True)
                return payload.decode("latin-1", "replace") if payload else ""
        return ""
    payload = msg.get_payload(decode=True)
    return payload.decode("latin-1", "replace") if payload else (msg.get_payload() or "")


def from_reddit_dump(path: str, lang: str = "en"):
    """Dumps de Reddit: ndjson (comentarios o submissions), plano/.gz/.zst."""
    for obj in _iter_ndjson(path):
        text = obj.get("body") or (obj.get("title", "") + "\n" + obj.get("selftext", "")).strip()
        if not text or obj.get("author") in (None, "[deleted]", "[removed]"):
            continue
        yield Record(
            id=obj.get("id", "") or "",
            platform="reddit",
            community=obj.get("subreddit", "") or "",
            author=obj.get("author", "") or "anon",
            ts=int(obj.get("created_utc", 0) or 0),
            text=text,
            lang=lang,
            parent_id=obj.get("parent_id"),
            url=obj.get("permalink"),
        )


def from_hn(path: str, lang: str = "en"):
    """Hacker News desde export NDJSON de BigQuery (`hacker_news.full`).

    Campos: id, by, time, text, title, parent, type. Una sola comunidad
    ('hackernews'). El `text` viene con HTML (entidades + <p>/<a>/<i>) -> se
    desescapa y se quitan tags antes de normalizar. Stories sin texto usan el
    título como contenido (representa el tema del hilo).
    """
    for obj in _iter_ndjson(path):
        if obj.get("type") not in ("comment", "story"):
            continue
        raw = obj.get("text") or obj.get("title") or ""
        if not raw or not obj.get("by"):
            continue
        text = _HTML_TAG.sub(" ", html.unescape(raw))
        parent = obj.get("parent")
        yield Record(
            id=str(obj.get("id", "")),
            platform="hn",
            community="hackernews",
            author=obj.get("by", "") or "anon",
            ts=int(obj.get("time", 0) or 0),   # bq exporta INT64 como string; int() lo absorbe
            text=text,
            lang=lang,
            parent_id=str(parent) if parent is not None else None,
            url=obj.get("url"),
        )


def _iter_ndjson(path: str):
    import json
    if path.endswith(".zst"):
        import zstandard, io
        raw = zstandard.ZstdDecompressor(max_window_size=2**31).stream_reader(open(path, "rb"))
        f = io.TextIOWrapper(raw, encoding="utf-8", errors="replace")
    elif path.endswith(".gz"):
        import gzip
        f = gzip.open(path, "rt", encoding="utf-8", errors="replace")
    else:
        f = open(path, "rt", encoding="utf-8", errors="replace")
    with f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue


def _selfcheck():
    import tempfile, os, json
    d = tempfile.mkdtemp()

    rp = os.path.join(d, "r.ndjson")
    with open(rp, "w") as f:
        f.write(json.dumps({"id": "a1", "subreddit": "test", "author": "u",
                            "created_utc": 1640995200, "body": "hello world"}) + "\n")  # 2022
    recs = list(from_reddit_dump(rp))
    assert len(recs) == 1 and recs[0].era == "2022" and recs[0].platform == "reddit", recs

    mp = os.path.join(d, "u.mbox")
    with open(mp, "w") as f:
        f.write("From x\nMessage-ID: <1@x>\nFrom: bob <bob@x.net>\n"
                "Newsgroups: comp.lang.c\nDate: Fri, 01 Jun 2007 00:00:00 +0000\n\n"
                "hello usenet\n")
    recs = list(from_usenet_mbox(mp))
    assert len(recs) == 1 and recs[0].era == "2007" and recs[0].author == "bob@x.net", recs

    gp = os.path.join(d, "u.mbox.gz")               # dos mensajes comprimidos, distinto año
    with gzip.open(gp, "wt", encoding="latin-1") as f:
        f.write("From x\nMessage-ID: <2@x>\nFrom: al <al@x.net>\nNewsgroups: sci.econ\n"
                "Date: Wed, 01 Jan 2003 00:00:00 +0000\n\ninflation talk\n"
                "From y\nMessage-ID: <3@x>\nFrom: bo <bo@x.net>\nNewsgroups: sci.econ\n"
                "Date: Fri, 01 Jun 2007 00:00:00 +0000\n\nmore econ\n")
    recs = list(from_usenet_mbox(gp))
    assert len(recs) == 2 and recs[0].era is None and recs[1].era == "2007", [r.era for r in recs]

    hp = os.path.join(d, "hn.ndjson")
    with open(hp, "w") as f:
        f.write(json.dumps({"id": 1, "type": "comment", "by": "pg",
                            "time": 1325376000, "text": "I&#x27;d use <i>C</i> here",
                            "parent": 99}) + "\n")           # 2012
        f.write(json.dumps({"id": 2, "type": "story", "by": "sama",
                            "title": "Show HN: my app", "time": 1640995200}) + "\n")  # 2022
    recs = list(from_hn(hp))
    assert len(recs) == 2, recs
    c = recs[0]
    assert c.platform == "hn" and c.era == "2012" and c.parent_id == "99", c
    assert c.text == "I'd use C here", repr(c.text)   # HTML desescapado y sin tags
    assert recs[1].era == "2022" and recs[1].text == "Show HN: my app", recs[1]
    print("ingest OK")


if __name__ == "__main__":
    _selfcheck()
