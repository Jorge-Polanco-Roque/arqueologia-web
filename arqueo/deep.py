"""Análisis profundo: léxicos temáticos/cognitivos/expresivos + métricas de forma.

Todo stdlib, todo descriptivo. Los léxicos son ilustrativos y se solapan: son un
termómetro comparativo entre cortes, no una medida canónica. El emparejamiento se
hace por token crudo (sin filtrar stopwords) para no perder palabras función que
aquí SÍ importan (because, always, will, we...).
"""
from __future__ import annotations
import re
from collections import Counter

_W = re.compile(r"[a-z']+")
_SENT = re.compile(r"[.!?]+")


def raw_tokens(text):
    return set(_W.findall(text.lower()))


def group_pct(recs, family):
    """family: {nombre: set(palabras)} -> {nombre: % de comentarios que activan}."""
    n = len(recs) or 1
    return {name: round(100 * sum(1 for r in recs if raw_tokens(r["text"]) & s) / n, 1)
            for name, s in family.items()}


def pair(da, db):
    cats = list(da)
    return {"cats": cats, "a": [da[k] for k in cats], "b": [db[k] for k in cats]}


# ---------- métricas de forma (no léxicas) ----------
def complexity(recs):
    words = longw = sents = commas = 0
    for r in recs:
        ws = r["text"].split()
        words += len(ws)
        longw += sum(1 for w in ws if len(w) > 7)
        sents += max(1, len(_SENT.findall(r["text"])))
        commas += r["text"].count(",")
    return {"% palabra larga (>7)": round(100 * longw / (words or 1), 1),
            "palabras/frase": round(words / (sents or 1), 1),
            "comas/comentario": round(commas / (len(recs) or 1), 1)}


_PAST = {"was", "were", "had", "used", "remember", "ago", "back", "then", "before",
         "once", "did", "been", "past", "history", "old"}
_FUT = {"will", "gonna", "going", "soon", "future", "next", "shall", "tomorrow", "hope"}


def tense(recs):
    c, tot = Counter(), 0
    for r in recs:
        for w in _W.findall(r["text"].lower()):
            tot += 1
            if w in _PAST:
                c["pasado"] += 1
            elif w in _FUT:
                c["futuro"] += 1
    return {"pasado (x1000)": round(1000 * c["pasado"] / (tot or 1), 1),
            "futuro (x1000)": round(1000 * c["futuro"] / (tot or 1), 1)}


def formatting(recs):
    n = len(recs) or 1
    def pct(f):
        return round(100 * sum(1 for r in recs if f(r["text"])) / n, 1)
    emoji = re.compile(r"[:;=]-?[)(DdpP]|[\U00002600-\U0001FAFF]")
    return {"% negrita (**)": pct(lambda t: "**" in t or "__" in t),
            "% enlace": pct(lambda t: "http" in t.lower()),
            "% TLDR/EDIT": pct(lambda t: bool(re.search(r"tl;?dr|edit:", t, re.I))),
            "% ¡exclamación!": pct(lambda t: "!" in t),
            "% emoji/emoticón": pct(lambda t: bool(emoji.search(t)))}


