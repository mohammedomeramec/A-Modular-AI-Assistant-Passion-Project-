"""
THE INTELLIGENT ROUTER.

Decides whether the user's input is:
  - a daily win to log             -> "win"
  - a factual question to look up  -> "wikipedia"
  - a normal chat message          -> "chat"

Uses simple keyword matching. This is intentional: it's instant, free,
and doesn't burn a whole extra LLM call just to classify one sentence.
(If you later want smarter routing, you could swap this out for a tiny
Ollama call that returns one word -- the rest of the app wouldn't need
to change, since main.py only cares about the string this returns.)
"""

# Phrases that strongly suggest the user is reporting a win.
_WIN_TRIGGERS = [
    "log that", "log a win", "log win", "win:", "i just did",
    "i woke up", "i worked out", "i studied", "i finished",
    "i completed", "i achieved", "note that i", "i did it",
]

# Phrases/words that strongly suggest a factual question.
_QUESTION_TRIGGERS = [
    "what is", "what are", "who is", "who was", "where is",
    "when did", "when was", "explain", "tell me about",
    "how does", "how do", "why does", "why is", "define",
]


def classify_input(user_text: str) -> str:
    """
    Classify a raw sentence from the user.

    Returns one of: "win", "wikipedia", "chat"
    """
    text = user_text.lower().strip()

    if any(trigger in text for trigger in _WIN_TRIGGERS):
        return "win"

    if any(trigger in text for trigger in _QUESTION_TRIGGERS) or text.endswith("?"):
        return "wikipedia"

    return "chat"
