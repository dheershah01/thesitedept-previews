# Job watch

Hourly scan of Freelancer.com for small, fully digital jobs (spreadsheets, financial models,
data cleaning, Python scripts, CVs, business plans, decks, reports) that Claude can produce
end to end. `scan.py` prints new matches as JSON and records reported job IDs in `seen.json`.

Filters: fixed price, budget ceiling £25–£400, 60 bids or fewer, posted in the last 3 hours,
English, and nothing that needs physical work, calls, design tools, apps, or academic cheating.