# ---------- familias léxicas ----------
TOPICS = {
    "guerra/militar": {"war", "military", "troops", "army", "iraq", "afghanistan", "ukraine", "russia", "invasion", "soldiers", "drone", "nuclear", "defense", "nato", "putin"},
    "economía": {"economy", "tax", "taxes", "jobs", "wage", "debt", "inflation", "market", "budget", "poverty", "wealth", "income", "price", "gas", "recession"},
    "elecciones": {"vote", "election", "campaign", "ballot", "primary", "candidate", "poll", "polls", "voters", "turnout", "midterms"},
    "medios": {"media", "news", "fox", "cnn", "msnbc", "propaganda", "journalist", "twitter", "facebook", "reddit", "misinformation", "censorship"},
    "ciencia/salud": {"science", "climate", "vaccine", "covid", "health", "pandemic", "research", "study", "doctors", "medicine", "abortion"},
    "religión": {"god", "religion", "christian", "faith", "church", "jesus", "muslim", "atheist", "sin", "holy", "prayer"},
    "raza/identidad": {"race", "racist", "racism", "black", "white", "immigrant", "gender", "women", "gay", "trans", "minority", "diversity"},
    "ley/derechos": {"law", "rights", "constitution", "court", "supreme", "amendment", "liberty", "justice", "legal", "police", "trial"},
    "conspiración": {"conspiracy", "sheep", "sheeple", "agenda", "hoax", "rigged", "corrupt", "elite", "cover", "wake", "puppet"},
    "clase/trabajo": {"worker", "workers", "class", "union", "corporate", "capitalism", "billionaire", "wealthy", "poor", "wallstreet", "labor"},
}
ENTITIES = {
    "Obama": {"obama"}, "Bush": {"bush"}, "Romney": {"romney"}, "Ron Paul": {"ron", "paul"},
    "Clinton/Hillary": {"clinton", "hillary"}, "Trump": {"trump"}, "Biden": {"biden"},
    "Putin": {"putin"}, "Bernie": {"bernie", "sanders"}, "AOC": {"aoc"}, "Manning": {"manning"},
    "Assange/Snowden": {"assange", "snowden"}, "Pelosi": {"pelosi"}, "Tulsi": {"tulsi"},
    "Congreso": {"congress", "senate", "senator"},
}
COGNITION = {
    "razonamiento": {"because", "therefore", "thus", "however", "although", "since", "hence", "whereas", "reason", "argument", "logic", "consequently"},
    "evidencia": {"source", "evidence", "proof", "study", "data", "cite", "according", "statistics", "fact", "facts", "research", "link"},
    "certeza": {"obviously", "clearly", "definitely", "certainly", "always", "never", "undeniable", "everyone", "nobody", "absolutely", "literally", "obvious"},
    "duda/matiz": {"maybe", "perhaps", "probably", "might", "seems", "guess", "suppose", "likely", "possibly", "arguably", "somewhat", "unsure"},
}
EXPRESSION = {
    "slang": {"lol", "lmao", "tbh", "ngl", "imo", "imho", "based", "cringe", "woke", "sus", "salty", "rekt", "pwned", "epic", "meh", "bruh", "yikes", "oof", "vibe", "lit", "normie", "simp", "cope", "ratio", "bro", "dude", "af"},
    "insultos": {"idiot", "moron", "stupid", "dumb", "sheep", "shill", "snowflake", "fascist", "nazi", "clown", "loser", "coward", "scum", "trash", "pathetic", "delusional", "brainwashed", "cult", "asshole"},
    "ironía": {"sure", "totally", "yeah", "wow", "genius", "brilliant", "great", "shocking", "obviously"},
    "profanidad": {"damn", "shit", "fuck", "fucking", "fucked", "crap", "hell", "ass", "bullshit", "bitch"},
}
VALUES = {
    "libertad": {"freedom", "liberty", "free", "rights", "individual", "choice"},
    "seguridad": {"security", "safety", "protect", "order", "defense", "threat", "danger"},
    "igualdad": {"equality", "equal", "fair", "fairness", "justice"},
    "tradición": {"tradition", "family", "faith", "values", "heritage", "moral", "church"},
    "progreso": {"progress", "change", "future", "reform", "modern", "forward", "innovation"},
    "nación": {"nation", "country", "american", "patriot", "america", "flag", "border"},
}
AFFECT = {
    "optimismo": {"hope", "better", "progress", "win", "improve", "future", "opportunity", "together", "good", "great"},
    "pesimismo": {"doom", "decline", "collapse", "worse", "hopeless", "fail", "corrupt", "broken", "dead", "crisis", "disaster", "afraid"},
}


# ---------- perfil psicológico (estilo LIWC; proxies léxicos, no instrumento validado) ----------
EMOTION = {
    "ira": {"angry", "anger", "hate", "mad", "furious", "rage", "pissed", "outrage", "disgust", "hostile", "fuck"},
    "ansiedad": {"afraid", "fear", "worried", "anxious", "nervous", "scared", "panic", "threat", "risk", "danger"},
    "tristeza": {"sad", "cry", "depressed", "grief", "hopeless", "miserable", "lonely", "hurt", "pain", "loss"},
    "emoción positiva": {"happy", "love", "hope", "great", "good", "glad", "proud", "enjoy", "wonderful", "nice"},
}
COGPROC = {
    "insight": {"think", "know", "realize", "understand", "consider", "believe", "aware", "sense", "notice"},
    "causación": {"because", "cause", "effect", "reason", "therefore", "thus", "since", "hence", "due", "leads"},
    "tentativo": {"maybe", "perhaps", "guess", "suppose", "seems", "might", "probably", "possibly", "unsure"},
    "diferenciación": {"but", "however", "although", "else", "without", "except", "though", "whereas", "unless"},
    "absolutismo": {"all", "always", "never", "none", "nothing", "everyone", "everything", "nobody", "totally", "completely", "absolute", "entire"},
}
BIG5 = {
    "Apertura": {"think", "idea", "perspective", "consider", "understand", "question", "imagine", "curious", "insight", "realize", "nuance", "complex"},
    "Responsabilidad": {"should", "must", "plan", "work", "responsibility", "duty", "order", "rule", "achieve", "complete", "careful"},
    "Extraversión": {"we", "us", "people", "together", "social", "talk", "share", "friend", "party", "everyone", "community"},
    "Amabilidad": {"thanks", "thank", "agree", "please", "help", "kind", "appreciate", "fair", "support", "respect", "sorry"},
    "Neuroticismo": {"angry", "afraid", "hate", "fear", "worried", "anxious", "sad", "hopeless", "stress", "upset", "outrage", "disgust"},
}


