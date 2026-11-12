#!/usr/bin/env python3
"""Write the first email and the follow-up for a qualified lead.

Only call this for leads with legal_status == "ltd" and a public business_email
(PECR: sole traders and partnerships need consent first). Returns dicts with
to / subject / body. Keep emails under ~90 words, one link, clear opt-out.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "config.json")))

PROBLEM_LINES = {
    "none": "I couldn't find a website for {short}, so people searching for you on Google only see the map listing.",
    "social_only": "At the moment, people who search for {short} end up on your {social} page, which makes it harder for new customers to see prices and book.",
    "booking_only": "At the moment, people who search for {short} land on your {platform} page, which also shows them other businesses nearby.",
    "weak": "I had a look at your current site and spotted {problem}, which could be costing you {goal}.",
}
GOAL = {"barber": "bookings", "salon": "bookings", "restaurant": "table bookings and orders",
        "cafe": "orders", "trades": "enquiries", "fitness": "new clients"}

def short_name(name):
    n = re.split(r"\s+[|/\-–:]\s+|\s*\|\s*", name)[0]
    n = re.sub(r"\s*-\s*Coventry$", "", n, flags=re.I)
    n = re.sub(r"\s+(Ltd|Limited)\.?$", "", n, flags=re.I)
    return n.strip()

def first_email(lead, preview_url, theme):
    short = short_name(lead["name"])
    status = lead.get("website_status") or "none"
    if status in ("ok", "good"):
        raise ValueError("Lead already has a decent website; skip it.")
    problems = [p for p in (lead.get("site_problems") or []) if p]
    social = "Instagram" if "instagram" in (lead.get("instagram_or_facebook") or "").lower() else "Facebook"
    platform = "booking app"
    for p in ("Fresha", "Booksy", "Treatwell", "Just Eat", "Deliveroo", "Uber Eats", "Checkatrade", "MyBuilder"):
        if p.lower() in json.dumps(lead).lower():
            platform = p; break
    line = PROBLEM_LINES[status].format(short=short, social=social, platform=platform,
                                        problem=(problems[0].rstrip(".").lower() if problems else "a few things that make it hard to use on a phone"),
                                        goal=GOAL.get(theme, "customers"))
    owner = (lead.get("owner_first_name") or "").strip()
    hello = f"Hi {owner}," if owner else f"Hi {short} team,"
    s = CFG
    subject = f"A homepage for {short}" if len(short) <= 24 else "Your new homepage"
    has_rev = bool(lead.get("reviews"))
    has_hrs = bool(lead.get("weekday_hours"))
    basis = ", using your real hours and reviews" if (has_rev and has_hrs) else (", using your real Google reviews" if has_rev else "")
    body = f"""{hello}

I'm {s['sender_name']}, a Warwick student who builds websites for local businesses across the Midlands. {line}

So I made a free preview of a new homepage for {short}{basis}:
{preview_url}

If you like it, I can have it live on your own domain within a week, from {s['from_price']} with no monthly fees. If not, no worries at all.

{s['sender_name']}
The Site Dept. · {s['portfolio_url']}

Not interested? Just reply "no thanks" and I won't email again."""
    return {"to": lead["business_email"], "subject": subject, "body": body}

def follow_up(lead, preview_url):
    short = short_name(lead["name"])
    s = CFG
    body = f"""Hi again,

Just bumping this in case it got buried. Your preview is still here if you'd like a look:
{preview_url}

Happy to change anything, or put your own photos and prices in. A one-word reply is fine.

{s['sender_name']}
The Site Dept.

Reply "no thanks" and I won't email again."""
    return {"to": lead["business_email"], "subject": f"Re: A homepage for {short}" if len(short) <= 24 else "Re: Your new homepage", "body": body}

if __name__ == "__main__":
    demo = {"name": "Example Barbers Ltd", "website_status": "booking_only", "business_email": "info@example.com",
            "notes": "uses Fresha", "site_problems": []}
    e = first_email(demo, "https://thesitedept-previews.pages.dev/example-barbers/", "barber")
    print(e["subject"]); print(e["body"]); print(len(e["body"].split()), "words")
