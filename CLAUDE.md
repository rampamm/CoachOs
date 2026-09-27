## Project Overview

This project is a CRM system to help trainers work more effectively, not replace them. In the current prototype, a client texts their workout to a LINE chat in unstructured text — e.g. "I did 2 sets of lat pull down, 40 kg 10 clean reps, 45 kg 8 reps". Two services handle it: one parses the unstructured message and stores structured data in Google Sheets; the other answers client questions from that stored data, e.g. "How is my progress this month?"


## User Preferences

- When proposing anything, give brief reasoning: why this way, what the alternatives were, and why the feature is needed.

- Before implementing a non-trivial feature (AI prompts, LINE/Sheets integration, data model), research current best practices — use a web-search subagent to answer.

## Module Responsibilites

- app/main.py      webhook wiring
- app/extractor.py AI layer — intent classify, text/vision extract, grounded answers
- app/sheets.py    Google Sheets read/write
- app/line_client.py  signature verify, reply, image fetch, profile name
- app/config.py    env loading

## Tech Stack

- Stack: FastAPI + uvicorn, httpx, gspread + google-auth, python-dotenv. No DB.

- Run locally: `python simulate.py --no-sheet` (AI only) or `python simulate.py` (with Sheets).

- Run server: `uvicorn app.main:app --reload --port 8000`, webhook at POST /webhook.

## Rules

- Secrets in .env and service_account.json — never commit; both are gitignored.

- After code changes affecting AI behavior, run `python simulate.py --no-sheet` to sanity-check.

