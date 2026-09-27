 # CoachOS MVP

"Texting in LINE **is** the product!"

Personal trainers in Bangkok run their whole client relationship through LINE
already — CoachOS gives that chat a memory, so the trainer isn't manually
copying workouts into a spreadsheet by hand. A client texts a workout the way
they'd text their coach, it lands as a structured row in a Google Sheet the
trainer already knows how to read, and when the client asks *"how's my
progress this month?"* the answer comes back grounded in exactly what's in
that sheet — nothing guessed, nothing invented. The client installs nothing
new; the trainer keeps coaching, just without the data entry.

---

## What's in here

```
coachos-mvp/
  app/
    main.py         FastAPI webhook — ties everything together
    line_client.py  Talk to LINE (verify signature, reply, fetch image, get name)
    extractor.py    THE AI LAYER — intent + extraction + grounded answers
    sheets.py       Google Sheets storage (the trainer's "database")
    config.py       Reads settings from .env
  simulate.py       Test the AI locally, no LINE needed  <-- start here
  scripts/          pre-commit hook that blocks secrets from being committed
                    (see scripts/README.md — install it once per clone)
  requirements.txt
  .env.example

  docs/             (local only, gitignored — not in this repo's history)
                    market research, business requirements, and the build
                    plan for turning this MVP into a real product
  prototype/        (local only, gitignored — not in this repo's history)
                    HTML mockups of a trainer-facing dashboard (not wired
                    up to real data yet — the pilot still runs on Sheets)
```



The one idea worth remembering: **the LLM only turns messy text into structured data, or phrases an answer from data we hand it. It never invents numbers.** All facts live in the sheet. That is what keeps it trustworthy.

---

## Step 0 — Install

```bash
cd coachos-mvp
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in the values below
```

## Step 1 — Get an LLM key (needed for everything)

Put your DeepSeek key in `.env` as `DEEPSEEK_API_KEY`.

## Step 2 — Test the brain FIRST (no LINE, no ngrok)

This is the most important step — it tells you if the core idea even works, especially on Thai text.

```bash
python simulate.py --no-sheet
```

Then type real, messy messages:

```
client> bench 80kg 5x5
client> เบนช์ 80 โล 5 เซ็ต เซ็ตละ 5 ครั้ง
client> did legs today, squat 100 for 4 sets of 8, felt weak
```

Look at what it extracts. **If extraction is bad here, fix the prompt in `extractor.py` before building anything else.** This is where you'll spend your real effort.

## Step 3 — Connect Google Sheets

1. In [Google Cloud Console](https://console.cloud.google.com/): create a project → enable **Google Sheets API** → create a **Service Account** → create a **JSON key** → download it.
   **Save it outside this repo folder** (e.g. `~/.config/coachos/service_account.json`), so it can never end up in a commit — point `.env`'s `GOOGLE_SERVICE_ACCOUNT_FILE` at that path. A pre-commit hook (`scripts/pre-commit` — install with `cp scripts/pre-commit .git/hooks/`) also blocks a commit if a file like this ends up staged anyway, but keeping it out of the folder is the real fix.
2. Create a Google Sheet. Copy its ID from the URL (`.../d/THIS_PART/edit`) into `.env` as `GOOGLE_SHEET_ID`.
3. **Share the sheet** with the service account's email (looks like `name@project.iam.gserviceaccount.com`) as **Editor**.
4. Test writing:

```bash
python simulate.py          # now sheet-writing is ON
client> bench 80kg 5x5
```

Open the sheet — you should see a new row. Then:

```
client> how is my progress?
```

## Step 4 — Connect LINE

1. At [LINE Developers](https://developers.line.biz/): create a **Messaging API** channel.
2. Copy the **Channel secret** → `.env` `LINE_CHANNEL_SECRET`.
3. Issue a **Channel access token (long-lived)** → `.env` `LINE_CHANNEL_ACCESS_TOKEN`.
4. Run the server:

```bash
uvicorn app.main:app --reload --port 8000
```

5. In another terminal, expose it (LINE needs a public HTTPS URL):

```bash
ngrok http 8000
```

6. In the LINE console, set the **Webhook URL** to `https://YOUR-NGROK-URL/webhook`, turn **Use webhook** ON, and turn **Auto-reply messages** OFF.
7. Add your channel as a friend (scan its QR) and text it `bench 80kg 5x5`.

---

## The flow, end to end

1. Client texts LINE.
2. LINE POSTs to `/webhook`; we verify the signature.
3. Text → classify intent (`log` / `question` / `other`); image → vision extract.
4. `log` → extract structured sets → append to the Google Sheet → reply a confirmation.
5. `question` → read that client's rows → LLM answers from them → reply.

## Known MVP limitations (on purpose)

- **One sheet, all clients** (a `line_user_id` column separates them). Fine for testing with a handful of clients; later, one sheet per trainer.
- **Synchronous** — the webhook does the LLM + Sheet work inline. Fine for low volume; if LINE times out under load, move the work to a background task and reply with a LINE *push* message instead of the reply token.
- **No auth/dashboard** — the trainer just opens the Google Sheet. That's the point of an MVP: the trainer's UI is a spreadsheet they already understand.

## First things to validate with a real trainer

1. Does extraction survive *their* clients' real messy Thai messages?
2. Do clients actually text workouts unprompted?
3. Does the trainer find the auto-filled sheet + Q&A genuinely useful — enough to pay?

