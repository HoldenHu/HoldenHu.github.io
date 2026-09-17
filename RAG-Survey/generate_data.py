"""
Generate JSON data files for the Agentic RAG Survey companion website.
Parses PAPERS.md, SURVEY.md, and notes/*.md into structured JSON.

Usage: python generate_data.py
Output: data/papers.json, data/taxonomy.json, data/stats.json
"""
import json
import re
import os
from pathlib import Path
from collections import Counter, defaultdict

SITE_DIR = Path(__file__).parent
SURVEY_DIR = SITE_DIR.parent
PDF_DIR = SURVEY_DIR / "pdfs"
NOTES_DIR = SURVEY_DIR / "notes"
DATA_DIR = SITE_DIR / "data"

# ---- Cluster definitions ----
CLUSTERS = {
    "A": "Agentic RAG Surveys",
    "B": "General RAG Surveys",
    "C": "Core Agentic RAG Methods (RL-Trained)",
    "D": "Process-Supervised RL Training",
    "E": "Multi-Hop & Iterative RAG",
    "F": "GraphRAG + Agentic",
    "G": "Tool-Use RAG & Function Calling",
    "H": "Agentic RAG Architectures & Planning",
    "I": "Streaming & Continual RAG",
    "J": "RAG Safety, Privacy & Security",
    "K": "RAG Evaluation & Benchmarks",
    "L": "Multimodal RAG Surveys",
    "M": "Code RAG",
    "N": "Domain-Specific Agentic RAG",
    "O": "RAG vs Long-Context & Efficient Retrieval",
    "P": "Query Rewriting & Optimization",
    "Q": "Multi-Agent & Evaluation",
    "R": "Additional RL Training Papers",
    "S": "Domain-Specific Agentic RAG II",
    "T": "Multi-Agent & Efficient RAG",
    "U": "Advanced RL Training",
    "V": "Efficient & Latent Agentic RAG",
    "W": "Multi-Hop, Multi-Agent & KG-RAG",
    "X": "Evaluation, Security & Benchmarks",
    "Y": "Foundational RAG Papers",
}

# Mapping from verbose venue strings to short codes
VENUE_SHORT = {
    "COLM 2025": "COLM",
    "EMNLP 2025": "EMNLP",
    "EMNLP 2025 Industry": "EMNLP",
    "EMNLP 2025 Findings": "EMNLP",
    "NeurIPS 2025": "NeurIPS",
    "NeurIPS 2025 Competition": "NeurIPS",
    "NeurIPS 2020": "NeurIPS",
    "NeurIPS 2021": "NeurIPS",
    "ACL 2025": "ACL",
    "ACL 2025 Findings": "ACL",
    "ACL 2026": "ACL",
    "ACL 2026 Findings": "ACL",
    "ACL ARR 2026": "ACL",
    "ICLR 2024": "ICLR",
    "ICLR 2026": "ICLR",
    "ICML 2020": "ICML",
    "KDD 2026": "KDD",
    "SIGIR 2026": "SIGIR",
    "SIGIR-AP 2025": "SIGIR",
    "FSE 2026": "FSE",
    "NAACL 2024": "NAACL",
}

# Papers known to have no PDF
MISSING_PDF_REASONS = {
    "datacentric2025agentic": "TechRxiv only; no arxiv version available",
    "vectors2025rag": "Elsevier paywalled; no arxiv preprint",
    "qprm2025": "EMNLP 2025 Findings; no arxiv version found",
}

