"""The AI layer.

Three jobs, all backed by DeepSeek:
  1. classify_intent(text)      -> "log" | "question" | "other"
  2. extract_from_text(text)    -> list of structured workout dicts
  3. extract_from_image(bytes)  -> list of structured workout dicts (vision)
  4. answer_question(q, rows)   -> a grounded natural-language answer

Design note (this is the important architectural idea):
The LLM ONLY turns messy language into structured data, or phrases an answer
from data we hand it. It never invents numbers. All facts live in the sheet.
That separation is what keeps the assistant trustworthy.
"""
import base64
import json
import httpx

from .config import config


def _ask(system: str, user_content, max_tokens: int = 1024) -> str:
    """Small wrapper around DeepSeek Chat API call."""
    if not config.DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY is not configured in .env file.")

    messages = [{"role": "system", "content": system}]
    if isinstance(user_content, str):
        messages.append({"role": "user", "content": user_content})
    elif isinstance(user_content, list):
        text_parts = [b.get("text", "") for b in user_content if isinstance(b, dict) and "text" in b]
        messages.append({"role": "user", "content": "\n".join(text_parts)})

    headers = {
        "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.DEEPSEEK_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
    }

    url = f"{config.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    with httpx.Client(timeout=30.0) as client:
        res = client.post(url, headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()
        msg_obj = data["choices"][0]["message"]
        content = msg_obj.get("content") or ""
        if not content and msg_obj.get("reasoning_content"):
            content = msg_obj.get("reasoning_content") or ""
        return content.strip()


def _parse_json(raw: str):
    """Robustly parse JSON arrays or objects from text output."""
    import re
    raw = raw.strip()
    # Try direct parse
    try:
        return json.loads(raw)
    except Exception:
        pass
    
    # Try stripping markdown codeblocks ```json ... ```
    if "```" in raw:
        for block in raw.split("```"):
            block = block.strip()
            if block.startswith("json"):
                block = block[4:].strip()
            if block.startswith("[") or block.startswith("{"):
                try:
                    return json.loads(block)
                except Exception:
                    pass

    # Regex search for JSON array [...]
    match = re.search(r"\[\s*\{.*\}\s*\]", raw, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    match_empty = re.search(r"\[\s*\]", raw)
    if match_empty:
        return []

    raise ValueError(f"Could not parse JSON: {raw[:100]}")


# ---------------------------------------------------------------------------
# 1. Intent
# ---------------------------------------------------------------------------
_INTENT_SYSTEM = """You classify a fitness client's chat message into exactly one label.
Return ONLY one word, no punctuation:
- "log"      : they are reporting a workout they did (e.g. "bench 80kg 5x5", "did legs today squat 100 4x8")
- "question" : they are asking about their progress/history (e.g. "how is my progress this month?", "what did I bench last week?")
- "other"    : greetings, chit-chat, anything else
The message may be in Thai or English."""


def classify_intent(text: str) -> str:
    label = _ask(_INTENT_SYSTEM, text, max_tokens=512).lower()
    for candidate in ("log", "question", "other"):
        if candidate in label:
            return candidate
    return "other"


# ---------------------------------------------------------------------------
# 2 & 3. Extraction (text and image)
# ---------------------------------------------------------------------------
_EXTRACT_SYSTEM = """You extract structured strength-training workout data from human chat messages (in Thai or English).

Return ONLY a valid JSON array of objects. Each object represents workout set(s):
[
  {"exercise": "Single-Arm Lat Pulldown", "weight": 25, "unit": "kg", "sets": 1, "reps": 8},
  {"exercise": "Single-Arm Lat Pulldown", "weight": 28, "unit": "kg", "sets": 1, "reps": 6}
]

RULES:
1. Normalize exercise names to clean English (e.g., "เบนช์" -> "Bench Press", "One hand lat pull down" -> "Single-Arm Lat Pulldown", "leg press" -> "Leg Press", "squat" -> "Squat").
2. If a single exercise has multiple weight/rep combinations across sets (e.g. "2 sets: 25kg 8 reps then 28kg 6 reps"), create a separate object for each set.
3. If reps or sets apply to all listed weights (e.g. "30kg then 35kg 10 reps each"), apply 10 reps to each entry.
4. Extract numeric values for `weight`, `sets`, `reps`. Default `unit` to "kg" unless "lbs" or "lb" is explicitly stated.
5. If a field is genuinely missing or unspecified, use null. NEVER invent numbers.
6. Return ONLY the raw JSON array. Do not include markdown codeblocks, reasoning, or extra text.

EXAMPLES:
Input: "bench 80kg 5x5"
Output: [{"exercise": "Bench Press", "weight": 80, "unit": "kg", "sets": 5, "reps": 5}]

Input: "leg press 2 sets 30kg then 35kg 10 reps then 8 reps"
Output: [{"exercise": "Leg Press", "weight": 30, "unit": "kg", "sets": 1, "reps": 10}, {"exercise": "Leg Press", "weight": 35, "unit": "kg", "sets": 1, "reps": 8}]

Input: "One hand lat pull down for 2 set set 25kg 8 reps and 28 kg 6 reps"
Output: [{"exercise": "Single-Arm Lat Pulldown", "weight": 25, "unit": "kg", "sets": 1, "reps": 8}, {"exercise": "Single-Arm Lat Pulldown", "weight": 28, "unit": "kg", "sets": 1, "reps": 6}]
"""


def extract_from_text(text: str) -> list[dict]:
    raw = _ask(_EXTRACT_SYSTEM, text, max_tokens=1024)
    try:
        data = _parse_json(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def extract_from_image(image_bytes: bytes, media_type: str = "image/jpeg") -> list[dict]:
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
        {"type": "text", "text": "Extract every workout set you can read from this image."},
    ]
    raw = _ask(_EXTRACT_SYSTEM, content, max_tokens=1500)
    try:
        data = _parse_json(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# 4. Answering progress questions (grounded in the sheet rows)
# ---------------------------------------------------------------------------
_ANSWER_SYSTEM = """You are a helpful assistant for a personal-training client.
You will be given the client's workout history as JSON rows, plus their question.
Answer ONLY using the data provided. If the data does not contain the answer, say so plainly.
Do not invent numbers. Keep it short and friendly. Reply in the same language as the question (Thai or English)."""


def answer_question(question: str, rows: list[dict]) -> str:
    if not rows:
        return "I don't have any workouts logged for you yet. Send me something like 'bench 80kg 5x5' first!"
    prompt = (
        f"Client's workout history (JSON):\n{json.dumps(rows, ensure_ascii=False)}\n\n"
        f"Question: {question}"
    )
    return _ask(_ANSWER_SYSTEM, prompt, max_tokens=600)
