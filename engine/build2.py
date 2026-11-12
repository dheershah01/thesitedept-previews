#!/usr/bin/env python3
"""Preview builder v2: photo-led, per-niche art direction.

build(lead) -> (slug, html, data)
A lead is a dict. Everything is optional except name + theme/niche. Real facts the
business has published (services, phone, logo, reviews, areas, badges) override the
theme defaults, so each preview reads like *their* site, not a template.
"""
import json, os, re, html
from build import parse_hours, pick_reviews, slugify, clean_name  # reuse tested helpers

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = open(os.path.join(HERE, "template2.html"), encoding="utf-8").read()
CFG = json.load(open(os.path.join(HERE, "config.json")))

U = "https://images.unsplash.com/"
def u(pid, w=1600):
    return f"{U}{pid}?auto=format&fit=crop&w={w}&q=70"

# Hand-picked free Unsplash photos (checked visually). Used only when the business
# has no usable photos of its own; the page then says they are placeholders.
STOCK = {
    "electrician": ["photo-1758101755915-462eddc23f57", "photo-1604610728890-6f4b631ed081", "photo-1656402887556-e727ffe1f6d7", "photo-1621905251189-08b45d6a269e"],
    "heating":     ["photo-1650551182991-b07558247564", "photo-1676210134190-3f2c0d5cf58d", "photo-1584622650111-993a426fbf0a", "photo-1676210134188-4c05dd172f89"],
    "plumber":     ["photo-1676210134188-4c05dd172f89", "photo-1584622650111-993a426fbf0a", "photo-1650551182991-b07558247564", "photo-1749532125405-70950966b0e5"],
    "car":         ["photo-1591278169757-deac26e49555", "photo-1522775644932-1e20a2479066", "photo-1626995587693-c50c9a5544c6", "photo-1534093607318-f025413f49cb"],
    "trades":      ["photo-1621905252507-b35492cc74b4", "photo-1584622650111-993a426fbf0a", "photo-1650551182991-b07558247564", "photo-1676210134188-4c05dd172f89"],
    "barber":      ["photo-1585747860715-2ba37e788b70", "photo-1593702275687-f8b402bf1fb5", "photo-1621605815971-fbc98d665033", "photo-1503951914875-452162b0f3f1"],
    "salon":       ["photo-1633681926022-84c23e8cb2d6", "photo-1580618672591-eb180b1a973f", "photo-1634449571010-02389ed0f9b0", "photo-1562322140-8baeececf3df"],
    "restaurant":  ["photo-1517248135467-4c7edcad34c4", "photo-1414235077428-338989a2e8c0", "photo-1544025162-d76694265947", "photo-1600891964599-f61ba0e24092"],
    "cafe":        ["photo-1554118811-1e0d58224f24", "photo-1541167760496-1628856ab772", "photo-1623334044303-241021148842", "photo-1600093463592-8e36ae95ef56"],
    "fitness":     ["photo-1534438327276-14e5300c3a48", "photo-1758875569256-f37c438cac65", "photo-1517838277536-f5f99be501cd", "photo-1623874514711-0f321325f318"],
}

FONTS = {
    "trades":     "family=Archivo:wght@500;700;800&family=Inter:wght@400;500;600;700",
    "fitness":    "family=Archivo:wght@500;700;800;900&family=Inter:wght@400;500;600;700",
    "barber":     "family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700",
    "salon":      "family=Fraunces:ital,opsz,wght@0,9..144,300..600;1,9..144,300..600&family=Inter:wght@400;500;600;700",
    "cafe":       "family=Fraunces:ital,opsz,wght@0,9..144,400..600;1,9..144,400..600&family=DM+Sans:wght@400;500;600;700",
    "restaurant": "family=Anton&family=Inter:wght@400;500;600;700",
}

THEME = {
    "trades": dict(cta="Get a free quote", kicker_svc="What we do", title_svc="Services",
        steps_title="Sorted, without the hassle.",
        steps=[("Tell us the job", "Call, message or use the form. A photo helps us quote faster."),
               ("Get a clear quote", "A fixed price before we start. No surprises on the invoice."),
               ("Job done properly", "Tidy, safe work, and we clear up after ourselves.")],
        cta_title="Need a hand? Let’s talk.", form_title="Ask for a free quote", form_btn="Request my quote",
        form_ph="What’s the job? Postcode helps too.", sticky="Free quote"),
    "barber": dict(cta="Book a cut", kicker_svc="Price list", title_svc="Cuts & prices",
        steps_title="In the chair in three taps.",
        steps=[("Pick your cut", "Fade, taper, beard: see every price upfront."),
               ("Choose a time", "Book online, day or night. No phone tag."),
               ("Walk in, sit down", "No waiting around. Leave sharp.")],
        cta_title="Fresh cut this week?", form_title="Ask a question", form_btn="Send", form_ph="Your question", sticky="Book now"),
    "salon": dict(cta="Book an appointment", kicker_svc="The menu", title_svc="Services",
        steps_title="Your next appointment, sorted.",
        steps=[("Choose a service", "Cut, colour or treatment: every price on show."),
               ("Pick a time", "Book online whenever suits you."),
               ("Relax", "We’ll take it from there.")],
        cta_title="Treat yourself this week.", form_title="Ask us anything", form_btn="Send", form_ph="Your question", sticky="Book now"),
    "restaurant": dict(cta="Book a table", kicker_svc="The menu", title_svc="On the menu",
        steps_title="Eat in or take it home.",
        steps=[("See the menu", "Every dish and price, right here."),
               ("Book or order", "Reserve a table or order for collection."),
               ("Enjoy", "Fresh, made to order.")],
        cta_title="Hungry? Come and eat.", form_title="Book a table", form_btn="Request booking", form_ph="Date, time and number of people", sticky="Book a table"),
    "cafe": dict(cta="See the menu", kicker_svc="The menu", title_svc="Coffee & food",
        steps_title="Your usual, ready when you are.",
        steps=[("Browse the menu", "Coffee, breakfast, lunch and bakes."),
               ("Order ahead", "Skip the queue on busy mornings."),
               ("Collect & go", "Or stay a while.")],
        cta_title="Coffee’s on.", form_title="Get in touch", form_btn="Send", form_ph="Catering, events or a question", sticky="Menu"),
    "fitness": dict(cta="Book a free consult", kicker_svc="Ways to train", title_svc="Plans",
        steps_title="Start this week.",
        steps=[("Free consultation", "Talk through your goals. No pressure, no hard sell."),
               ("Your plan", "Training built around your schedule and level."),
               ("See results", "Check-ins and support so you stay on track.")],
        cta_title="Your first session is on us.", form_title="Book your free consult", form_btn="Book my consult", form_ph="Your goal, and when you can train", sticky="Free consult"),
}

