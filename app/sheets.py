"""Google Sheets storage layer.

This is the trainer's "database" for the MVP: a plain spreadsheet they can open
in their browser and watch fill up as clients text their workouts.

One row per exercise. Columns:
    timestamp | line_user_id | client_name | exercise | weight | unit | sets | reps | source | raw_text
"""
from datetime import datetime, timezone, timedelta
import gspread
from google.oauth2.service_account import Credentials

from .config import config

# Bangkok time so the trainer sees local timestamps
BKK_TZ = timezone(timedelta(hours=7))

HEADER = [
    "timestamp", "line_user_id", "client_name", "exercise",
    "weight", "unit", "sets", "reps", "source", "raw_text",
]

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _worksheet():
    """Open (and if needed, initialise) the target worksheet."""
    creds = Credentials.from_service_account_file(
        config.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=_SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
    try:
        ws = sheet.worksheet(config.GOOGLE_WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=config.GOOGLE_WORKSHEET_NAME, rows=1000, cols=len(HEADER))

    # Make sure the header row exists
    first_row = ws.row_values(1)
    if first_row != HEADER:
        ws.update([HEADER], "A1")
    return ws


def append_workouts(line_user_id: str, client_name: str, workouts: list[dict], source: str, raw_text: str):
    """Append one row per exercise. `workouts` is the list returned by the extractor."""
    ws = _worksheet()
    ts = datetime.now(BKK_TZ).strftime("%Y-%m-%d %H:%M")
    display_name = client_name if client_name else line_user_id
    rows = []
    for w in workouts:
        rows.append([
            ts,
            line_user_id,
            display_name,
            w.get("exercise", ""),
            w.get("weight", ""),
            w.get("unit", ""),
            w.get("sets", ""),
            w.get("reps", ""),
            source,
            raw_text,
        ])
    if rows:
        ws.append_rows(rows, value_input_option="USER_ENTERED")
    return len(rows)


def read_client_rows(line_user_id: str) -> list[dict]:
    """Return all stored rows for one client (used to answer progress questions)."""
    ws = _worksheet()
    records = ws.get_all_records()  # list of dicts keyed by header
    return [r for r in records if str(r.get("line_user_id")) == str(line_user_id)]
