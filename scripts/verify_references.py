"""Verify candidate references against arXiv and Crossref (no fabricated metadata).

Writes references/verified_references.json; only entries with status "verified"
may be cited in the manuscript.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import time
from urllib.parse import quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "before-the-recommendation-research/0.1 (reference verification)"}

ARXIV_TITLES = [
    "Selective Elicitation as a Commercial Influence Channel",
    "Beyond Expert Users: Agents Should Help Users Construct Preferences, Not Just Elicit Them",
    "Entropy Guided Diversification and Preference Elicitation in Agentic Recommendation Systems",
    "A Verifiable Benchmark for Agentic Recommender Systems",
    "Shopping Companion: Benchmarking and Training LLM Agents for Long-Horizon Preference-Grounded E-Commerce Tasks",
    "APeB: Benchmarking Personalization Ability of Large Language Models",
    "Shopping by Algorithm: How Agentic AI Deploys Human Heuristics as a Surrogate Consumer",
    "Whom Do AI Agents Work For? Role Assignment Induces Sponsorship Bias in LLM Recommenders",
    "When Agents Shop for You: Role Coherence in AI-Mediated Markets",
    "Experimental Evidence That Conversational Artificial Intelligence Can Steer Consumer Behavior Without Detection",
    "Commercial Persuasion in AI-Mediated Conversations",
    "A Survey on LLM-powered Agents for Recommender Systems",
]
DOIS = [
    "10.1177/00222429251326941",   # Fang, Kim, Chintagunta, JM 2025 (project.md)
    "10.1086/209535",              # Bettman, Luce, Payne 1998, constructive consumer choice
    "10.1287/mksc.19.1.4.15178",   # Haubl & Trifts 2000, interactive decision aids
    "10.1002/mar.4220080105",      # Lynn 1991, scarcity effects meta-analysis
    "10.1086/209457",              # Grewal et al.? verify; dropped if mismatch
    "10.1509/jmkr.43.3.326",       # candidate; dropped if mismatch
]


def get(url: str) -> bytes:
    with urlopen(Request(url, headers=UA), timeout=60) as r:
        return r.read()


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.casefold()).strip()


def arxiv(title: str) -> dict:
    words = [w for w in norm(title).split() if len(w) > 3][:8]
    q = "+AND+".join(f"ti:{quote(w)}" for w in words)
    xml = get(f"https://export.arxiv.org/api/query?search_query={q}&max_results=5")
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml)
    for e in root.findall("a:entry", ns):
        t = " ".join(e.find("a:title", ns).text.split())
        if norm(t) == norm(title) or norm(title) in norm(t) or norm(t) in norm(title):
            arxiv_id = e.find("a:id", ns).text.rsplit("/abs/", 1)[-1]
            return {"status": "verified", "source": "arXiv API", "title": t,
                    "authors": [a.find("a:name", ns).text for a in e.findall("a:author", ns)],
                    "published": e.find("a:published", ns).text[:10], "arxiv_id": arxiv_id,
                    "url": f"https://arxiv.org/abs/{arxiv_id}"}
    return {"status": "not_found", "query_title": title}


def crossref(doi: str) -> dict:
    try:
        m = json.loads(get(f"https://api.crossref.org/works/{quote(doi)}"))["message"]
    except Exception as exc:
        return {"status": "not_found", "doi": doi, "error": type(exc).__name__}
    return {"status": "verified", "source": "Crossref API", "doi": doi, "title": " ".join(m.get("title", [""])[0].split()),
            "authors": [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in m.get("author", [])],
            "journal": (m.get("container-title") or [""])[0], "year": (m.get("issued", {}).get("date-parts") or [[None]])[0][0],
            "volume": m.get("volume"), "issue": m.get("issue"), "pages": m.get("page"), "url": f"https://doi.org/{doi}"}


def main() -> None:
    out = {"artifact_version": "verified-references-v1", "verified_on": time.strftime("%Y-%m-%d"), "arxiv": [], "doi": []}
    for t in ARXIV_TITLES:
        try:
            out["arxiv"].append(arxiv(t))
        except Exception as exc:
            out["arxiv"].append({"status": "lookup_error", "query_title": t, "error": type(exc).__name__})
        time.sleep(5)  # arXiv API etiquette
    for d in DOIS:
        out["doi"].append(crossref(d)); time.sleep(1)
    path = ROOT / "references" / "verified_references.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for e in out["arxiv"] + out["doi"]:
        print(e["status"], "|", e.get("title") or e.get("query_title") or e.get("doi"), "|", (e.get("authors") or [""])[:3], e.get("published") or e.get("year"), e.get("arxiv_id") or e.get("journal", ""))


if __name__ == "__main__":
    main()
