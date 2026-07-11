"""
THE INTELLIGENT ROUTER.

Decides whether the user's input is:
  - a daily win to log             -> "win"
  - a factual question to look up  -> "wikipedia"
  - a normal chat message          -> "chat"

This now uses Ollama itself to classify the message, with a strict system
prompt that forces a single-word answer. This generalizes far better than
any fixed keyword list -- it understands phrasing like "log it" at the end
of a sentence, or implied wins that don't contain the word "log" at all.

If Ollama is unreachable, this falls back to simple keyword matching so the
app still works offline (same fallback pattern used in win_logger.py).
"""

import re

from ollama_client import generate_response

# --- AI-based classification (primary path) ---

# A strict, non-conversational system prompt. Like the win-cleaning prompt,
# this is deliberately NOT the coach persona -- we want a precise
# classification tool, not a chatty reply.
_CLASSIFICATION_SYSTEM_PROMPT = (
    "You are a precise text-classification tool. You are not a conversational "
    "assistant and you must never behave like one.\n\n"
    "Your ONLY job: read the user's message and classify it into EXACTLY ONE "
    "of these three categories:\n\n"
    "WIN - The user is reporting something they did, accomplished, or wants "
    "logged as a daily win. This includes messages that mention the word "
    "'log' in any position (start, middle, or end), as well as messages "
    "describing an accomplishment even without the word 'log' "
    "(e.g. 'I finished my workout', 'just studied for 2 hours').\n\n"
    "WIKIPEDIA - The user is asking a factual question about a topic, person, "
    "place, thing, or concept -- something you'd look up in an encyclopedia.\n\n"
    "CHAT - Anything else: greetings, feelings, opinions, casual conversation, "
    "requests for motivation or advice, or questions about the user themselves "
    "or the assistant (e.g. 'how are you', 'I'm feeling unmotivated').\n\n"
    "Rules:\n"
    "- Output ONLY one word: WIN, WIKIPEDIA, or CHAT.\n"
    "- No punctuation, no explanation, no other text whatsoever.\n\n"
    "Examples:\n"
    "Input: i ate lunch pretty fast. log it\n"
    "Output: WIN\n\n"
    "Input: I just crushed my workout at the gym\n"
    "Output: WIN\n\n"
    "Input: What is a transistor?\n"
    "Output: WIKIPEDIA\n\n"
    "Input: Tell me about the French Revolution\n"
    "Output: WIKIPEDIA\n\n"
    "Input: How are you today?\n"
    "Output: CHAT\n\n"
    "Input: I'm feeling unmotivated\n"
    "Output: CHAT"
)

_VALID_LABELS = {"WIN": "win", "WIKIPEDIA": "wikipedia", "CHAT": "chat"}


def _classify_with_ai(user_text: str):
    """
    Ask Ollama to classify the message.

    Returns "win" / "wikipedia" / "chat", or None if the AI call failed or
    returned something that isn't a recognizable label (so the caller can
    fall back to keyword matching).
    """
    raw_reply = generate_response(
        prompt=user_text,
        system_prompt=_CLASSIFICATION_SYSTEM_PROMPT,
        temperature=0.0,  # classification should be as deterministic as possible
    )

    # generate_response() returns a "⚠️ ..." string on connection/timeout
    # errors instead of raising -- treat that as a failure so we can fall back.
    if not raw_reply or raw_reply.startswith("\u26a0\ufe0f"):
        return None

    # Be forgiving about formatting: take the first word, strip punctuation,
    # uppercase it, in case the model adds a stray period or extra text.
    first_word = raw_reply.strip().split()[0] if raw_reply.strip() else ""
    label = re.sub(r"[^A-Za-z]", "", first_word).upper()

    return _VALID_LABELS.get(label)  # None if not a recognized label


# --- Keyword-based fallback (used only if Ollama is unreachable) ---

_WIN_TRIGGERS = [
    "log that", "log a win", "log win", "win:", "i just did",
    "i woke up", "i worked out", "i studied", "i finished",
    "i completed", "i achieved", "note that i", "i did it",
]

# Matches the standalone WORD "log" anywhere in the sentence -- e.g. "log it",
# "log this" -- without matching words that merely CONTAIN "log", like
# "catalog", "blog", or "login".
_LOG_WORD_PATTERN = re.compile(r"\blog\b")

_QUESTION_TRIGGERS = [
    "what is", "what are", "who is", "who was", "where is",
    "when did", "when was", "explain", "tell me about",
    "how does", "how do", "why does", "why is", "define",
]


def _classify_with_keywords(user_text: str) -> str:
    """
    Simple keyword-based classification, used ONLY if Ollama can't be
    reached. Same logic as the original offline-only router.
    """
    text = user_text.lower().strip()

    if any(trigger in text for trigger in _WIN_TRIGGERS) or _LOG_WORD_PATTERN.search(text):
        return "win"

    if any(trigger in text for trigger in _QUESTION_TRIGGERS) or text.endswith("?"):
        return "wikipedia"

    return "chat"


def classify_input(user_text: str) -> str:
    """
    Classify a raw sentence from the user.

    Tries the AI classifier first; falls back to keyword matching if Ollama
    is unreachable or returns something unusable.

    Returns one of: "win", "wikipedia", "chat"
    """
    label = _classify_with_ai(user_text)
    if label is not None:
        return label

    return _classify_with_keywords(user_text)