def top_terms(recs, n=14):
    """Palabras de contenido más frecuentes (stopwords filtradas) -> conceptos predominantes."""
    from collections import Counter
    from .analyze import tokenize
    c = Counter()
    for r in recs:
        c.update(tokenize(r["text"]))
    return c.most_common(n)


def group_rate(recs, family):
    """Como group_pct pero por MIL PALABRAS (densidad) -> robusto a la longitud."""
    tot = 0
    c = {name: 0 for name in family}
    for r in recs:
        for w in _W.findall(r["text"].lower()):
            tot += 1
            for name, s in family.items():
                if w in s:
                    c[name] += 1
    return {name: round(1000 * c[name] / (tot or 1), 1) for name in family}


def trigrams(text):
    from .analyze import tokenize
    t = tokenize(text)
    return [f"{t[i]} {t[i+1]} {t[i+2]}" for i in range(len(t) - 2)]


def _syll(w):
    g = re.findall(r"[aeiouy]+", w.lower())
    n = len(g) - (1 if w.lower().endswith("e") else 0)
    return max(1, n)


def readability(recs):
    """Facilidad de lectura Flesch (mayor = más fácil) + sus componentes."""
    words = sents = syl = 0
    for r in recs:
        ws = _W.findall(r["text"])
        words += len(ws)
        sents += max(1, len(_SENT.findall(r["text"])))
        syl += sum(_syll(w) for w in ws)
    wps, spw = words / (sents or 1), syl / (words or 1)
    return {"Flesch (facilidad)": round(206.835 - 1.015 * wps - 84.6 * spw, 1),
            "palabras/frase": round(wps, 1), "sílabas/palabra": round(spw, 2)}


def lexdiv(recs):
    """Diversidad léxica robusta: TTR medio por comentario + rareza (hapax)."""
    from collections import Counter
    from .analyze import tokenize
    ttrs, allc = [], Counter()
    for r in recs:
        t = tokenize(r["text"])
        if len(t) >= 10:
            ttrs.append(len(set(t)) / len(t))
        allc.update(t)
    hapax = sum(1 for _, c in allc.items() if c == 1) / (len(allc) or 1)
    return {"TTR por comentario": round(sum(ttrs) / (len(ttrs) or 1), 3),
            "Rareza (hapax)": round(hapax, 3)}


def hour_hist(recs):
    from datetime import datetime, timezone
    from collections import Counter
    c = Counter(datetime.fromtimestamp(r["ts"], timezone.utc).hour for r in recs)
    n = len(recs) or 1
    return {f"{h:02d}": round(100 * c.get(h, 0) / n, 1) for h in range(24)}


def length_buckets(recs):
    labs = ["1–10", "11–25", "26–50", "51–100", "100+"]
    from collections import Counter
    b = Counter()
    n = len(recs) or 1
    for r in recs:
        w = len(r["text"].split())
        b[labs[0] if w <= 10 else labs[1] if w <= 25 else labs[2] if w <= 50 else labs[3] if w <= 100 else labs[4]] += 1
    return {l: round(100 * b[l] / n, 1) for l in labs}


_WE = {"we", "us", "our", "ours"}
_THEY = {"they", "them", "their", "theirs"}


def polarization(recs):
    we = they = tot = 0
    for r in recs:
        for w in _W.findall(r["text"].lower()):
            tot += 1
            if w in _WE:
                we += 1
            elif w in _THEY:
                they += 1
    return {"Ellos / (nosotros+ellos) %": round(100 * they / ((we + they) or 1), 1),
            "Exogrupo (x1000)": round(1000 * they / (tot or 1), 1),
            "Endogrupo (x1000)": round(1000 * we / (tot or 1), 1)}


def _selfcheck():
    recs = [{"text": "We must protect freedom because the evidence is clear. Obviously!"},
            {"text": "lol trump is an idiot tbh, war in ukraine 😂"}]
    assert group_pct([recs[0]], VALUES)["libertad"] == 100.0
    assert group_pct([recs[1]], EXPRESSION)["slang"] == 100.0
    assert group_pct([recs[1]], TOPICS)["guerra/militar"] == 100.0
    assert complexity(recs)["palabras/frase"] > 0
    assert formatting([recs[1]])["% emoji/emoticón"] == 100.0
    print("deep OK")


if __name__ == "__main__":
    _selfcheck()
