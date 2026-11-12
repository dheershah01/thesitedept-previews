#!/usr/bin/env python3
"""Build a personalised preview page for one lead.

usage: build.py leads.json LEAD_ID [overrides.json] [--out DIR]
Writes DIR/<slug>/index.html (default DIR = ../previews) and prints the slug.
"""
import json, re, sys, os, html

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()

def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:48] or "preview"

def theme_for(lead):
    name = (lead.get("name") or "").lower()
    types = set(lead.get("types") or [])
    n = lead.get("niche")
    if n == "barber_salon":
        return "barber" if ("barber" in name or "barber_shop" in types or "fade" in name) else "salon"
    if n == "food":
        if types & {"cafe", "coffee_shop", "bakery", "brunch_restaurant"} or re.search(r"caf|coffee|bakery|brunch|tea", name):
            return "cafe"
        return "restaurant"
    if n == "trades":
        return "trades"
    return "fitness"

def parse_time(s):
    s = s.strip().replace(" ", " ").replace(" ", " ").upper()
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?", s)
    if not m:
        return None, None
    h = int(m.group(1)); mi = int(m.group(2) or 0); ap = m.group(3)
    return h, mi, ap

def to_dec(h, mi, ap):
    if ap == "PM" and h != 12: h += 12
    if ap == "AM" and h == 12: h = 0
    return h + mi / 60

def parse_hours(lines):
    out = {}
    for line in lines or []:
        line = line.replace(" ", " ").replace(" ", " ")
        if ":" not in line:
            continue
        day, rest = line.split(":", 1)
        rest = rest.strip()
        if rest.lower().startswith("closed"):
            out[day] = [0, 0]; continue
        if "24 hours" in rest.lower():
            out[day] = [0, 23.99]; continue
        ranges = [r for r in rest.split(",") if r.strip()]
        try:
            first = ranges[0].split("–") if "–" in ranges[0] else ranges[0].split("-")
            last = ranges[-1].split("–") if "–" in ranges[-1] else ranges[-1].split("-")
            a = parse_time(first[0]); b = parse_time(last[1])
            # Google omits AM/PM on the start when it matches the end ("12–3 PM")
            ap_a = a[2] or b[2]
            open_t = to_dec(a[0], a[1], ap_a)
            close_t = to_dec(b[0], b[1], b[2])
            if open_t > close_t and not a[2]:
                open_t = to_dec(a[0], a[1], "AM")
            if close_t <= open_t:
                close_t += 24 if close_t < 6 else 0
            out[day] = [round(open_t, 2), round(min(close_t, 23.99), 2)]
        except Exception:
            continue
    return out

NEG = re.compile(r"\b(rude|worst|terrible|awful|disappoint|never again|unprofessional|waited|wait(ing)? for|dirty|cold food|overpriced|refund|complain|uncomfortable|pathetic|didn'?t|not happy|poor)\b", re.I)

def pick_reviews(texts, k=3):
    out = []
    for t in texts or []:
        t = re.sub(r"\s+", " ", t).strip()
        if not t or NEG.search(t):
            continue
        sents = re.split(r"(?<=[.!?])\s+", t)
        snip = ""
        for s in sents:
            if len(snip) + len(s) > 150:
                break
            snip = (snip + " " + s).strip()
        if not snip:
            snip = t[:140].rsplit(" ", 1)[0] + "…"
        if len(snip) < 25:
            continue
        out.append({"text": snip, "who": "Google review"})
        if len(out) == k:
            break
    return out

