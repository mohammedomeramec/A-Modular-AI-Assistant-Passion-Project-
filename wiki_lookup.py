"""
MODULE B: Wikipedia lookup.

Fetches a plain-language summary from Wikipedia and hands it to Ollama
so the coach persona can explain it back to you in its own voice,
instead of just dumping a raw encyclopedia paragraph on you.

Before hitting the Wikipedia API, raw conversational input (e.g. "can you
tell me about spiderman?") is first cleaned by Ollama into a bare search
keyword/entity (e.g. "Spider-Man"), since Wikipedia's search is picky about
getting an actual subject rather than a full sentence.
"""

import re

import wikipedia  # pip install wikipedia
from ollama_client import generate_response

# --- AI-based query extraction ---

# Strict, non-conversational system prompt -- same pattern as the win
# cleaner and router: a precise text tool, not a chatty assistant.
_QUERY_EXTRACTION_SYSTEM_PROMPT = (
    "Extract only the primary subject keyword or entity from this prompt "
    "suitable for a Wikipedia search. Return ONLY the keyword phrase, no "
    "punctuation, no conversational text, no quotation marks, nothing else.\n\n"
    "Examples:\n"
    "Input: can you tell me about spiderman?\n"
    "Output: Spider-Man\n\n"
    "Input: spiderman wikipedia\n"
    "Output: Spider-Man\n\n"
    "Input: what is a transistor?\n"
    "Output: Transistor\n\n"
    "Input: tell me about the french revolution\n"
    "Output: French Revolution"
)


def _extract_search_query_ai(user_text: str):
    """
    Ask Ollama to reduce a conversational question down to a bare search
    keyword/entity suitable for the Wikipedia API.

    Returns the cleaned query string, or None if the AI call failed or
    returned something unusable (so the caller can fall back to a simple
    regex-based cleanup).
    """
    raw_reply = generate_response(
        prompt=user_text,
        system_prompt=_QUERY_EXTRACTION_SYSTEM_PROMPT,
        temperature=0.0,  # deterministic: we want the same keyword every time
    )

    if not raw_reply or raw_reply.startswith("\u26a0\ufe0f"):
        return None

    cleaned = raw_reply.strip().strip('"').strip("'").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned if cleaned else None


# --- Regex-based fallback (used only if Ollama is unreachable) ---

_FILLER_PHRASES = [
    "can you tell me about", "tell me about", "can you explain",
    "what is", "what are", "who is", "who was", "explain", "define",
    "wikipedia",
]


def _extract_search_query_fallback(user_text: str) -> str:
    """
    Simple regex-based cleanup, used ONLY if Ollama can't be reached.
    Strips common conversational filler so at least the obvious cases work.
    """
    cleaned = user_text.strip().rstrip("?").strip()
    lowered = cleaned.lower()

    for phrase in _FILLER_PHRASES:
        lowered_stripped = lowered.replace(phrase, "")
        if lowered_stripped != lowered:
            # Rebuild cleaned text with the phrase removed, preserving
            # whatever's left (order-independent, simple substring removal).
            cleaned = re.sub(re.escape(phrase), "", cleaned, flags=re.IGNORECASE)
            lowered = cleaned.lower()

    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,-")
    cleaned = re.sub(r"^(a|an|the)\s+", "", cleaned, flags=re.IGNORECASE)
    return cleaned or user_text


# --- Wikipedia fetch + explanation ---


def _fetch_summary(query: str, sentences: int = 4):
    """
    Fetch a short summary for a query from Wikipedia.
    Handles the two most common failure cases: ambiguous topics
    (e.g. "Mercury" the planet vs the element) and topics that don't exist.

    Returns the summary string, or None if nothing usable was found.
    """
    try:
        return wikipedia.summary(query, sentences=sentences)
    except wikipedia.exceptions.DisambiguationError as e:
        # Multiple pages matched -- just take the first suggested option.
        first_option = e.options[0]
        try:
            return wikipedia.summary(first_option, sentences=sentences)
        except Exception:
            return None
    except wikipedia.exceptions.PageError:
        return None
    except Exception:
        return None


def answer_factual_question(query: str) -> str:
    """
    Clean the user's raw question down to a search keyword, look it up on
    Wikipedia, then ask the local model to explain it in the coach's
    motivational tone.
    """
    search_term = _extract_search_query_ai(query)
    if search_term is None:
        # Ollama unreachable or returned something unusable -- fall back
        # to simple regex cleanup so lookups still work offline.
        search_term = _extract_search_query_fallback(query)

    summary = _fetch_summary(search_term)

    if summary is None:
        return (
            f'I couldn\'t find a clear Wikipedia article for "{search_term}". '
            "Try rephrasing it a bit more specifically -- that's how good "
            "researchers work anyway."
        )

    prompt = (
        f'The user asked: "{query}"\n\n'
        f'Here is factual background from Wikipedia on "{search_term}":\n'
        f'"""\n{summary}\n"""\n\n'
        "Explain this to the user clearly and briefly in your own motivational "
        "coaching voice. Do not just repeat the text verbatim."
    )

    return generate_response(prompt)