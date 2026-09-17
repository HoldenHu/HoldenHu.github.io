"""Extract the survey's numbered research questions (Q26-Q91) from the LaTeX manuscript.

Reads the merged manuscript at papers/RAG_Survey/chapters/ and writes data/questions.json
for the companion website. Read-only with respect to the manuscript.

Usage: python extract_questions.py
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent.parent          # .../research-bot
CHAPTERS = REPO / "papers" / "RAG_Survey" / "chapters"
OUT = HERE / "data" / "questions.json"

# Which chapter files carry numbered questions, and how to label them on the site.
CHAPTER_META = [
    ("whole.tex",          "design",   3, "System Design and Coordination",
     "Design & Coordination", "From components to working systems: composition, resources, workloads."),
    ("agenticRAG.tex",     "runtime",  4, "Agentic RAG: Runtime Control, Memory, and Collaboration",
     "Runtime Control", "When the coordination itself becomes adaptive: search, memory, multi-agent work."),
    ("RAG_Evaluation.tex", "eval",     6, "Evaluation of RAG: Objects, Quality Dimensions, Settings, and Methods",
     "Evaluation", "What an evaluation claim actually establishes, from source defects to end-to-end success."),
    ("future.tex",         "open",     7, "Open Challenges and Future Directions",
     "Open Frontiers", "The questions the field has not answered yet."),
]

MACRO = re.compile(r"\\(focalquestion|openresearchquestion)\{")
SEC = re.compile(r"\\(?:sub)*section\*?\{")
TITLE_OF = re.compile(r"\\(?:sub)*section\*?\{(.+?)\}\s*$", re.M)


def read_braced(s, i):
    """Return (content, end_index) for the brace group starting at s[i] == '{'."""
    assert s[i] == "{"
    depth, j = 0, i
    while j < len(s):
        if s[j] == "\\":          # skip escaped char (e.g. \%, \{)
            j += 2
            continue
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    raise ValueError("unbalanced braces")


def clean(tex):
    """LaTeX -> readable plain text for the web."""
    t = tex
    t = re.sub(r"\\cite[a-z]*\{[^}]*\}", "", t)          # citations out
    t = re.sub(r"\\Qref\{([^}]*)\}", r"\1", t)           # question refs
    t = re.sub(r"\\(?:textit|emph|textsc|texttt)\{([^{}]*)\}", r"\1", t)
    t = re.sub(r"\\[a-zA-Z]+\s?", "", t)                 # any remaining command
    t = t.replace("---", "\u2014").replace("--", "\u2013")
    t = t.replace("\\%", "%").replace("\\&", "&").replace("\\_", "_")
    t = t.replace("~", " ").replace("$", "")
    return re.sub(r"\s+", " ", t).strip()


def extract(path):
    src = path.read_text(encoding="utf-8")
    out = []
    for m in MACRO.finditer(src):
        kind = "Open" if m.group(1) == "openresearchquestion" else "Focal"
        i = m.end() - 1        # the regex consumed the opening brace
        num, i = read_braced(src, i)
        i = src.index("{", i)
        label, i = read_braced(src, i)
        i = src.index("{", i)
        text, _ = read_braced(src, i)
        # nearest preceding (sub)section title
        section = ""
        for sm in TITLE_OF.finditer(src[:m.start()]):
            section = clean(sm.group(1))
        out.append({
            "n": int(num),
            "type": kind,
            "label": clean(label),
            "text": clean(text),
            "section": section,
        })
    return out


def main():
    groups = []
    for fname, key, chapter, title, label, blurb in CHAPTER_META:
        qs = extract(CHAPTERS / fname)
        nums = [q["n"] for q in qs]
        groups.append({
            "key": key,
            "chapter": chapter,
            "file": fname,
            "title": title,
            "label": label,
            "blurb": blurb,
            "range": f"Q{nums[0]}\u2013Q{nums[-1]}" if nums else "",
            "count": len(qs),
            "questions": qs,
        })
        print(f"  {fname:22s} {len(qs):3d} questions  {groups[-1]['range']}")

    all_q = [q for g in groups for q in g["questions"]]
    data = {
        "source": "papers/RAG_Survey/chapters (merged manuscript)",
        "total": len(all_q),
        "range": f"Q{min(q['n'] for q in all_q)}\u2013Q{max(q['n'] for q in all_q)}",
        "focal": sum(1 for q in all_q if q["type"] == "Focal"),
        "open": sum(1 for q in all_q if q["type"] == "Open"),
        "groups": groups,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ({data['total']} questions, {data['range']})")


if __name__ == "__main__":
    main()
