"""Local simulator — test the brain WITHOUT LINE or ngrok.

This is the fastest way to check the part that actually makes or breaks the MVP:
does the LLM correctly read messy (Thai/English) workout messages?

Usage:
    python simulate.py                 # interactive chat loop
    python simulate.py --no-sheet      # don't write to Google Sheets, just print

Type a workout ("bench 80kg 5x5" / "เบนช์ 80 โล 5 เซ็ต เซ็ตละ 5")
or a question ("how is my progress this month?") and watch what it does.
Type 'quit' to exit.
"""
import os
import sys

from app import extractor
from app.config import config
from app.config import extractor

WRITE_SHEET = "--no-sheet" not in sys.argv
FAKE_USER = "local-test-user"
FAKE_NAME = "Test Client"

if WRITE_SHEET and not os.path.exists(config.GOOGLE_SERVICE_ACCOUNT_FILE):
    WRITE_SHEET = False
    print(f"[Notice] '{config.GOOGLE_SERVICE_ACCOUNT_FILE}' not found. Auto-disabling Google Sheets sync.\n")

if WRITE_SHEET:
    from app import sheets


def handle(text: str):
    intent = extractor.classify_intent(text)
    print(f"  [intent = {intent}]")

    if intent == "question":
        rows = sheets.read_client_rows(FAKE_USER) if WRITE_SHEET else []
        print("  " + extractor.answer_question(text, rows))
        return

    if intent == "log":
        workouts = extractor.extract_from_text(text)
        print("  extracted:", workouts)
        if WRITE_SHEET and workouts:
            n = sheets.append_workouts(FAKE_USER, FAKE_NAME, workouts, "text", text)
            print(f"  -> wrote {n} row(s) to the sheet")
        return

    print("  (chit-chat — nothing stored)")


if __name__ == "__main__":
    print("CoachOS local simulator. Sheet writing:", "ON" if WRITE_SHEET else "OFF")
    print("Type a message (or 'quit').")
    while True:
        try:
            line = input("\nclient> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if line.lower() in ("quit", "exit"):
            break
        if line:
            handle(line)
