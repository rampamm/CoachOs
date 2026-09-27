"""CoachOS MVP — FastAPI webhook.

Flow:
    LINE message  ->  /webhook
        if it's a workout log   -> extract -> append to Google Sheet -> confirm
        if it's a question      -> read sheet -> LLM answers -> reply
        if it's an image        -> vision extract -> append -> confirm

Run locally:
    uvicorn app.main:app --reload --port 8000
Then expose port 8000 with ngrok and paste the https URL + /webhook into LINE.
"""
from fastapi import FastAPI, Request, Response
from starlette.concurrency import run_in_threadpool

from . import line_client, extractor, sheets

app = FastAPI(title="CoachOS MVP")

@app.get("/health")
def health():
    return {"status": "ok", "service": "coachos-mvp"}

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    # 1. Security: confirm the request really came from LINE
    if not line_client.verify_signature(body, signature):
        return Response(status_code=400, content="Bad signature")

    payload = await request.json()
    for event in payload.get("events", []):
        await _handle_event(event)

    # LINE only needs a 200 back
    return {"ok": True}


async def _handle_event(event: dict):
    if event.get("type") != "message":
        return

    reply_token = event.get("replyToken")
    user_id = event.get("source", {}).get("userId", "")
    message = event.get("message", {})
    mtype = message.get("type")

    # Look up the client's name once (nice to have in the sheet)
    client_name = await line_client.get_display_name(user_id)

    # ---- IMAGE: photo of a paper sheet / whiteboard ----
    if mtype == "image":
        try:
            img = await line_client.get_image_bytes(message["id"])
            workouts = await run_in_threadpool(extractor.extract_from_image, img)
        except Exception:
            workouts = []
        await _store_and_confirm(reply_token, user_id, client_name, workouts, "image", "(image)")
        return

    # ---- TEXT ----
    if mtype == "text":
        text = message.get("text", "").strip()
        intent = await run_in_threadpool(extractor.classify_intent, text)

        if intent == "question":
            rows = await run_in_threadpool(sheets.read_client_rows, user_id)
            answer = await run_in_threadpool(extractor.answer_question, text, rows)
            await line_client.reply_text(reply_token, answer)
            return

        if intent == "log":
            workouts = await run_in_threadpool(extractor.extract_from_text, text)
            await _store_and_confirm(reply_token, user_id, client_name, workouts, "text", text)
            return

        # other / chit-chat
        await line_client.reply_text(
            reply_token,
            "Hi! Send me your workout like 'bench 80kg 5x5', or ask 'how is my progress this month?'",
        )
        return


async def _store_and_confirm(reply_token, user_id, client_name, workouts, source, raw_text):
    if not workouts:
        await line_client.reply_text(
            reply_token,
            "I couldn't read a workout from that. Try something like 'squat 100kg 4x8'.",
        )
        return
    count = await run_in_threadpool(
        sheets.append_workouts, user_id, client_name, workouts, source, raw_text
    )
    # Build a short confirmation the client can trust
    lines = [
        f"- {w.get('exercise')}: {w.get('weight')}{w.get('unit') or ''} x {w.get('reps')} x {w.get('sets')} sets"
        for w in workouts
    ]
    await line_client.reply_text(reply_token, "Logged " + str(count) + " set(s):\n" + "\n".join(lines))
