"""
MODULE A: The Win Logger.

Appends timestamped "wins" to a local Markdown file (daily_wins.md),
formatted like a clean engineering log:  * [Time] Win description

Time extraction stays regex-based (fast, deterministic, no need to bother
the AI with something a simple pattern already handles perfectly).

Cleaning the WORDING of the win, however, is handled by Ollama: it reads
your raw sentence and extracts just the core accomplishment in past tense.
This handles far more phrasing variety than a fixed prefix list ever could.
If Ollama is unreachable, a simple regex-based fallback keeps the logger
working offline.
"""

import os
import re
from datetime import datetime
from dateutil import parser as date_parser  # pip install python-dateutil

from config import WINS_FILE
from ollama_client import generate_response

# --- AI-based cleaning ---

# A strict, non-conversational system prompt. This is deliberately NOT the
# coach persona from config.py -- for this task we want a precise text tool,
# not a motivational speaker, so the output formats cleanly in the log file.
_EXTRACTION_SYSTEM_PROMPT = (
    "You are a precise text-extraction tool. You are not a conversational assistant "
    "and you must never behave like one.\n\n"
    "Your ONLY job: read the user's raw sentence about something they did, and output "
    "the core accomplishment as a short phrase in past tense, suitable for a clean "
    "engineering log.\n\n"
    "Rules:\n"
    "- Output ONLY the cleaned phrase. No preamble, no explanation, no quotation marks, "
    "no trailing period, nothing else.\n"
    "- Remove commands and lead-ins such as 'log that', 'log a win', 'note that'.\n"
    "- Remove pronouns such as 'I', 'I just', 'I've'.\n"
    "- Remove filler and conversational tone.\n"
    "- Rewrite in past tense if it isn't already.\n"
    "- Do not include any time, date, or timestamp in the output -- that is handled "
    "separately.\n"
    "- Do not add any information that was not in the original sentence.\n"
    "- Keep it short: ideally under 12 words.\n"
    "- Capitalize the first letter of the output.\n\n"
    "Examples:\n"
    "Input: log a win that I successfully studied electronics for 2 hours\n"
    "Output: Studied electronics for 2 hours\n\n"
    "Input: I just crushed my workout at the gym\n"
    "Output: Crushed workout at the gym"
)


def _clean_description_ai(text: str) -> str:
    """
    Ask Ollama to extract a clean, past-tense description of the win.

    Returns the cleaned string, or None if the AI call failed or returned
    something unusable (so the caller can fall back to the regex cleaner).
    """
    raw_reply = generate_response(
        prompt=text,
        system_prompt=_EXTRACTION_SYSTEM_PROMPT,
        temperature=0.2,  # low temperature: we want consistent, boring, predictable output
    )

    # generate_response() returns a "⚠️ ..." string on connection/timeout errors
    # instead of raising -- treat that as a failure so we can fall back.
    if not raw_reply or raw_reply.startswith("\u26a0\ufe0f"):
        return None

    # Ollama usually follows instructions, but strip stray quotes/whitespace
    # just in case, so a mis-formatted reply doesn't corrupt the log file.
    cleaned = raw_reply.strip().strip('"').strip("'").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    if not cleaned:
        return None

    return cleaned[0].upper() + cleaned[1:]


# --- Regex-based fallback (used only if Ollama is unreachable) ---

# Filler phrases we strip off the front of a sentence so the log reads cleanly.
# Order matters: longer/more specific phrases should come first.
_PREFIXES_TO_STRIP = [
    "log that i", "log that", "log a win that i", "log a win",
    "log win", "win:", "note that i", "note that",
    "i just", "i've", "i have", "i",
]

# Matches time expressions like "2 PM", "2:30pm", "14:30", "9 am"
_TIME_PATTERN = re.compile(
    r"\b(\d{1,2}(:\d{2})?\s*(am|pm|AM|PM))\b|\b([01]?\d|2[0-3]):[0-5]\d\b"
)


def _extract_time(matched_time_str: str) -> datetime:
    """
    Convert a matched time string (e.g. "2 PM") into a full datetime,
    using today's date. Falls back to "now" if parsing fails.
    """
    if not matched_time_str:
        return datetime.now()

    # Use TODAY'S DATE but MIDNIGHT as the default, so that any time
    # component NOT present in the matched string (e.g. minutes, when the
    # user only said "6 AM") comes out as :00 instead of leaking in the
    # current minute from datetime.now().
    default_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        return date_parser.parse(matched_time_str, default=default_dt)
    except (ValueError, OverflowError):
        return datetime.now()


def _clean_description_fallback(text: str, matched_time_str: str) -> str:
    """
    Regex-only cleanup, used ONLY if Ollama can't be reached. Strips the
    matched time expression and common filler phrases from the sentence.
    """
    cleaned = text.strip()

    if matched_time_str:
        cleaned = cleaned.replace(matched_time_str, "")

    lowered = cleaned.lower()
    for prefix in _PREFIXES_TO_STRIP:
        if lowered.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            lowered = cleaned.lower()

    # Clean up leftover connector words ("at", trailing commas) and whitespace
    cleaned = re.sub(r"\bat\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,-")

    return cleaned.capitalize() if cleaned else "Unspecified win"


def log_win(raw_text: str) -> str:
    """
    Parse a sentence describing a win, extract an optional time, and append
    a clean, timestamped entry to daily_wins.md.

    Args:
        raw_text: The user's original sentence, e.g. "Log that I studied at 2 PM".

    Returns:
        A short confirmation message to show the user.
    """
    match = _TIME_PATTERN.search(raw_text)
    matched_time_str = match.group(0) if match else None
    entry_time = _extract_time(matched_time_str)

    # Strip the time expression out before handing the text to the AI, so it
    # doesn't have to worry about (or accidentally repeat) the timestamp.
    text_without_time = raw_text.replace(matched_time_str, "") if matched_time_str else raw_text

    description = _clean_description_ai(text_without_time)
    if description is None:
        # Ollama unreachable or returned something unusable -- fall back
        # to the regex cleaner so logging a win still works offline.
        description = _clean_description_fallback(raw_text, matched_time_str)

    time_label = entry_time.strftime("%Y-%m-%d %I:%M %p")
    log_line = f"* [{time_label}] {description}\n"

    file_exists = _file_exists(WINS_FILE)

    # Make sure the target folder exists (e.g. in case Documents is
    # redirected somewhere unusual) so the file write doesn't crash.
    os.makedirs(os.path.dirname(WINS_FILE), exist_ok=True)

    with open(WINS_FILE, "a", encoding="utf-8") as f:
        if not file_exists:
            f.write("# Daily Wins Log\n\n")
        f.write(log_line)

    return f'Logged: "{description}" at {time_label}'


def _file_exists(path: str) -> bool:
    """Small helper to avoid importing os.path just for one check."""
    try:
        with open(path, "r", encoding="utf-8"):
            return True
    except FileNotFoundError:
        return False