COPY = {
    "barber": dict(headline=["Sharp cuts.", "Booked in seconds."], intro="{name}: fades, tapers and beard work in {area}. Check the prices, pick a time and walk straight into the chair.",
                   cta="Book a cut", kicker="Price list", title="Cuts & prices",
                   services=[("Skin fade", "Bald to blend, finished sharp"), ("Taper fade", "Clean neckline, length kept on top"), ("Men's cut", "Clipper or scissor"), ("Beard trim & line-up", "Shape, trim and sharp edges"), ("Kids' cut", "Under 12s")]),
    "salon": dict(headline=["Hair you'll love,", "every visit."], intro="{name} in {area}: cuts, colour and styling from a team that listens first. See the menu and book your next appointment online.",
                  cta="Book an appointment", kicker="The menu", title="Services",
                  services=[("Cut & blow-dry", "Consultation, wash, cut and finish"), ("Colour", "Full head, roots or highlights"), ("Balayage", "Hand-painted, lived-in colour"), ("Blow-dry", "Smooth, bouncy or waved"), ("Treatments", "Repair and shine")]),
    "restaurant": dict(headline=["Proper food,", "made fresh."], intro="{name} in {area}. See the menu, book a table, or order for collection without the delivery-app markup.",
                       cta="Book a table", kicker="The menu", title="On the menu",
                       services=[("Starters", "Small plates to share"), ("Mains", "House favourites"), ("Sides", "The perfect extras"), ("Desserts", "Something sweet"), ("Drinks", "Soft drinks and more")]),
    "cafe": dict(headline=["Good coffee.", "Great food."], intro="{name} in {area}. Fresh coffee, good food and a warm welcome. See today's menu and order ahead for collection.",
                 cta="Order ahead", kicker="The menu", title="Coffee & food",
                 services=[("Coffee", "Flat white, latte, cappuccino and more"), ("Breakfast & brunch", "Served every morning"), ("Lunch", "Sandwiches, toasties and specials"), ("Cakes & bakes", "Fresh every day"), ("Tea & soft drinks", "Hot and cold")]),
    "trades": dict(headline=["Reliable work.", "Fair, fixed quotes."], intro="{name}, covering {area} and nearby. Tell us what you need and get a clear quote, fast.",
                   cta="Get a free quote", kicker="What we do", title="Services",
                   services=[("Call-outs & repairs", "Fast response when something goes wrong"), ("Installations", "Done properly, first time"), ("Planned work", "Quoted upfront, no surprises"), ("Maintenance", "Keep everything running safely"), ("Free quotes", "Tell us the job and we'll price it")]),
    "fitness": dict(headline=["Get strong.", "Stay strong."], intro="{name} in {area}. Coaching that fits around real life, with a plan, check-ins and results you can see.",
                    cta="Book a free consult", kicker="Ways to train", title="Plans",
                    services=[("Free consultation", "Talk through your goals, no pressure"), ("1:1 coaching", "Coached sessions built around you"), ("Online coaching", "Programme, check-ins and support"), ("Small groups", "Train with others, coached properly")]),
}

def area_of(addr):
    m = re.search(r",\s*([A-Za-z' ]+?)\s+(CV\d{1,2})", addr or "")
    return "Coventry" if not m else ("Coventry" if m.group(1).strip().lower() == "coventry" else m.group(1).strip() + ", Coventry")

def clean_name(n):
    n = re.split(r"\s+[|/\-–:]\s+|\s*\|\s*|\s*/\s*", n)[0].strip()
    n = re.sub(r"\s*-\s*Coventry$", "", n, flags=re.I).strip()
    return n

def build(lead, overrides=None):
    lead = dict(lead); lead["name"] = clean_name(lead["name"])
    theme = theme_for(lead)
    c = COPY[theme]
    area = area_of(lead.get("address"))
    data = {
        "theme": theme,
        "name": lead["name"],
        "shortName": re.split(r"\s[|\-–:]\s", lead["name"])[0][:28],
        "rating": f'{lead["rating"]:.1f}' if lead.get("rating") else "",
        "reviewCount": str(lead.get("rating_count") or ""),
        "tagline": area,
        "headline": c["headline"],
        "intro": c["intro"].format(name=re.split(r"\s[|\-–:]\s", lead["name"])[0], area=area),
        "cta": {"label": c["cta"], "url": (lead.get("booking_url") or "")},
        "secondaryLabel": "See " + c["title"].lower(),
        "phone": (lead.get("phone_number") or "").replace("+44 ", "0").replace("+44", "0"),
        "address": (lead.get("address") or "").replace(", UK", ""),
        "servicesKicker": c["kicker"],
        "servicesTitle": c["title"],
        "services": [{"name": n, "desc": d, "price": ""} for n, d in c["services"]],
        "servicesNote": "Your real prices and services go here. Send us your price list and we'll add it.",
        "reviews": pick_reviews(lead.get("reviews")),
        "hours": parse_hours(lead.get("weekday_hours")),
    }
    if overrides:
        data.update(overrides)
    if not data["cta"]["url"]:
        data["cta"]["url"] = ""  # template falls back to tel:
    page = TEMPLATE.replace("__TITLE__", html.escape(lead["name"] + " | Website preview")).replace(
        "__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    return slugify(lead["name"]), page, data

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_dir = os.path.join(HERE, "..", "previews")
    if "--out" in sys.argv:
        out_dir = sys.argv[sys.argv.index("--out") + 1]
        args = [a for a in args if a != out_dir]
    leads = json.load(open(args[0]))
    lead = next(l for l in leads if l["id"] == args[1])
    ov = json.load(open(args[2])) if len(args) > 2 else None
    slug, page, data = build(lead, ov)
    os.makedirs(os.path.join(out_dir, slug), exist_ok=True)
    open(os.path.join(out_dir, slug, "index.html"), "w", encoding="utf-8").write(page)
    print(slug, data["theme"], len(data["reviews"]), "reviews", len(data["hours"]), "days")
