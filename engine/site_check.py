#!/usr/bin/env python3
"""Find a company's website by guessing domains, judge its quality, extract published emails.

usage: site_check.py IN.json OUT.json [--limit N]
Adds: website_url, website_status (none/weak/ok/good), site_problems, business_email, email_source.
"""
import json, re, sys, os, datetime, concurrent.futures as cf
import urllib.request, ssl, socket
socket.setdefaulttimeout(12)
STOP = {"ltd", "limited", "the", "and", "uk", "co", "company", "services", "service", "group", "&", "of", "t/a"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
BAD_EMAIL = re.compile(r"(example|sentry|wixpress|domain\.com|yourname|email@|godaddy|\.png|\.jpg|\.webp|noreply|no-reply)", re.I)
YEAR = datetime.date.today().year

def words(name):
    w = [x for x in re.sub(r"[^a-z0-9& ]", " ", name.lower()).split() if x not in STOP]
    return w

def candidates(name):
    w = words(name)
    if not w: return []
    joined = "".join(w); first2 = "".join(w[:2]); hy = "-".join(w)
    c = []
    for base in dict.fromkeys([joined, first2, hy]):
        if 3 <= len(base) <= 40:
            for tld in (".co.uk", ".com", ".uk"):
                c.append(base + tld)
    return c[:7]

def fetch(url):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; TheSiteDeptCheck/1.0)"})
    t0 = datetime.datetime.now()
    with urllib.request.urlopen(req, timeout=12, context=ctx) as r:
        body = r.read(1_500_000).decode("utf-8", "ignore")
        return r.geturl(), body, (datetime.datetime.now() - t0).total_seconds(), len(body)

LOCAL = re.compile(r"(coventry|warwick|leamington|kenilworth|rugby|nuneaton|solihull|birmingham|bedworth|stratford|redditch|sutton coldfield|west midlands|warwickshire|\bCV\d{1,2}\b|\bB\d{1,2}\s?\d[A-Z]{2})", re.I)
PARKED = re.compile(r"(domain (is )?for sale|buy this domain|parked|this domain may be for sale|coming soon|under construction|godaddy\.com/forsale|sedoparking|hugedomains)", re.I)

def matches(name, html):
    t = html.lower()
    title = re.search(r"<title[^>]*>(.*?)</title>", t, re.S)
    hay = (title.group(1) if title else "") + " " + t[:20000]
    w = [x for x in words(name) if len(x) > 2]
    if not w: return False
    hits = sum(1 for x in w if x in hay)
    return hits >= max(1, min(2, len(w)))

def judge(html, secs, size, url):
    probs = []
    h = html.lower()
    if 'name="viewport"' not in h and "name='viewport'" not in h: probs.append("not built for phones (no mobile layout)")
    yrs = [int(y) for y in re.findall(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?(20\d\d)", h)]
    if yrs and max(yrs) <= YEAR - 3: probs.append(f"footer still says {max(yrs)}")
    if url.startswith("http://"): probs.append("no secure https padlock")
    if secs > 6: probs.append("slow to load")
    if size < 3000: probs.append("very thin page with little information")
    if re.search(r"\.pdf['\"]", h) and re.search(r"menu|price", h): probs.append("menu or prices only as a PDF")
    if not re.search(r"tel:|\d{5}\s?\d{6}|\d{4}\s?\d{3}\s?\d{4}", h): probs.append("no clickable phone number")
    if re.search(r"\.swf|<font |<marquee|<center>", h): probs.append("dated, early-2010s style code")
    builder = "wix" if "wix.com" in h else "squarespace" if "squarespace" in h else "wordpress" if "wp-content" in h else ""
    strong = [p for p in probs if p not in ("slow to load",)]
    status = "weak" if len(strong) >= 2 or "not built for phones (no mobile layout)" in strong or any(p.startswith("footer still says") for p in strong) else "ok" if strong else "good"
    return status, probs, builder

def emails_from(html, domain):
    found = [e for e in EMAIL.findall(html) if not BAD_EMAIL.search(e)]
    found += re.findall(r"mailto:([^\"'?>\s]+)", html)
    found = [e.strip(".").lower() for e in found if "@" in e and not BAD_EMAIL.search(e)]
    dom = [e for e in found if domain.split(".")[0] in e.split("@")[1]]
    generic = [e for e in (dom or found) if re.match(r"(info|hello|enquir|contact|office|admin|bookings?|sales|mail|team)", e)]
    return (generic or dom or [None])[0]

def check(co):
    out = dict(co); out.update(website_url=None, website_status="none", site_problems=[], business_email=None, email_source=None, builder="")
    for dom in candidates(co["company_name"]):
        for scheme in ("https://", "http://"):
            try:
                url, html, secs, size = fetch(scheme + dom)
            except Exception:
                continue
            if PARKED.search(html[:30000]) or not matches(co["company_name"], html):
                break
            local_html = html
            if not LOCAL.search(local_html):
                for path in ("/contact", "/contact-us", "/about", "/about-us"):
                    try:
                        local_html = fetch(url.rstrip("/") + path)[1]
                        if LOCAL.search(local_html): break
                    except Exception:
                        pass
                if not LOCAL.search(local_html):
                    break
            status, probs, builder = judge(html, secs, size, url)
            out.update(website_url=url, website_status=status, site_problems=probs, builder=builder)
            em = emails_from(html, dom); src = url
            if not em:
                for path in ("/contact", "/contact-us", "/contact.html", "/contact-us/"):
                    try:
                        u2, h2, _, _ = fetch(url.rstrip("/") + path)
                        em = emails_from(h2, dom)
                        if em: src = u2; break
                    except Exception:
                        pass
            out.update(business_email=em, email_source=src if em else None)
            return out
    return out

if __name__ == "__main__":
    inp, outp = sys.argv[1], sys.argv[2]
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    cos = json.load(open(inp))[:lim]
    with cf.ThreadPoolExecutor(12) as ex:
        res = list(ex.map(check, cos))
    json.dump(res, open(outp, "w"), indent=1)
    from collections import Counter
    print(Counter(r["website_status"] for r in res), "emails:", sum(1 for r in res if r["business_email"]),
          "weak+email:", sum(1 for r in res if r["business_email"] and r["website_status"] == "weak"))
