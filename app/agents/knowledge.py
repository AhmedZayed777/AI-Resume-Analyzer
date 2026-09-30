import re

from .. import db as dbm

SEED_DOCS = [f"{title}: {content}" for _, title, content in dbm.SEED_KNOWLEDGE]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9\+#\.]+", text.lower()))


def _all_docs() -> list[str]:
    try:
        with dbm.get_db() as conn:
            rows = conn.execute("SELECT title, content FROM knowledge").fetchall()
        if rows:
            return [f"{row['title']}: {row['content']}" for row in rows]
    except Exception:
        pass
    return list(SEED_DOCS)


def retrieve(query: str, k: int = 4) -> list[str]:
    docs = _all_docs()
    q = _tokens(query)
    scored = [(len(q & _tokens(doc)), doc) for doc in docs]
    scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [doc for _, doc in scored[:k]]