# ---- Verified Venue Overrides (checked from PDFs, DBLP, and web search) ----
# These override whatever venue is in PAPERS.md
VERIFIED_VENUES = {
    # === Surveys ===
    "singh2025agentic": ("arXiv preprint", "arXiv"),
    "sok2026agentic": ("arXiv preprint", "arXiv"),
    "li2025ragreasoning": ("arXiv preprint", "arXiv"),
    "sys12_2025": ("arXiv preprint", "arXiv"),
    "mma2025rag": ("HAL preprint", "HAL"),
    "datacentric2025agentic": ("TechRxiv preprint", "TechRxiv"),
    "sharma2025rag": ("TOIS (under review)", "TOIS"),
    "wu2024rag": ("arXiv preprint", "arXiv"),
    "gupta2024rag": ("arXiv preprint", "arXiv"),
    "knowledge2025rag": ("arXiv preprint", "arXiv"),
    "eval2025rag": ("arXiv preprint", "arXiv"),
    "vectors2025rag": ("Elsevier", "Elsevier"),

    # === Core Methods (verified from DBLP/conference proceedings) ===
    "jin2025searchr1": ("COLM 2025", "COLM"),
    "li2025searcho1": ("EMNLP 2025", "EMNLP"),
    "wu2025searchwisely": ("EMNLP 2025", "EMNLP"),
    "research2025": ("NeurIPS 2025", "NeurIPS"),
    "zhao2025expandsearch": ("arXiv preprint", "arXiv"),
    "smartrag2024": ("arXiv preprint", "arXiv"),

    # === Process-Supervised RL ===
    "leng2025decex": ("arXiv preprint", "arXiv"),
    "rexrag2025": ("arXiv preprint", "arXiv"),
    "cwgrpo2026": ("ACL 2026", "ACL"),
    "arbor2026": ("arXiv preprint", "arXiv"),
    "prorag2026": ("arXiv preprint", "arXiv"),
    "treeps2026": ("WWW 2026", "WWW"),
    "reasonrag2025": ("NeurIPS 2025", "NeurIPS"),
    "hashemi2025costaware": ("arXiv preprint", "arXiv"),
    "porag2025": ("arXiv preprint", "arXiv"),
    "moler2025": ("arXiv preprint", "arXiv"),
    "rlqr2025": ("arXiv preprint", "arXiv"),

    # === Multi-Hop ===
    "globalrag2025": ("arXiv preprint", "arXiv"),
    "kirag2025": ("arXiv preprint", "arXiv"),
    "dualrag2025": ("ACL 2025", "ACL"),
    "opera2025": ("arXiv preprint", "arXiv"),
    "rtrag2026": ("arXiv preprint", "arXiv"),
    "compactrag2026": ("arXiv preprint", "arXiv"),
    "grip2026": ("ACL 2026", "ACL"),
    "stride2026": ("SIGIR 2026", "SIGIR"),
    "raser2026": ("arXiv preprint", "arXiv"),
    "eka2025": ("arXiv preprint", "arXiv"),

    # === GraphRAG ===
    "graphr1_2025": ("arXiv preprint", "arXiv"),
    "prographr1_2026": ("arXiv preprint", "arXiv"),
    "graphragr1_2025": ("arXiv preprint", "arXiv"),
    "memgraphrag2026": ("KDD 2026", "KDD"),
    "techgraphrag2026": ("arXiv preprint", "arXiv"),
    "graphsearch2025": ("arXiv preprint", "arXiv"),
    "neighborhoods2026": ("arXiv preprint", "arXiv"),
    "benchgraphrag2026": ("arXiv preprint", "arXiv"),

    # === Tool-Use ===
    "when2tool2026": ("arXiv preprint", "arXiv"),
    "artist2025": ("arXiv preprint", "arXiv"),
    "seer2025": ("arXiv preprint", "arXiv"),
    "jtpro2026": ("ACL 2026", "ACL"),
    "unitoolcall2026": ("arXiv preprint", "arXiv"),
    "onlineopt2025": ("arXiv preprint", "arXiv"),

    # === Architectures ===
    "researcher2025": ("arXiv preprint", "arXiv"),
    "apex2026": ("arXiv preprint", "arXiv"),
    "cogplanner2025": ("SIGIR-AP 2025", "SIGIR"),
    "evipath2025": ("arXiv preprint", "arXiv"),
    "dynatree2026": ("arXiv preprint", "arXiv"),
    "autothinkrag2026": ("arXiv preprint", "arXiv"),
    "llmwiki2026": ("arXiv preprint", "arXiv"),
    "rethink2026": ("arXiv preprint", "arXiv"),
    "sira2026": ("arXiv preprint", "arXiv"),

    # === Streaming ===
    "cream2026": ("arXiv preprint", "arXiv"),
    "livevectorlake2025": ("arXiv preprint", "arXiv"),
    "streamingrag2025": ("arXiv preprint", "arXiv"),
    "luma2025": ("arXiv preprint", "arXiv"),
    "oaks2026": ("arXiv preprint", "arXiv"),
    "contprompts2025": ("arXiv preprint", "arXiv"),

    # === Security ===
    "secure2026rag": ("arXiv preprint", "arXiv"),
    "securing2026rag": ("arXiv preprint", "arXiv"),
    "sokprivacy2026": ("arXiv preprint", "arXiv"),
    "pad2026": ("KDD 2026", "KDD"),
    "dpksa2026": ("arXiv preprint", "arXiv"),

    # === Evaluation ===
    "rt4chart2026": ("arXiv preprint", "arXiv"),
    "faithjudge2025": ("EMNLP 2025 Industry", "EMNLP"),
    "franq2025": ("arXiv preprint", "arXiv"),
    "trivia2026": ("ACL 2026", "ACL"),
    "semanticillusion2025": ("arXiv preprint", "arXiv"),

    # === Multimodal ===
    "mrrag2025": ("ACL 2025 Findings", "ACL"),

    # === Code RAG ===
    "coderagsurvey2025": ("arXiv preprint", "arXiv"),
    "hydra2026": ("FSE 2026", "FSE"),

    # === Domain-Specific ===
    "semarag2026": ("ACL 2026 Findings", "ACL"),
    "policygoverned2025": ("arXiv preprint", "arXiv"),
    "citationclosure2026": ("arXiv preprint", "arXiv"),

    # === Long-Context ===
    "shim2026ldar": ("ICLR 2026", "ICLR"),
    "hu2026sage": ("ACL ARR 2026", "ACL"),
    "attentionretriever2026": ("arXiv preprint", "arXiv"),
    "llmspecific2025": ("arXiv preprint", "arXiv"),

    # === Query Rewriting ===
    "acqo2026": ("WWW 2026", "WWW"),
    "qprm2025": ("EMNLP 2025 Findings", "EMNLP"),
    "flashrank2025": ("arXiv preprint", "arXiv"),
    "embsim2024": ("arXiv preprint", "arXiv"),

    # === Multi-Agent ===
    "massrag2026": ("ACL 2026 Findings", "ACL"),
    "spdrag2026": ("arXiv preprint", "arXiv"),
    "riker2026": ("arXiv preprint", "arXiv"),

    # === Additional RL ===
    "hiprag2025": ("arXiv preprint", "arXiv"),
    "ragreward2025": ("arXiv preprint", "arXiv"),
    "othink2026": ("arXiv preprint", "arXiv"),
    "r32025": ("arXiv preprint", "arXiv"),
    "rewardrag2024": ("arXiv preprint", "arXiv"),
    "treegrpo2025": ("ICLR 2026", "ICLR"),
    "strongermas2025": ("arXiv preprint", "arXiv"),

    # === Domain-Specific II ===
    "deepdxsearch2025": ("arXiv preprint", "arXiv"),
    "fintechrag2025": ("arXiv preprint", "arXiv"),

    # === Multi-Agent & Efficient ===
    "r2rag2026": ("NeurIPS 2025 Competition", "NeurIPS"),
    "carrot2024": ("arXiv preprint", "arXiv"),
    "fairrag2025": ("arXiv preprint", "arXiv"),
    "corpus2skill2026": ("arXiv preprint", "arXiv"),
    "certa2026": ("arXiv preprint", "arXiv"),

    # === Advanced RL ===
    "lets2025": ("arXiv preprint", "arXiv"),
    "r3rag2025": ("arXiv preprint", "arXiv"),
    "ctrlrag2026": ("arXiv preprint", "arXiv"),
    "stratifiedgrpo2025": ("arXiv preprint", "arXiv"),
    "parag2024": ("arXiv preprint", "arXiv"),
    "criticr2026": ("arXiv preprint", "arXiv"),

    # === Efficient & Latent ===
    "latentrag2026": ("arXiv preprint", "arXiv"),
    "graphragrouter2026": ("arXiv preprint", "arXiv"),
    "sras2026": ("arXiv preprint", "arXiv"),
    "rasd2025": ("arXiv preprint", "arXiv"),

    # === Multi-Hop & KG ===
    "mmsearchr12025": ("arXiv preprint", "arXiv"),
    "marag2025": ("arXiv preprint", "arXiv"),
    "bridgerag2026": ("arXiv preprint", "arXiv"),
    "adagate2026": ("arXiv preprint", "arXiv"),
    "hoprag2025": ("arXiv preprint", "arXiv"),
    "spathrag2026": ("arXiv preprint", "arXiv"),
    "collabrag2025": ("arXiv preprint", "arXiv"),
    "vendirag2025": ("arXiv preprint", "arXiv"),

    # === Eval & Security ===
    "ragrewardbench2024": ("arXiv preprint", "arXiv"),
    "derag2025": ("arXiv preprint", "arXiv"),

    # === Foundational ===
    "lewis2020rag": ("NeurIPS 2020", "NeurIPS"),
    "asai2023selfrag": ("ICLR 2024", "ICLR"),
    "jeong2023adaptiverag": ("NAACL 2024", "NAACL"),
    "trivedi2022ircot": ("ACL 2023", "ACL"),
    "shao2023iterretgen": ("EMNLP 2023 Findings", "EMNLP"),
    "jiang2023flare": ("EMNLP 2023", "EMNLP"),
    "li2024dragin": ("ACL 2024", "ACL"),
    "sarthi2024raptor": ("ICLR 2024", "ICLR"),
    "edge2024graphrag": ("arXiv preprint", "arXiv"),
    "guo2024lightrag": ("arXiv preprint", "arXiv"),
    "guu2020realm": ("ICML 2020", "ICML"),
    "qian2024memorag": ("arXiv preprint", "arXiv"),
    "yan2024crag": ("arXiv preprint", "arXiv"),
    "nakano2021webgpt": ("NeurIPS 2021", "NeurIPS"),
    "zhao2026component": ("FSE 2026", "FSE"),
}