def uk_phone(p):
    p = (p or "").strip()
    if not p: return "", "", ""
    digits = re.sub(r"[^\d+]", "", p)
    if digits.startswith("+44"): digits = "0" + digits[3:]
    disp = digits
    if re.fullmatch(r"07\d{9}", digits): disp = f"{digits[:5]} {digits[5:]}"
    elif re.fullmatch(r"0\d{10}", digits): disp = f"{digits[:5]} {digits[5:]}" if digits[1] != "2" else f"{digits[:3]} {digits[3:7]} {digits[7:]}"
    wa = ("44" + digits[1:]) if digits.startswith("07") else ""
    return digits, disp, wa

def build(lead):
    L = dict(lead)
    name = clean_name(L["name"])
    short = L.get("short_name") or re.sub(r"\s+(ltd|limited|llp)\.?$", "", name, flags=re.I)
    theme = L.get("theme") or "trades"
    T = THEME[theme]
    stock_key = L.get("stock") or theme
    own = L.get("photos") or []
    photos_stock = len(own) < 4
    ids = STOCK[stock_key]
    pics = own if not photos_stock else [u(i) for i in ids]
    phone, disp, wa = uk_phone(L.get("phone"))
    if L.get("whatsapp") is False: wa = ""
    reviews = L.get("reviews_clean") or pick_reviews(L.get("reviews"))
    data = {
        "theme": theme,
        "accent": L.get("accent"), "accentInk": L.get("accent_ink"),
        "name": name, "shortName": short,
        "logo": L.get("logo"),
        "kicker": L["kicker"],
        "headline": L["headline"],
        "intro": L["intro"],
        "cta": {"label": L.get("cta") or T["cta"], "url": L.get("booking_url") or ""},
        "phone": phone, "phoneDisplay": disp, "whatsapp": wa if L.get("whatsapp", True) else "",
        "email": L.get("email") or "",
        "rating": f'{L["rating"]:.1f}' if L.get("rating") else "",
        "reviewCount": str(L.get("rating_count") or ""),
        "facts": L.get("facts") or [],
        "servicesKicker": L.get("services_kicker") or T["kicker_svc"],
        "servicesTitle": L.get("services_title") or T["title_svc"],
        "servicesIntro": L.get("services_intro") or "",
        "services": [{"name": s[0], "desc": s[1], "price": (s[2] if len(s) > 2 else "")} for s in L["services"]],
        "servicesNote": L.get("services_note", "Prices to add: send us your price list and they’ll appear here."),
        "photos": {"hero": pics[0], "heroPos": L.get("hero_pos"), "gallery": pics[1:4], "stock": photos_stock,
                   "caption": "Placeholder photos. We’d use real photos of your work." if photos_stock else ""},
        "reviews": reviews,
        "reviewsTitle": L.get("reviews_title"),
        "stepsKicker": "How it works", "stepsTitle": T["steps_title"], "steps": L.get("steps") or T["steps"],
        "contactTitle": L.get("contact_title") or "Get in touch.",
        "contactIntro": L.get("contact_intro") or "",
        "hours": parse_hours(L.get("weekday_hours")),
        "areas": L.get("areas") or [],
        "aboutLine": L.get("about_line") or "",
        "mapsQuery": L.get("maps_query") or "",
        "addressShort": L.get("address_short") or "",
        "formTitle": T["form_title"], "formButton": T["form_btn"], "formPlaceholder": T["form_ph"],
        "ctaTitle": L.get("cta_title") or T["cta_title"],
        "stickyLabel": T["sticky"],
        "companyLine": L.get("company_line") or "",
        "pitchEmail": CFG.get("sender_email", ""), "pitchName": CFG.get("sender_name", "us"),
    }
    fonts = f'<link href="https://fonts.googleapis.com/css2?{FONTS[theme]}&display=swap" rel="stylesheet">'
    page = (TEMPLATE.replace("__TITLE__", html.escape(name + " | Website preview"))
            .replace("__FONTS__", fonts)
            .replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
    return slugify(L.get("slug") or short), page, data
