"""Build the slim web catalog (data/catalog.json) from the full library data.

Reads data/papers_full.json and writes a deploy-friendly catalog: no local PDF
paths (they are not shipped to the public site), trimmed abstracts, one URL per
paper (arXiv, falling back to DOI).

Usage: python build_catalog.py
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "data" / "papers_full.json"
OUT = HERE / "data" / "catalog.json"

ABSTRACT_CHARS = 600


def authors_str(a):
    if isinstance(a, list):
        a = ", ".join(str(x) for x in a)
    a = str(a or "").strip()
    return a if len(a) <= 140 else a[:137].rstrip() + "…"


def main():
    papers = json.loads(SRC.read_text(encoding="utf-8"))
    out = []
    for p in papers:
        url = (p.get("arxiv_url") or "").strip()
        if not url:
            doi = (p.get("doi") or "").strip()
            url = f"https://doi.org/{doi}" if doi else ""
        abstract = (p.get("abstract") or "").strip()
        if len(abstract) > ABSTRACT_CHARS:
            abstract = abstract[:ABSTRACT_CHARS].rsplit(" ", 1)[0] + "…"
        out.append({
            "id": p.get("id"),
            "title": (p.get("title") or "").strip(),
            "authors": authors_str(p.get("authors")),
            "year": str(p.get("year") or "").strip(),
            "venue": (p.get("venue_short") or p.get("venue") or "").strip(),
            "url": url,
            "cluster": p.get("cluster_id") or "",
            "cluster_name": p.get("cluster_name") or "",
            "has_note": bool(p.get("has_note")),
            "abstract": abstract,
        })
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    n_note = sum(1 for p in out if p["has_note"])
    n_url = sum(1 for p in out if p["url"])
    print(f"Wrote {OUT} ({len(out)} papers, {n_note} with notes, "
          f"{n_url} with a link, {OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