def normalize(s):
    """Normalize string for fuzzy matching: lowercase, remove underscores/dashes."""
    return re.sub(r'[_-]', '', s.lower())


def parse_papers_md():
    """Parse PAPERS.md into structured paper entries by cluster."""
    papers_path = SURVEY_DIR / "PAPERS.md"
    with open(papers_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_cluster = None
    papers = []
    paper_id = 0

    for line in lines:
        stripped = line.strip()

        # Detect cluster headers
        cluster_match = re.match(r'^## Cluster ([A-Z]):', stripped)
        if cluster_match:
            current_cluster = cluster_match.group(1)
            continue

        # Skip non-table lines
        if not stripped.startswith("|") or stripped.startswith("|---"):
            continue
        if "BibKey" in stripped or "# | Title" in stripped:
            continue

        # Parse table row
        parts = [p.strip() for p in stripped.split("|")]
        if len(parts) < 8:
            continue

        # #, Title, Authors, Year, Venue, arXiv, BibKey, PDF
        idx = parts[1].strip()
        title = parts[2].strip()
        authors = parts[3].strip()
        year = parts[4].strip()
        venue = parts[5].strip()
        arxiv_cell = parts[6].strip()
        bibkey = parts[7].strip().strip("`")
        pdf_status = parts[8].strip() if len(parts) > 8 else ""

        # Skip header rows or non-numeric entries
        if not idx or idx in ("#", "---"):
            continue

        # Extract arXiv ID from markdown link
        arxiv_id = ""
        arxiv_url = ""
        arxiv_md = re.search(r'\[([^\]]+)\]\(([^)]+)\)', arxiv_cell)
        if arxiv_md:
            arxiv_id = arxiv_md.group(1)
            arxiv_url = arxiv_md.group(2)
        elif arxiv_cell and arxiv_cell != "—":
            arxiv_id = arxiv_cell

        # Clean year: handle ranges like "2025→2026", "2024→2026"
        year_clean = year
        if "→" in year:
            year_clean = year.split("→")[-1].strip()
        elif "-" in year and len(year) > 5:
            year_clean = year.split("-")[-1].strip()

        # Clean venue
        venue_short = VENUE_SHORT.get(venue, venue)
        # Handle "arXiv (v4 Apr 2026)" → "arXiv"
        if venue.startswith("arXiv"):
            venue_short = "arXiv"
        elif venue.startswith("HAL"):
            venue_short = "HAL"
        elif venue.startswith("TechRxiv"):
            venue_short = "TechRxiv"
        elif venue.startswith("Elsevier"):
            venue_short = "Elsevier"

        # Determine PDF status
        has_pdf = "✅" in pdf_status
        pdf_missing_reason = ""
        if not has_pdf:
            pdf_missing_reason = MISSING_PDF_REASONS.get(bibkey, "")

        # Apply verified venue override if available
        if bibkey in VERIFIED_VENUES:
            venue, venue_short = VERIFIED_VENUES[bibkey]

        paper_id += 1
        papers.append({
            "id": paper_id,
            "idx": idx,
            "title": title,
            "authors": authors if authors and authors != "—" else "",
            "year": year_clean,
            "year_display": year,
            "venue": venue,
            "venue_short": venue_short,
            "arxiv_id": arxiv_id,
            "arxiv_url": arxiv_url,
            "bibkey": bibkey,
            "has_pdf": has_pdf,
            "pdf_missing_reason": pdf_missing_reason,
            "cluster_id": current_cluster or "?",
            "cluster_name": CLUSTERS.get(current_cluster, "Unknown"),
        })

    return papers


def find_pdf_path(bibkey, arxiv_id):
    """Find the PDF filename for a paper. Returns relative path or None."""
    # Try bibkey.pdf
    pdf_path = PDF_DIR / f"{bibkey}.pdf"
    if pdf_path.exists():
        return f"../pdfs/{bibkey}.pdf"

    # Try arxiv_id.pdf
    if arxiv_id:
        pdf_path = PDF_DIR / f"{arxiv_id}.pdf"
        if pdf_path.exists():
            return f"../pdfs/{arxiv_id}.pdf"

    # Try fuzzy match: list all PDFs and find closest match
    bibkey_norm = normalize(bibkey)
    if PDF_DIR.exists():
        for f in sorted(PDF_DIR.iterdir()):
            if f.suffix == ".pdf":
                f_norm = normalize(f.stem)
                # Check if bibkey is contained in filename or vice versa
                if bibkey_norm in f_norm or f_norm in bibkey_norm:
                    return f"../pdfs/{f.name}"
                # Try arxiv ID match
                if arxiv_id and arxiv_id in f.stem:
                    return f"../pdfs/{f.name}"

    return None


def parse_notes():
    """Parse notes/*.md to extract abstracts and key contributions."""
    notes_data = {}
    if not NOTES_DIR.exists():
        return notes_data

    for note_file in sorted(NOTES_DIR.iterdir()):
        if not note_file.suffix == ".md":
            continue
        if note_file.name == "uncited_papers_review.md":
            continue

        try:
            with open(note_file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        # Extract abstract
        abstract = ""
        abs_match = re.search(r'## Abstract\s*\n(.*?)(?=\n##|\n#|\Z)', content, re.DOTALL)
        if abs_match:
            abstract = abs_match.group(1).strip()

        # Extract key contributions
        contributions = []
        contrib_match = re.search(r'## Key Contributions\s*\n(.*?)(?=\n##|\n#|\Z)', content, re.DOTALL)
        if contrib_match:
            contrib_text = contrib_match.group(1).strip()
            for line in contrib_text.split("\n"):
                line = line.strip()
                if line.startswith(("1.", "2.", "3.", "4.", "5.", "-")):
                    contrib = re.sub(r'^\d+\.\s*\**', '', line).strip()
                    contrib = contrib.strip("_").strip("*").strip()
                    if contrib and len(contrib) > 5:
                        contributions.append(contrib)

        # Map note filename to bibkey
        note_name = note_file.stem  # e.g., "jin2025_search_r1"
        notes_data[normalize(note_name)] = {
            "abstract": abstract,
            "contributions": contributions,
            "note_file": f"../notes/{note_file.name}",
        }

    return notes_data


def match_notes_to_papers(papers, notes_data):
    """Match note files to papers by normalizing bibkeys."""
    for paper in papers:
        bk_norm = normalize(paper["bibkey"])
        # Direct match
        if bk_norm in notes_data:
            note = notes_data[bk_norm]
            paper["abstract"] = note["abstract"]
            paper["contributions"] = note["contributions"]
            paper["has_note"] = True
            paper["note_file"] = note["note_file"]
        else:
            # Try fuzzy matching
            matched = False
            for note_key, note_val in notes_data.items():
                if bk_norm in note_key or note_key in bk_norm:
                    paper["abstract"] = note_val["abstract"]
                    paper["contributions"] = note_val["contributions"]
                    paper["has_note"] = True
                    paper["note_file"] = note_val["note_file"]
                    matched = True
                    break
            if not matched:
                paper["abstract"] = ""
                paper["contributions"] = []
                paper["has_note"] = False
                paper["note_file"] = ""
    return papers


def parse_taxonomy():
    """Extract taxonomy structure from SURVEY.md."""
    survey_path = SURVEY_DIR / "SURVEY.md"
    with open(survey_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Dimension I: Decision Autonomy
    dim1 = {
        "id": "decision_autonomy",
        "name": "Decision Autonomy",
        "description": "Control Flow Spectrum",
        "levels": [
            {"level": 0, "name": "Static", "desc": "Fixed retrieve-then-generate, no decisions"},
            {"level": 1, "name": "Adaptive Routing", "desc": "Binary or multi-way routing decision (gate/switch)"},
            {"level": 2, "name": "Iterative Looping", "desc": "Multiple rounds, each informs the next (search-read-think)"},
            {"level": 3, "name": "Autonomous Planning", "desc": "Plan → Execute → Reflect → Replan"},
            {"level": 4, "name": "Self-Evolving", "desc": "Persistent improvement across sessions"},
        ],
        "w_questions": "W1 (when to retrieve), W5 (which retriever)",
        "example_papers": {
            0: ["lewis2020rag"],
            1: ["jeong2023adaptiverag", "asai2023selfrag", "when2tool2026"],
            2: ["trivedi2022ircot", "shao2023iterretgen", "jiang2023flare", "li2024dragin", "kirag2025"],
            3: ["jin2025searchr1", "leng2025decex", "opera2025", "stride2026", "globalrag2025"],
            4: ["llmwiki2026", "seer2025", "semarag2026"],
        },
    }

    # Dimension II: Knowledge Organization
    dim2 = {
        "id": "knowledge_organization",
        "name": "Knowledge Organization",
        "description": "Structure Spectrum",
        "levels": [
            {"level": 0, "name": "Flat Text Chunks", "desc": "Standard chunk-and-embed RAG"},
            {"level": 1, "name": "Hierarchical Indexing", "desc": "Tree structures, recursive summarization"},
            {"level": 2, "name": "Graph-Structured", "desc": "Entity-relationship graphs, KG traversal"},
            {"level": 3, "name": "Parametric/Compressed Memory", "desc": "Knowledge encoded in model parameters"},
            {"level": 4, "name": "Agent-Native Knowledge", "desc": "Structured for agent navigation"},
        ],
        "w_questions": "W3 (query form), W4 (knowledge structure)",
        "example_papers": {
            0: [],
            1: ["sarthi2024raptor", "autothinkrag2026"],
            2: ["edge2024graphrag", "guo2024lightrag", "graphr1_2025", "memgraphrag2026"],
            3: ["guu2020realm", "qian2024memorag", "cream2026", "luma2025"],
            4: ["llmwiki2026", "corpus2skill2026", "sira2026"],
        },
    }

    # Dimension III: Quality Control
    dim3 = {
        "id": "quality_control",
        "name": "Quality Control",
        "description": "Reflection Spectrum",
        "levels": [
            {"level": 0, "name": "No Verification", "desc": "Trust retrieval results blindly"},
            {"level": 1, "name": "Post-hoc Scoring", "desc": "Evaluate output after generation"},
            {"level": 2, "name": "Intrinsic Self-Critique", "desc": "Model evaluates own output during inference"},
            {"level": 3, "name": "External Verification", "desc": "Separate verifier module or external source"},
            {"level": 4, "name": "Adversarial/Process-Level", "desc": "Multi-step verification with formal guarantees"},
        ],
        "w_questions": "W6 (quality evaluation)",
        "example_papers": {
            0: [],
            1: ["faithjudge2025", "franq2025"],
            2: ["asai2023selfrag", "researcher2025"],
            3: ["yan2024crag", "rt4chart2026", "nakano2021webgpt"],
            4: ["arbor2026", "treeps2026", "policygoverned2025"],
        },
    }

    # Training taxonomy tree
    training_tree = {
        "name": "Agentic RAG Training",
        "children": [
            {
                "name": "Outcome-Based RL",
                "color": "#3182ce",
                "children": [
                    {
                        "name": "PPO variants",
                        "papers": ["li2025searcho1", "research2025"],
                    },
                    {
                        "name": "GRPO variants",
                        "papers": ["jin2025searchr1", "wu2025searchwisely", "smartrag2024"],
                    },
                    {
                        "name": "Cost-aware",
                        "papers": ["hashemi2025costaware", "porag2025"],
                    },
                ],
            },
            {
                "name": "Process-Supervised RL",
                "color": "#38a169",
                "highlighted": True,
                "badge": "KEY DIFFERENTIATOR",
                "children": [
                    {"name": "MDP Formalization", "papers": ["leng2025decex"]},
                    {"name": "MCTS-based PRM", "papers": ["prorag2026", "reasonrag2025"]},
                    {"name": "Tree-based Credit Assignment", "papers": ["treeps2026"]},
                    {"name": "Contribution-Weighted", "papers": ["cwgrpo2026"]},
                    {"name": "Rubric Buffer", "papers": ["arbor2026"]},
                    {"name": "Process-Constrained", "papers": ["graphragr1_2025"]},
                ],
            },
            {
                "name": "Multi-Agent RL (MARL)",
                "color": "#805ad5",
                "children": [
                    {"name": "MAPGRPO", "papers": ["opera2025"]},
                    {"name": "Hierarchical", "papers": ["memgraphrag2026"]},
                ],
            },
        ],
    }

    return {
        "dimensions": [dim1, dim2, dim3],
        "training_tree": training_tree,
        "w_questions": [
            {"id": "W1", "question": "When to retrieve?"},
            {"id": "W2", "question": "Where to retrieve from?"},
            {"id": "W3", "question": "What form should the query take?"},
            {"id": "W4", "question": "How to organize retrieved knowledge?"},
            {"id": "W5", "question": "Which retriever to use?"},
            {"id": "W6", "question": "How to evaluate quality?"},
        ],
    }


def compute_stats(papers):
    """Compute aggregate statistics from papers."""
    # Year distribution
    year_counts = Counter()
    for p in papers:
        y = p["year"]
        try:
            year_counts[int(y)] += 1
        except ValueError:
            year_counts[y] += 1

    # Venue distribution
    venue_counts = Counter()
    for p in papers:
        venue_counts[p["venue_short"]] += 1

    # Cluster distribution
    cluster_counts = Counter()
    for p in papers:
        cluster_counts[p["cluster_id"]] += 1

    # PDF stats
    pdf_ok = sum(1 for p in papers if p["has_pdf"])
    pdf_missing = sum(1 for p in papers if not p["has_pdf"])
    has_note = sum(1 for p in papers if p["has_note"])
    no_note = sum(1 for p in papers if not p["has_note"])

    # Year range
    years_int = [int(p["year"]) for p in papers if p["year"].isdigit()]
    year_range = f"{min(years_int)}–{max(years_int)}" if years_int else "N/A"

    return {
        "total_papers": len(papers),
        "total_clusters": len(set(p["cluster_id"] for p in papers)),
        "year_range": year_range,
        "papers_by_year": dict(sorted(year_counts.items())),
        "papers_by_venue": dict(venue_counts.most_common(15)),
        "papers_by_cluster": {k: cluster_counts.get(k, 0) for k in CLUSTERS},
        "pdf_available": pdf_ok,
        "pdf_missing": pdf_missing,
        "pdf_rate": round(pdf_ok / len(papers) * 100, 1) if papers else 0,
        "papers_with_notes": has_note,
        "papers_without_notes": no_note,
        "papers_2026": sum(1 for p in papers if p["year"] == "2026"),
        "papers_2025": sum(1 for p in papers if p["year"] == "2025"),
        "missing_pdfs": [
            {"bibkey": p["bibkey"], "title": p["title"], "reason": p["pdf_missing_reason"]}
            for p in papers if not p["has_pdf"]
        ],
        "differentiators": [
            {"dimension": "Analysis Level", "singh": "Agent architecture", "ours": "Component-level (6 components)"},
            {"dimension": "Taxonomy Type", "singh": "Architectural", "ours": "Capability-spectrum (3D morphology)"},
            {"dimension": "Evolution Story", "singh": "Two stages: RAG → Agentic RAG", "ours": "Continuous agentification of each component"},
            {"dimension": "Engineering Value", "singh": "None", "ours": "Decision Matrix for builders"},
            {"dimension": "Time Coverage", "singh": "Through early 2025", "ours": "Through mid-2026 (60+ 2026 papers)"},
            {"dimension": "RL Training", "singh": "Not covered", "ours": "Process-Supervised RL taxonomy (GRPO, MCTS, credit assignment)"},
            {"dimension": "Streaming", "singh": "Not covered", "ours": "Streaming/Continual RAG chapter"},
        ],
        "white_spaces": [
            {
                "title": "Process-Supervised RL for Agentic RAG",
                "desc": "GRPO variants, MCTS-based PRMs, credit assignment — the core unsolved problem in Agentic RAG training.",
            },
            {
                "title": "Streaming/Continual Agentic RAG",
                "desc": "Dynamic knowledge, temporal retrieval, incremental updates — how RAG stays current in production.",
            },
            {
                "title": "Component-to-Agent Evolution Bridge",
                "desc": "How each static RAG component (retriever, reader, memory) acquires agentic capabilities autonomously.",
            },
        ],
    }


# ---- Full-library clusters (for papers_full.json, all notes/*.md) ----
FULL_CLUSTERS = {
    "A": "Surveys & Position Papers",
    "B": "Foundational RAG",
    "C": "Agentic & Iterative RAG",
    "D": "RL Training for RAG",
    "E": "Retrieval, Reranking & Embeddings",
    "F": "Graph & Structured RAG",
    "G": "Query Processing",
    "H": "Context, Compression & Efficiency",
    "I": "Multimodal RAG",
    "J": "Security, Privacy & Robustness",
    "K": "Evaluation, Benchmarks & Hallucination Detection",
    "L": "Domain-Specific RAG",
    "M": "Memory, Continual & Dynamic Corpora",
    "N": "Generation, Knowledge Conflicts & Alignment",
    "O": "RAG Beyond QA (Generation & Embodied)",
}

# Keyword rules: (priority order matters — first match wins; specific before generic)
FULL_CLUSTER_RULES = [
    ("A", ["survey", "mapping study", "systematic review", "position paper", "scaling laws"]),
    ("J", ["poison", "attack", "defense", "defence", "watermark", "copyright", "privacy", "leakage", "extraction",
           "adversarial", "security", "jailbreak", "certified", "conformal", "robustness", "safe", "fairness",
           "misinformation", "nepotism", "stealth", "traceback", "bias"]),
    ("K", ["benchmark", "evaluation", "evaluating", "hallucination detection", "detecting hallucin",
           "attribution", "uncertainty", "judge", "metric divergence", "evaluator", "quality estimation", "factuality",
           "probing", "desiderata"]),
    ("L", ["medical", "clinical", "health", "biomedical", "bioasq", "legal", "litigation", "law ", "finance", "financial",
           "code summarization", "code repair", "programming", "software", "agricultur", "chemistry", "scientific",
           "recipe", "culinary", "education", "ehr", "radiology", "medicine", "reaction prediction", "fashion",
           "e-commerce", "enterprise", "erp", "book search", "food delivery", "talmud"]),
    ("I", ["multimodal", "vision-language", "vision language", "visual", "vqa", "ocr", "chart", "layout", "gesture",
           "audio", "speech", "eeg", "rgbt", "text-to-image", "text-to-video", "captioning", "super-resolution",
           "visually rich", "video"]),
    ("O", ["molecule", "trajectory", "tracking", "deraining", "garment", "scenario", "human-scene", "brain decoding",
           "prompt optimization", "traffic"]),
    ("F", ["graph", "knowledge graph", "hypergraph", "tree", "kg-rag", "graphrag", "raptor", "structured",
           "entity", "proposition", "logic"]),
    ("H", ["compression", "compress", "kv cache", "context window", "long context", "long-context", "pruning",
           "efficient", "efficiency", "latency", "prefetch", "serving", "cache", "prefill", "speculative", "cost"]),
    ("M", ["memory", "continual", "dynamic corpora", "dynamic corpus", "streaming", "evolving", "incremental", "forgetting",
           "rehearsal", "lifelong"]),
    ("D", ["reinforcement learning", "grpo", "process reward", "process supervision", "policy optimization", "reward model",
           "search-r1", "rl training", "bootstrapping", "search-o1"]),
    ("G", ["query rewriting", "query reformulation", "query expansion", "query understanding", "query augmentation",
           "decomposition", "reformulat", "query production"]),
    ("E", ["generative retrieval", "dense retrieval", "sparse retrieval", "rerank", "re-rank", "docid", "embedding",
           "search index", "query likelihood", "hash code", "index", "retriever", "search engine", "cross-encoder"]),
    ("C", ["agent", "multi-hop", "multihop", "iterative", "reasoning", "planning", "self-rag", "search",
           "tool", "interact", "evidence tree", "consensus"]),
    ("N", ["hallucinat", "conflict", "grounding", "faithful", "internal knowledge", "parametric knowledge",
           "contextual interference", "evidence", "distraction", "consolidat"]),
    ("B", ["retrieval-augmented", "retrieval augmented", "knowledge-intensive", "in-context ralm", "realm",
           "fusion-in-decoder", "rag "]),
]


def _parse_note_header(content):
    """Parse a note's header lines (Authors/Year/Venue/arxiv/DOI/Zotero)."""
    meta = {"authors": "", "year": "", "venue": "", "arxiv_id": "", "doi": ""}
    for line in content.split("\n")[:15]:
        line = line.strip()
        m = re.match(r'-\s*\*\*(Authors|Year|Venue|arxiv|DOI)\*\*:\s*(.*)', line)
        if m:
            key, val = m.group(1).lower(), m.group(2).strip()
            if key == "authors":
                meta["authors"] = val
            elif key == "year":
                ym = re.match(r'(\d{4})', val)
                meta["year"] = ym.group(1) if ym else ""
            elif key == "venue":
                # Strip trailing "(arXiv:xxxx)" / "(DOI: ...)"
                meta["venue"] = re.sub(r'\s*\((arXiv|DOI)[^)]*\)\s*$', '', val).strip()
            elif key == "arxiv":
                am = re.search(r'\[([^\]]+)\]\(([^)]+)\)', val)
                if am:
                    meta["arxiv_id"] = am.group(1)
                    if not meta["arxiv_id"]:
                        meta["arxiv_id"] = am.group(2).rstrip('/').split('/')[-1]
                else:
                    meta["arxiv_id"] = val
            elif key == "doi":
                meta["doi"] = val
    return meta


def _venue_short(venue, arxiv_id):
    """Map a verbose venue string to a short code."""
    v = venue.lower()
    short = "Other"
    table = [
        ("annual meeting of the association for computational linguistics", "ACL"),
        ("conference on empirical methods", "EMNLP"),
        ("north american chapter", "NAACL"),
        ("european chapter", "EACL"),
        ("international conference on learning representations", "ICLR"),
        ("international conference on machine learning", "ICML"),
        ("neural information processing systems", "NeurIPS"),
        ("sigir", "SIGIR"),
        ("knowledge discovery and data mining", "KDD"),
        ("web conference", "WWW"),
        ("international conference on information and knowledge management", "CIKM"),
        ("aaai conference", "AAAI"),
        ("computer vision and pattern recognition", "CVPR"),
        ("international conference on computer vision", "ICCV"),
        ("european conference on computer vision", "ECCV"),
        ("acm multimedia", "ACM MM"),
        ("european conference on information retrieval", "ECIR"),
        ("international conference on computational linguistics", "COLING"),
        ("transactions of the association for computational linguistics", "TACL"),
        ("transactions on information systems", "TOIS"),
        ("acm trans", "TOIS"),
        ("nature communications", "Nat Comm"),
        ("nature", "Nature"),
        ("international conference on the theory of information retrieval", "ICTIR"),
        ("international conference on data engineering", "ICDE"),
        # abbreviation fallbacks (check first)
        ("icml", "ICML"),
        ("iclr", "ICLR"),
        ("iccv", "ICCV"),
        ("cvpr", "CVPR"),
        ("eccv", "ECCV"),
        ("aaai", "AAAI"),
        ("emnlp", "EMNLP"),
        ("naacl", "NAACL"),
        ("eacl", "EACL"),
        ("tacl", "TACL"),
        ("acl", "ACL"),
        ("neurips", "NeurIPS"),
        ("sigir", "SIGIR"),
        ("kdd", "KDD"),
        ("www", "WWW"),
        ("cikm", "CIKM"),
        ("coling", "COLING"),
        ("tois", "TOIS"),
        ("icde", "ICDE"),
        ("ictir", "ICTIR"),
        ("ecir", "ECIR"),
    ]
    for pat, code in table:
        if pat in v:
            return code
    if arxiv_id:
        return "arXiv"
    if "workshop" in v:
        return "Workshop"
    return short


def _assign_full_cluster(title_lower):
    for cid, kws in FULL_CLUSTER_RULES:
        for kw in kws:
            if kw in title_lower:
                return cid
    return "C"  # default: agentic RAG family


def _load_cluster_overrides():
    """Manual review overrides: {note_stem: cluster_id}, reviewed in batches."""
    p = SITE_DIR / "cluster_overrides.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def parse_all_notes():
    """Build the full library entry list from all notes/*.md (1050 papers)."""
    overrides = _load_cluster_overrides()
    full_papers = []
    if not NOTES_DIR.exists():
        return full_papers
    paper_id = 0
    for note_file in sorted(NOTES_DIR.iterdir()):
        if not note_file.suffix == ".md":
            continue
        if note_file.name in ("uncited_papers_review.md",):
            continue
        try:
            content = note_file.read_text(encoding="utf-8")
        except Exception:
            continue

        # Title = first H1 line
        title_m = re.match(r'^#\s+(.*)', content)
        title = title_m.group(1).strip() if title_m else note_file.stem

        meta = _parse_note_header(content)
        abstract = ""
        abs_m = re.search(r'## Abstract\s*\n(.*?)(?=\n##|\n#|\Z)', content, re.DOTALL)
        if abs_m:
            abstract = abs_m.group(1).strip()
        placeholder = "状态说明" in content  # no-PDF metadata-only note

        # PDF path by slug (note stem = slug used in pdfs/)
        pdf_rel = f"../pdfs/{note_file.stem}.pdf"
        has_pdf = (PDF_DIR / f"{note_file.stem}.pdf").exists()

        cid = overrides.get(note_file.stem) or _assign_full_cluster(title.lower())
        paper_id += 1
        full_papers.append({
            "id": paper_id,
            "title": title,
            "authors": meta["authors"],
            "year": meta["year"],
            "year_display": meta["year"],
            "venue": meta["venue"],
            "venue_short": _venue_short(meta["venue"], meta["arxiv_id"]),
            "arxiv_id": meta["arxiv_id"],
            "arxiv_url": f"https://arxiv.org/abs/{meta['arxiv_id']}" if meta["arxiv_id"] else "",
            "doi": meta["doi"],
            "bibkey": note_file.stem,
            "has_pdf": has_pdf,
            "pdf_path": pdf_rel if has_pdf else "",
            "pdf_missing_reason": "" if has_pdf else ("metadata-only note (no PDF in collection)" if placeholder else ""),
            "has_note": True,
            "note_file": f"../notes/{note_file.name}",
            "abstract": abstract,
            "placeholder": placeholder,
            "cluster_id": cid,
            "cluster_name": FULL_CLUSTERS.get(cid, "Unknown"),
        })
    return full_papers


def main():
    print("Generating Agentic RAG Survey website data...")

    # Parse papers
    print("  Parsing PAPERS.md...")
    papers = parse_papers_md()
    print(f"    Found {len(papers)} papers")

    # Parse notes
    print("  Parsing notes/...")
    notes_data = parse_notes()
    print(f"    Found {len(notes_data)} note files")

    # Match notes to papers
    papers = match_notes_to_papers(papers, notes_data)
    matched = sum(1 for p in papers if p["has_note"])
    print(f"    Matched {matched}/{len(papers)} papers to notes")

    # Find PDF paths
    print("  Matching PDFs...")
    pdf_found = 0
    for p in papers:
        pdf_path = find_pdf_path(p["bibkey"], p["arxiv_id"])
        if pdf_path:
            p["pdf_path"] = pdf_path
            if not p["has_pdf"] and MISSING_PDF_REASONS.get(p["bibkey"]):
                # Override: PDF actually found at a different name
                p["has_pdf"] = True
                p["pdf_missing_reason"] = ""
            pdf_found += 1
        else:
            p["pdf_path"] = ""
    print(f"    Found PDFs for {pdf_found}/{len(papers)} papers")

    # Parse taxonomy
    print("  Building taxonomy...")
    taxonomy = parse_taxonomy()

    # Compute stats
    print("  Computing statistics...")
    stats = compute_stats(papers)

    # Write JSON files
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    papers_path = DATA_DIR / "papers.json"
    with open(papers_path, "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)
    print(f"  Wrote {papers_path} ({len(papers)} papers, {papers_path.stat().st_size // 1024} KB)")

    taxonomy_path = DATA_DIR / "taxonomy.json"
    with open(taxonomy_path, "w", encoding="utf-8") as f:
        json.dump(taxonomy, f, ensure_ascii=False, indent=2)
    print(f"  Wrote {taxonomy_path} ({taxonomy_path.stat().st_size // 1024} KB)")

    stats_path = DATA_DIR / "stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"  Wrote {stats_path} ({stats_path.stat().st_size // 1024} KB)")

    # ---- Full library (all notes, for full-list page) ----
    print("  Building full library from notes/...")
    full_papers = parse_all_notes()
    full_path = DATA_DIR / "papers_full.json"
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(full_papers, f, ensure_ascii=False, indent=1)
    n_full = len(full_papers)
    n_pdf = sum(1 for p in full_papers if p["has_pdf"])
    n_ph = sum(1 for p in full_papers if p["placeholder"])
    print(f"  Wrote {full_path} ({n_full} papers, {n_pdf} with PDF, {n_ph} placeholder, {full_path.stat().st_size // 1024} KB)")

    # Full-library stats
    fc = Counter(p["cluster_id"] for p in full_papers)
    full_stats = {
        "total_papers": n_full,
        "with_pdf": n_pdf,
        "placeholders": n_ph,
        "with_abstract": sum(1 for p in full_papers if p["abstract"]),
        "papers_by_cluster": {k: fc.get(k, 0) for k in FULL_CLUSTERS},
        "cluster_names": FULL_CLUSTERS,
    }
    with open(DATA_DIR / "full_stats.json", "w", encoding="utf-8") as f:
        json.dump(full_stats, f, ensure_ascii=False, indent=2)

    print(f"\nDone! {stats['total_papers']} featured papers, {n_full} full-library papers, "
          f"{stats['pdf_available']}/{stats['total_papers']} featured PDFs available.")


if __name__ == "__main__":
    main()
