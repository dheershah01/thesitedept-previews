#!/usr/bin/env python3
"""Daily outreach batch.

usage: run.py LEADS_RAW QUALIFIED [QUALIFIED ...] [--n 12] [--date YYYY-MM-DD]

1. Merges Google listing data with qualification results.
2. Skips anything already in tracker.json or suppression.json, or with an ok/good site.
3. Scores and picks today's batch.
4. Builds a preview page for each picked lead into ../previews/<slug>/.
5. Writes ../today/plan.json:
     emails      -> Ltd companies with a public business email (PECR-safe to cold email)
     visit_list  -> everyone else (sole traders / unknown / no email): walk in or call
6. Records everything in ../tracker.json.
Follow-ups due today are added to plan.json["follow_ups"].
"""
import json, os, sys, math, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import build as B
import emails as E

def load(p, default):
    return json.load(open(p)) if os.path.exists(p) else default

def score(l):
    w = {"none": 3, "social_only": 3, "booking_only": 2.6, "weak": 2.2}.get(l.get("website_status"), 0)
    if not w: return 0
    r = l.get("rating") or 0; n = l.get("rating_count") or 0
    s = w + (1 if r >= 4.5 else .5 if r >= 4.2 else 0) + min(math.log10(n + 1), 3) * .6
    if l.get("legal_status") == "ltd" and l.get("business_email"): s += 1.5
    return round(s, 2)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else E.CFG["daily_target"]
    today = sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv else datetime.date.today().isoformat()
    args = [a for a in args if a not in (str(n), today)]
    raw = {l["id"]: l for l in json.load(open(args[0]))}
    q = {}
    for p in args[1:]:
        for l in json.load(open(p)):
            q[l["id"]] = l
    tracker = load(os.path.join(ROOT, "tracker.json"), [])
    supp = set(x.lower() for x in load(os.path.join(ROOT, "suppression.json"), []))
    done = {t["id"] for t in tracker}
    pool = []
    for i, l in q.items():
        if i in done or i not in raw: continue
        lead = {**raw[i], **{k: v for k, v in l.items() if v not in (None, "", [])}}
        if (lead.get("business_email") or "").lower() in supp or lead["name"].lower() in supp: continue
        lead["score"] = score(lead)
        if lead["score"] > 0: pool.append(lead)
    pool.sort(key=lambda l: -l["score"])
    picked = pool[:n]
    base = E.CFG["previews_base"].rstrip("/")
    plan = {"date": today, "emails": [], "visit_list": [], "follow_ups": []}
    for lead in picked:
        slug, page, data = B.build(lead)
        os.makedirs(os.path.join(ROOT, "previews", slug), exist_ok=True)
        open(os.path.join(ROOT, "previews", slug, "index.html"), "w", encoding="utf-8").write(page)
        url = f"{base}/{slug}/"
        rec = {"id": lead["id"], "name": lead["name"], "niche": lead["niche"], "theme": data["theme"],
               "preview_url": url, "website_status": lead.get("website_status"), "legal_status": lead.get("legal_status"),
               "company_number": lead.get("company_number"), "email": lead.get("business_email"),
               "email_source": lead.get("email_source") or lead.get("website_url") or lead.get("instagram_or_facebook"),
               "phone": lead.get("phone_number"), "address": lead.get("address"), "score": lead["score"], "created": today}
        if lead.get("legal_status") == "ltd" and lead.get("business_email"):
            e = E.first_email(lead, url, data["theme"])
            plan["emails"].append({**e, "id": lead["id"], "preview_url": url})
            rec["channel"] = "email"; rec["status"] = "draft_created"
        else:
            why = "sole trader or not confirmed Ltd" if lead.get("legal_status") != "ltd" else "no public email"
            plan["visit_list"].append({"id": lead["id"], "name": lead["name"], "address": lead.get("address"),
                                       "phone": lead.get("phone_number"), "preview_url": url, "why_not_email": why,
                                       "website_status": lead.get("website_status"), "notes": lead.get("notes")})
            rec["channel"] = "visit_or_call"; rec["status"] = "to_visit"
        tracker.append(rec)
    # follow-ups: emails sent >= N days ago with no reply recorded
    fu_days = E.CFG["follow_up_after_days"]
    for t in tracker:
        if t.get("channel") == "email" and t.get("status") == "sent" and t.get("sent_date") and not t.get("followed_up"):
            if (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(t["sent_date"])).days >= fu_days:
                lead = {**raw.get(t["id"], {}), **q.get(t["id"], {})}
                plan["follow_ups"].append({**E.follow_up(lead, t["preview_url"]), "id": t["id"]})
    os.makedirs(os.path.join(ROOT, "today"), exist_ok=True)
    json.dump(plan, open(os.path.join(ROOT, "today", "plan.json"), "w"), indent=1, ensure_ascii=False)
    json.dump(tracker, open(os.path.join(ROOT, "tracker.json"), "w"), indent=1, ensure_ascii=False)
    print(f"{today}: {len(plan['emails'])} email drafts, {len(plan['visit_list'])} visit/call, {len(plan['follow_ups'])} follow-ups; pool left {len(pool)-len(picked)}")

if __name__ == "__main__":
    main()
