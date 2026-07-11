"""
MODULE A: The Win Logger.

Appends timestamped "wins" to a local Markdown file (daily_wins.md),
formatted like a clean engineering log:  * [Time] Win description

This module is self-contained: it doesn't call Ollama at all, it just
does simple text parsing + file writing. That keeps it fast and reliable.
"""

import re
from datetime import datetime
from dateutil import parser as date_parser  # pip install python-dateutil

from config import WINS_FILE

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


def _clean_description(text: str, matched_time_str: str) -> str:
    """
    Strip the matched time expression and common filler phrases out of the
    sentence, leaving just a clean description of the win.
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
    description = _clean_description(raw_text, matched_time_str)

    time_label = entry_time.strftime("%Y-%m-%d %I:%M %p")
    log_line = f"* [{time_label}] {description}\n"

    file_exists = _file_exists(WINS_FILE)

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
