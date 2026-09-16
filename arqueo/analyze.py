"""Comparación diacrónica.

Capa barata (sin deps): log-odds con prior de Dirichlet (Monroe et al. 2008,
"Fightin' Words") — qué palabras/temas distinguen una era de otra, con z-score
para no dejarse engañar por palabras raras. Es el caballo de batalla.

Capas ML (embeddings, BERTopic dinámico, cambio semántico diacrónico) y matiz
por LLM: import perezoso, ver PLAN.md fases 4–6.
"""
from __future__ import annotations
import re
import math
from collections import Counter

_TOK = re.compile(r"[a-zA-Z']+")

# Palabras función / genéricas: ruido en log-odds. NO incluye palabras con carga
# (war, money, democrats, freedom...) que sí son señal sociológica.
STOPWORDS = {
    "the", "and", "but", "for", "are", "was", "you", "your", "not", "have", "has",
    "had", "this", "that", "these", "those", "with", "from", "they", "them", "their",
    "there", "here", "what", "when", "which", "who", "will", "would", "can", "could",
    "should", "its", "his", "her", "him", "she", "our", "out", "about", "into", "than",
    "then", "also", "just", "like", "very", "much", "more", "most", "some", "any", "all",
    "one", "get", "got", "going", "gonna", "want", "know", "think", "make", "made",
    "even", "still", "back", "being", "been", "because", "while", "after", "before",
    "over", "under", "such", "same", "other", "each", "how", "why", "where", "now",
    "too", "yeah", "lol", "dont", "doesnt", "cant", "wont", "didnt", "isnt", "youre",
    "thats", "theyre", "were", "does", "did", "say", "said", "way", "see", "let",
    "may", "many", "off", "own", "via", "yet", "per", "etc", "actually", "something",
    "someone", "anything", "everything", "http", "https", "www", "com",
}


def tokenize(text: str, drop_stop: bool = True):
    ws = (w.lower() for w in _TOK.findall(text) if len(w) > 2)
    return [w for w in ws if not (drop_stop and w in STOPWORDS)]


def log_odds(texts_a, texts_b, prior: float = 0.01, top: int = 30, tok=None):
    """Términos más característicos de A vs B (z-score de log-odds con prior).

    Devuelve {'a_distinctive': [(palabra, z)...], 'b_distinctive': [...]}.
    z alto en a_distinctive = propio de A; z bajo (negativo) = propio de B.
    `tok`: tokenizador (por defecto unigramas); pásale uno de bigramas para colocaciones.
    """
    tok = tok or tokenize
    ca, cb = Counter(), Counter()
    for t in texts_a:
        ca.update(tok(t))
    for t in texts_b:
        cb.update(tok(t))
    vocab = set(ca) | set(cb)
    na, nb = sum(ca.values()), sum(cb.values())
    a0 = prior * len(vocab)
    scores = {}
    for w in vocab:
        ya, yb = ca[w] + prior, cb[w] + prior
        delta = math.log(ya / (na + a0 - ya)) - math.log(yb / (nb + a0 - yb))
        var = 1.0 / ya + 1.0 / yb
        scores[w] = delta / math.sqrt(var)
    ranked = sorted(scores.items(), key=lambda kv: kv[1])
    return {"b_distinctive": ranked[:top], "a_distinctive": ranked[-top:][::-1]}


def compare_eras(con, era_a="2012", era_b="2022", platform=None, community=None, sample=50000, top=30):
    """log-odds del corte era_a vs era_b sobre el corpus DuckDB.

    a_distinctive = propio de era_a; b_distinctive = propio de era_b.
    Sin platform= AVISA: comparar entre plataformas confunde plataforma+población
    con era (ver CLAUDE.md § Confusores). Una comparación válida fija platform=.
    """
    where = ["era IS NOT NULL"]
    if platform:
        where.append(f"platform = '{platform}'")
    if community:
        where.append(f"community = '{community}'")
    w = " AND ".join(where)

    def texts(era):
        # ponytail: random()+LIMIT ordena todo; si el corpus es enorme, cambia a
        # 'USING SAMPLE n ROWS' (muestreo por reservorio, sin sort).
        q = f"SELECT text FROM corpus WHERE {w} AND era='{era}' ORDER BY random() LIMIT {sample}"
        return [r[0] for r in con.execute(q).fetchall()]

    if not platform:
        print("AVISO: comparación entre plataformas -> confunde plataforma+población "
              "con era. Fija platform= para un contraste válido (CLAUDE.md § Confusores).")
    return log_odds(texts(era_a), texts(era_b), top=top)


# --- Hooks de la capa ML (import perezoso; ver PLAN.md) --------------------
def embed(texts, model="all-MiniLM-L6-v2"):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model).encode(list(texts), show_progress_bar=True)


def semantic_change(texts_a, texts_b, words, dim=100):
    """Cambio de significado por era: word2vec por corpus + alineación Procrustes
    (método HistWords). Devuelve distancia coseno del vector de cada palabra.
    ponytail: esqueleto; afinar min_count/epochs con datos reales."""
    from gensim.models import Word2Vec
    import numpy as np
    def train(texts):
        sents = [tokenize(t) for t in texts]
        return Word2Vec(sents, vector_size=dim, min_count=5, workers=4)
    ma, mb = train(texts_a), train(texts_b)
    shared = [w for w in words if w in ma.wv and w in mb.wv]
    A = np.array([ma.wv[w] for w in shared]); B = np.array([mb.wv[w] for w in shared])
    # Procrustes: rota B para alinearlo con A
    U, _, Vt = np.linalg.svd(B.T @ A)
    R = U @ Vt
    Br = B @ R
    return {w: float(1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
            for w, a, b in zip(shared, A, Br)}


def _selfcheck():
    early = ["compiled program unix mainframe university kernel"] * 20
    modern = ["posted meme phone based tiktok crypto"] * 20
    early_vocab, modern_vocab = set(tokenize(early[0])), set(tokenize(modern[0]))
    out = log_odds(early, modern, top=5)
    a_words = {w for w, _ in out["a_distinctive"]}
    b_words = {w for w, _ in out["b_distinctive"]}
    # cada lado debe caracterizar SU corpus, sin fugas al otro
    assert a_words <= early_vocab, a_words - early_vocab
    assert b_words <= modern_vocab, b_words - modern_vocab
    print("analyze OK")


if __name__ == "__main__":
    _selfcheck()
