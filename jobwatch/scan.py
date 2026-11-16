#!/usr/bin/env python3
"""Job watcher: finds small, fully-digital gigs Claude can do end to end.

Source: Freelancer.com public projects API (no login needed).
Prints new matching jobs as JSON and remembers what it has already shown
in seen.json, so each job is only reported once.

Usage:
  python3 scan.py                 # live scan
  python3 scan.py --fixture f.json  # test with saved API results
"""
import json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SEEN = os.path.join(HERE, "seen.json")
API = "https://www.freelancer.com/api/projects/0.1/projects/active/"

# Searches for work Claude can produce as files (spreadsheets, documents, code, writing).
QUERIES = [
    "excel", "spreadsheet", "google sheets", "financial model", "excel vba",
    "data cleaning", "csv", "python script", "data analysis", "statistics",
    "cv", "resume", "cover letter", "linkedin profile", "business plan",
    "powerpoint", "presentation", "report writing", "research", "pitch deck",
    "proofreading", "editing", "template", "dashboard", "budget",
]

# Things Claude can't deliver alone (physical, manual typing from scans, calls, design tools, apps, accounts).
EXCLUDE = [
    "scanned", "scan ", "images", "handwritten", "business card", "paper",
    "phone", "call", "cold call", "video", "voice", "logo", "illustrat",
    "photoshop", "figma", "android", "ios", "mobile app", "flutter",
    "wordpress", "shopify", "amazon", "flipkart", "ebay", "seo", "backlink",
    "social media", "instagram", "tiktok", "facebook", "virtual assistant",
    "lead", "email list", "database of", "testing", "qa ", "cnc", "pcb",
    "autocad", "solidworks", "ninjatrader", "mt4", "mt5", "trading bot",
    "crypto", "telegram", "whatsapp", "translation", "translate",
    "transcri", "assignment", "homework", "exam", "thesis", "dissertation",
    "essay", "coursework", "on-site", "onsite", "full time", "full-time",
    "long term", "long-term", "daily task", "per hour", "hourly",
]

MIN_GBP, MAX_GBP = 25, 400      # budget ceiling must fall in this range
MAX_BIDS = 60                   # skip jobs already flooded
MAX_AGE_H = 3                   # only fresh jobs
GBP_RATE_FALLBACK = 1.32        # USD per GBP if not found in results


def fetch(query):
    params = {
        "query": query, "limit": 40, "job_details": "true", "compact": "true",
        "sort_field": "time_updated", "project_types[]": "fixed",
        "full_description": "false",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 jobwatch"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)["result"]["projects"]


def english(text):
    if not text:
        return True
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    words = text.lower().split()
    common = {"the", "and", "i", "a", "to", "need", "for", "my", "of", "with", "in", "is"}
    return ascii_chars / max(len(text), 1) > 0.97 and any(w in common for w in words)


def to_gbp(amount, cur, gbp_rate):
    usd = (amount or 0) * (cur.get("exchange_rate") or 1)
    return usd / gbp_rate


def main():
    fixture = None
    if "--fixture" in sys.argv:
        fixture = sys.argv[sys.argv.index("--fixture") + 1]
    seen = set()
    if os.path.exists(SEEN):
        seen = set(json.load(open(SEEN)).get("ids", []))

    projects, errors = {}, []
    if fixture:
        for p in json.load(open(fixture)):
            projects[p["id"]] = p
    else:
        for q in QUERIES:
            try:
                for p in fetch(q):
                    projects[p["id"]] = p
            except Exception as e:  # keep going if one search fails
                errors.append(f"{q}: {e}")
            time.sleep(0.4)

    gbp_rate = GBP_RATE_FALLBACK
    for p in projects.values():
        if p["currency"]["code"] == "GBP":
            gbp_rate = p["currency"]["exchange_rate"]
            break

    now = time.time()
    matches = []
    for p in projects.values():
        if p["id"] in seen or p.get("type") != "fixed":
            continue
        title = p.get("title") or ""
        desc = p.get("preview_description") or ""
        text = f"{title} {desc}".lower()
        if not english(title + " " + desc):
            continue
        if any(x in text for x in EXCLUDE):
            continue
        b = p.get("budget") or {}
        lo = to_gbp(b.get("minimum"), p["currency"], gbp_rate)
        hi = to_gbp(b.get("maximum"), p["currency"], gbp_rate)
        if not (MIN_GBP <= hi and lo <= MAX_GBP):
            continue
        bids = (p.get("bid_stats") or {}).get("bid_count") or 0
        if bids > MAX_BIDS:
            continue
        age_h = (now - (p.get("time_submitted") or 0)) / 3600
        if age_h > MAX_AGE_H and not fixture:
            continue
        score = min(hi, 300) / (bids + 3) / (1 + age_h)
        matches.append({
            "id": p["id"], "title": title.strip(),
            "budget_gbp": f"£{lo:.0f}–£{hi:.0f}",
            "original": f"{p['currency']['code']} {b.get('minimum'):.0f}–{b.get('maximum'):.0f}",
            "bids": bids, "age_min": round(age_h * 60),
            "url": "https://www.freelancer.com/projects/" + (p.get("seo_url") or str(p["id"])),
            "preview": desc.strip().replace("\n", " ")[:200],
            "score": round(score, 3),
        })

    matches.sort(key=lambda m: -m["score"])
    if not fixture:
        ids = list(seen | {p for p in projects})[-5000:]
        json.dump({"ids": ids, "updated": int(now)}, open(SEEN, "w"))
    print(json.dumps({"checked": len(projects), "new_matches": matches,
                      "errors": errors}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
