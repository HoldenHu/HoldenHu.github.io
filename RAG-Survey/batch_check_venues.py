"""
Batch venue checker: searches Semantic Scholar + arxiv API for each paper
to determine if it has been published at a peer-reviewed venue.
"""
import json
import time
import urllib.request
import urllib.parse
import ssl
from pathlib import Path

SITE_DIR = Path(__file__).parent
DATA_DIR = SITE_DIR / "data"

with open(DATA_DIR / "papers.json", "r", encoding="utf-8") as f:
    papers = json.load(f)

# Focus on papers currently marked as arXiv-only
arxiv_papers = [p for p in papers if p["venue_short"] == "arXiv"]

print(f"Checking {len(arxiv_papers)} arXiv papers for real publication venues...\n")

ctx = ssl.create_default_context()

def search_semantic_scholar(title):
    """Search Semantic Scholar for paper by title."""
    try:
        query = urllib.parse.quote(title[:200])
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=3&fields=title,venue,journal,year,publicationVenue"
        req = urllib.request.Request(url, headers={"User-Agent": "RAG-Survey-Venue-Checker/1.0"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read())
            if "data" in data and data["data"]:
                return data["data"]
    except Exception as e:
        pass
    return []

def search_arxiv_metadata(arxiv_id):
    """Check arxiv metadata for journal-ref or comments about acceptance."""
    try:
        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}&max_results=1"
        req = urllib.request.Request(url, headers={"User-Agent": "RAG-Survey-Venue-Checker/1.0"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            text = resp.read().decode("utf-8")
            # Look for journal-ref or accepted notices
            import re
            journal_ref = re.search(r'<arxiv:journal-ref>(.*?)</arxiv:journal-ref>', text)
            comment = re.search(r'<arxiv:comment>(.*?)</arxiv:comment>', text)
            results = {}
            if journal_ref:
                results["journal_ref"] = journal_ref.group(1)
            if comment:
                results["comment"] = comment.group(1)
            return results
    except Exception as e:
        pass
    return {}

# Known real venue indicators from arxiv comments/journal-ref
VENUE_KEYWORDS = {
    "ACL": "ACL",
    "EMNLP": "EMNLP",
    "NeurIPS": "NeurIPS",
    "ICLR": "ICLR",
    "ICML": "ICML",
    "AAAI": "AAAI",
    "KDD": "KDD",
    "SIGIR": "SIGIR",
    "WWW": "WWW",
    "CIKM": "CIKM",
    "COLING": "COLING",
    "NAACL": "NAACL",
    "EACL": "EACL",
    "COLM": "COLM",
    "FSE": "FSE",
    "ICSE": "ICSE",
    "ASE": "ASE",
    "ISSTA": "ISSTA",
    "CVPR": "CVPR",
    "ICCV": "ICCV",
    "ECCV": "ECCV",
    "Neurips": "NeurIPS",
    "neurips": "NeurIPS",
    "NeurIPS": "NeurIPS",
    "Accepted at": None,  # flag to check further
    "accepted at": None,
    "to appear": None,
    "in proceedings": None,
    "Findings of": None,
}

found_venues = {}
still_arxiv = []
checked = 0

for i, paper in enumerate(arxiv_papers):
    bibkey = paper["bibkey"]
    title = paper["title"]
    arxiv_id = paper["arxiv_id"]

    if i % 5 == 0:
        print(f"[{i+1}/{len(arxiv_papers)}] Checking... ({bibkey})")

    # Step 1: Check arxiv metadata for journal-ref or acceptance comment
    venue_found = None
    if arxiv_id:
        arxiv_meta = search_arxiv_metadata(arxiv_id)
        journal_ref = arxiv_meta.get("journal_ref", "")
        comment = arxiv_meta.get("comment", "")

        # Check for venue indicators in journal-ref
        for keyword, venue_name in VENUE_KEYWORDS.items():
            if keyword in journal_ref:
                if venue_name:
                    venue_found = (f"{venue_name} ({journal_ref})", venue_name)
                    break
                else:
                    # Extract from the text: e.g. "Accepted at ACL 2025"
                    pass

        # Check for acceptance in comments
        if not venue_found:
            for keyword, venue_name in VENUE_KEYWORDS.items():
                if keyword in comment:
                    if venue_name:
                        venue_found = (f"{venue_name} (from comment: {comment[:80]})", venue_name)
                        break

    # Step 2: Search Semantic Scholar
    if not venue_found:
        ss_results = search_semantic_scholar(title)
        for result in ss_results:
            pub_venue = result.get("publicationVenue") or result.get("venue") or ""
            journal = result.get("journal") or {}
            journal_name = journal.get("name", "") if journal else ""

            venue_str = str(pub_venue) + " " + str(journal_name)

            # Skip if it's just arXiv
            if "arxiv" in venue_str.lower() and "arxiv" not in venue_str.lower().replace("arxiv.org", ""):
                continue

            for keyword, venue_name in VENUE_KEYWORDS.items():
                if venue_name and keyword.lower() in venue_str.lower():
                    venue_found = (f"{venue_name} [via Semantic Scholar]", venue_name)
                    break

            if venue_found:
                break

    checked += 1

    if venue_found:
        full_venue, short_venue = venue_found
        found_venues[bibkey] = (full_venue, short_venue)
        print(f"  FOUND {bibkey}: {full_venue}")
    else:
        still_arxiv.append(bibkey)

    # Rate limiting
    if i < len(arxiv_papers) - 1:
        time.sleep(0.3)

# Results
print(f"\n{'='*60}")
print(f"Checked: {checked} papers")
print(f"Found real venues: {len(found_venues)}")
print(f"Still arXiv-only: {len(still_arxiv)}")
print(f"\n=== FOUND VENUES ===")
for bk, (full, short) in sorted(found_venues.items()):
    print(f"  {bk}: {full} -> {short}")
print(f"\n=== STILL ARXIV-ONLY ({len(still_arxiv)}) ===")
for bk in still_arxiv:
    p = next(pp for pp in arxiv_papers if pp["bibkey"] == bk)
    print(f"  {bk}: {p['title'][:80]}")


# Save results
with open(DATA_DIR / "venue_check_results.json", "w", encoding="utf-8") as f:
    json.dump({
        "found": found_venues,
        "still_arxiv": still_arxiv,
        "checked": checked,
    }, f, ensure_ascii=False, indent=2)

print(f"\nResults saved to data/venue_check_results.json")
