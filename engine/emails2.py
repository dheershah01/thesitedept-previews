"""Cold email v2: short, personal, one specific verified problem, one link, one soft ask.

Rules baked in (from cold-email research + Really Good Emails' "do one thing" principle):
- plain text, no images or tracking, one link only
- under ~110 words in the body
- the hook must be something we actually saw on their site (quoted where possible)
- PECR: say who we are and give an easy opt-out every time
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "config.json")))

def first_email(lead, url):
    who = CFG["sender_name"]
    hi = f"Hi {lead['owner_first_name']}," if lead.get("owner_first_name") else "Hi there,"
    proof = lead.get("proof") or "your services"
    body = f"""{hi}

I'm {who}, a student at Warwick who builds websites for local businesses.

{lead['hook']}

So I put together a free preview of a new homepage for {lead['short']}, with {proof}:
{url}

If you like it, I can have it live on your own domain within a week, from {CFG['from_price']} with no monthly fees. Worth a look?

{who}
The Site Dept.

P.S. Not interested? Just reply "no" and I won't email again."""
    return {"to": lead["email"], "subject": lead["subject"], "body": body}

def follow_up(lead, url):
    who = CFG["sender_name"]
    hi = f"Hi {lead['owner_first_name']}," if lead.get("owner_first_name") else "Hi there,"
    body = f"""{hi}

Just bumping this in case it got buried. The preview for {lead['short']} is still here:
{url}

Happy to change anything on it, or I'll leave you be if it's not for you.

{who}
The Site Dept."""
    return {"to": lead["email"], "subject": "Re: " + lead["subject"], "body": body}
