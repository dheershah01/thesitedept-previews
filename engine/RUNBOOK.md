# The Site Dept. outreach runbook

Daily goal: 10 to 15 Gmail **drafts** to UK limited companies with weak websites, each linking to a personalised preview. Dheer reviews and clicks send. Claude never sends.

## Setup in a fresh session
1. Clone this repo. Copy `engine/` into a scratch working folder.
2. Ask Dheer for the Companies House API key. Put it in `CH_KEY` or `outreach/.ch_key`. **Never commit it.**
3. Check the network: `curl -s -o /dev/null -w '%{http_code}' https://example.com/` should give 200. The environment needs **Full** network access.

## Pipeline
1. **Source.** Run `ch_source.py`. It pulls active Ltd companies by SIC code across Coventry, Warwick, Leamington, Kenilworth, Rugby, Nuneaton, Solihull and Birmingham.
   - Exclude holding, property, investment and similar names.
   - Exclude anything incorporated in the last 18 months.
   - Shuffle the rest.
2. **Skip.** Drop everything in `contacted.json` (both `contacted` and `suppressed`).
3. **Check sites.** Run `site_check.py`. It:
   - guesses the domain and confirms a local match
   - keeps only emails on the same domain
   - flags weak signals
4. **Look properly.** For every candidate, open the real site, on a phone-sized screen too, and find **one specific, verifiable problem**. Good hooks so far:
   - Wix template text left live (sample San Francisco address, placeholder testimonials)
   - "Coming soon" pages and broken links
   - headline cut off on mobile
   - typo in the browser tab title
   - footer copyright years old

   No real problem means no email.
5. **Research the business** from its own site and its Google listing: real services, phone, areas covered, badges (only ones they display), reviews, logo URL.
6. **Build.** Use `build2.py` with a lead dict (see `sample_leads.json`).
   - Themes: `trades`, `barber`, `salon`, `restaurant`, `cafe`, `fitness`.
   - Stock photo keys: electrician, heating, plumber, car, trades, barber, salon, restaurant, cafe, fitness.
   - Use only facts the business has published. Never invent "24/7", accreditations or areas.
7. **Publish.** Write the output to `public/<slug>/index.html`, then commit and push. Cloudflare Workers deploys to `https://thesitedept-previews.dheershah544.workers.dev/<slug>/`. Check that each link returns 200.
8. **Draft.** Use `emails2.first_email()`.
   - Subject: specific and 2 to 6 words.
   - Hook: the verified problem, quoted.
   - One link, about 110 words, with the "reply no" opt-out.
   - Create drafts with Gmail `create_draft` only.
9. **Record.** Add each company to `contacted.json`. Follow up once after 4 days with `emails2.follow_up()` as a reply draft.

## Rules
- **PECR:** only email limited companies (corporate subscribers). Never email sole traders or partnerships.
- Identify the sender every time and include an easy opt-out. Honour every "no" by adding the company to `suppressed`.
- Gmail: ramp up slowly, around 5 sends a day at first. Best send window is Tuesday to Thursday, 8am to 12pm.
- Previews carry a banner ("Not the live site"), noindex, and a note that the photos are placeholders.
