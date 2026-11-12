#!/usr/bin/env python3
"""Pull active limited companies by trade (SIC) and area from Companies House."""
import json, os, re, subprocess, time, urllib.parse, sys
KEY = os.environ.get("CH_KEY") or open(os.path.join(os.path.dirname(__file__), "..", ".ch_key")).read().strip()
SIC = {"96020": "barber_salon", "56101": "food", "56102": "food", "56103": "food",
       "43210": "trades", "43220": "trades", "81210": "trades", "81229": "trades", "81222": "trades",
       "93130": "fitness", "85510": "fitness"}
AREAS = ["Coventry", "Warwick", "Leamington Spa", "Kenilworth", "Rugby", "Nuneaton", "Solihull", "Birmingham"]
OK_PC = re.compile(r"^(CV\d{1,2}|B\d{1,2})\s", re.I)

def get(path):
    out = subprocess.run(["curl", "-sS", "-m", "30", "-u", KEY + ":", "https://api.company-information.service.gov.uk" + path], capture_output=True, text=True).stdout
    try: return json.loads(out)
    except Exception: return {}

def main():
    seen = {}
    for sic, niche in SIC.items():
        for area in AREAS:
            start = 0
            while start < 300:
                q = urllib.parse.urlencode({"company_status": "active", "company_type": "ltd", "sic_codes": sic, "location": area, "size": 100, "start_index": start})
                d = get("/advanced-search/companies?" + q); items = d.get("items", [])
                for it in items:
                    pc = (it.get("registered_office_address") or {}).get("postal_code") or ""
                    if not OK_PC.match(pc + " "): continue
                    n = it["company_number"]
                    if n in seen: continue
                    seen[n] = {"company_number": n, "company_name": it["company_name"], "niche": niche, "sic": sic,
                               "postcode": pc, "address": ", ".join(v for v in (it.get("registered_office_address") or {}).values() if isinstance(v, str)),
                               "incorporated": it.get("date_of_creation")}
                if len(items) < 100: break
                start += 100; time.sleep(0.6)
            time.sleep(0.6)
        print(sic, niche, len(seen), file=sys.stderr)
    json.dump(list(seen.values()), open(os.path.join(os.path.dirname(__file__), "..", "ch_companies.json"), "w"), indent=1)
    print(len(seen))
main()
