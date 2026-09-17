"""Rebuild the citation graph from the current manuscript + rag.bib.

Emits (into site/data/):
  graph_data.json      -- nodes (cited keys, chapter attribution) + co-citation edges
  graph_positions.json -- spring-layout coordinates

Chapter names follow the post-merge manuscript structure.
"""
import io
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent.parent.parent / "papers" / "RAG_Survey"
DATA = HERE / "data"

CHAPTER_OF = {
    "intro.tex": "Introduction",
    "pipeline.tex": "Components",
    "whole.tex": "System Design",
    "agenticRAG.tex": "Agentic RAG",
    "rlTraining.tex": "Learning",
    "RAG_Evaluation.tex": "Evaluation",
    "future.tex": "Open Challenges",
    "conclusion.tex": "Conclusions",
    "appendix.tex": "Appendix",
    "appendix_curation.tex": "Appendix",
}

MIN_EDGE_WEIGHT = 2

# ── Bib parsing ──────────────────────────────────────────────────────────────

ENTRY = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.S)


def read_braced(text, i):
    """Return (content, next_index) for the brace-balanced group starting at text[i] == '{'."""
    assert text[i] == "{"
    depth, j = 0, i
    while j < len(text):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j], j + 1
        j += 1
    return text[i + 1:], len(text)


def parse_bib(path):
    """bibkey -> {field: value}."""
    text = io.open(path, encoding="utf-8", errors="replace").read()
    out = {}
    pos = 0
    while True:
        m = ENTRY.search(text, pos)
        if not m:
            break
        brace = text.rindex("{", m.start(), m.end())
        body, pos = read_braced(text, brace)
        fields = {}
        k = 0
        while k < len(body):
            fm = re.compile(r"([A-Za-z_]+)\s*=\s*").match(body, k)
            if not fm:
                k += 1
                continue
            k = fm.end()
            if k < len(body) and body[k] == "{":
                val, k = read_braced(body, k)
            elif k < len(body) and body[k] == '"':
                end = body.find('"', k + 1)
                val, k = body[k + 1:end], end + 1
            else:
                end = body.find(",", k)
                val, k = body[k:end], end + 1
            fields[fm.group(1).lower()] = re.sub(r"\s+", " ", val).strip()
        out[m.group(2)] = fields
    return out


# ── Citation scan ────────────────────────────────────────────────────────────

CITE = re.compile(r"\\cite[a-z]?\*?(?:\[[^\]]*\])*\{([^}]*)\}")


def scan_chapter(path):
    """Return (paragraphs, counter) where paragraphs is a list of cited-key lists."""
    text = io.open(path, encoding="utf-8", errors="replace").read()
    # drop comment lines
    text = "\n".join(l for l in text.split("\n") if not l.lstrip().startswith("%"))
    counts = Counter()
    paragraphs = []
    for para in re.split(r"\n\s*\n", text):
        keys = []
        for m in CITE.finditer(para):
            for k in m.group(1).split(","):
                k = k.strip()
                if k:
                    keys.append(k)
                    counts[k] += 1
        if keys:
            paragraphs.append(keys)
    return paragraphs, counts


def main():
    print("Parsing rag.bib ...")
    bib = parse_bib(PAPER / "rag.bib")
    print(f"  {len(bib)} entries")

    counts = Counter()
    chapter_counts = defaultdict(Counter)   # key -> Counter(chapter)
    edges = Counter()                       # (a, b) sorted -> weight

    print("Scanning chapters ...")
    for fname, chapter in CHAPTER_OF.items():
        path = PAPER / "chapters" / fname
        if not path.exists():
            print(f"  !! missing {fname}")
            continue
        paragraphs, c = scan_chapter(path)
        counts.update(c)
        for k, v in c.items():
            chapter_counts[k][chapter] += v
        for keys in paragraphs:
            uniq = sorted(set(keys))
            for i in range(len(uniq)):
                for j in range(i + 1, len(uniq)):
                    edges[(uniq[i], uniq[j])] += 1

    cited = [k for k in counts if k in bib]
    missing = [k for k in counts if k not in bib]
    print(f"Cited keys: {len(counts)}  (in bib: {len(cited)}, unknown: {len(missing)})")
    if missing:
        print("  unknown:", missing[:10])

    # ── Nodes ────────────────────────────────────────────────────────────────
    nodes = []
    for k in cited:
        f = bib[k]
        arxiv = f.get("eprint", "") or ""
        doi = f.get("doi", "") or ""
        if not arxiv:
            m = re.search(r"arxiv[.:/]?\s*(\d{4}\.\d{4,5})", " ".join(f.values()), re.I)
            arxiv = m.group(1) if m else ""
        url = (f"https://arxiv.org/abs/{arxiv}" if arxiv
               else f"https://doi.org/{doi}" if doi
               else f.get("url", "") or "")
        nodes.append({
            "bibkey": k,
            "title": f.get("title", "").replace("{", "").replace("}", ""),
            "year": (f.get("year", "") or "")[:4],
            "arxiv": arxiv,
            "url": url,
            "venue": f.get("booktitle", "") or f.get("journal", "") or "",
            "n_cites": counts[k],
            "primary_chapter": chapter_counts[k].most_common(1)[0][0] if chapter_counts[k] else "Other",
        })
    nodes.sort(key=lambda n: (-n["n_cites"], n["bibkey"]))

    # ── Edges ────────────────────────────────────────────────────────────────
    node_keys = {n["bibkey"] for n in nodes}
    kept = [(a, b, w) for (a, b), w in edges.items()
            if w >= MIN_EDGE_WEIGHT and a in node_keys and b in node_keys]
    print(f"Edges (co-citation >= {MIN_EDGE_WEIGHT}): {len(kept)}")

    # ── Layout ───────────────────────────────────────────────────────────────
    G = nx.Graph()
    G.add_nodes_from(node_keys)
    G.add_weighted_edges_from(kept)
    print(f"Computing layout for {G.number_of_nodes()} nodes / {G.number_of_edges()} edges ...")
    t0 = time.time()
    pos = nx.spring_layout(G, k=0.6, iterations=50, seed=42, weight="weight", scale=1000)
    print(f"  done in {time.time() - t0:.1f}s")

    positions = {k: {"x": round(float(x), 2), "y": round(float(y), 2)} for k, (x, y) in pos.items()}

    per_chapter = Counter(n["primary_chapter"] for n in nodes)

    with io.open(DATA / "graph_data.json", "w", encoding="utf-8") as f:
        json.dump({
            "nodes": nodes,
            "edges": [{"a": a, "b": b, "weight": w} for a, b, w in kept],
            "meta": {
                "total_nodes": len(nodes),
                "total_edges": len(kept),
                "total_citations": sum(counts.values()),
                "min_edge_weight": MIN_EDGE_WEIGHT,
                "per_chapter": per_chapter.most_common(),
            },
        }, f, ensure_ascii=False)
    with io.open(DATA / "graph_positions.json", "w", encoding="utf-8") as f:
        json.dump({"positions": positions, "total_nodes": len(nodes), "total_edges": len(kept)}, f)

    print("\nPapers per chapter:")
    for ch, c in per_chapter.most_common():
        print(f"  {ch}: {c}")
    print(f"\nWrote graph_data.json ({len(nodes)} nodes, {len(kept)} edges) and graph_positions.json")


if __name__ == "__main__":
    main()
