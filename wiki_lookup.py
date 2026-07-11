"""
MODULE B: Wikipedia lookup.

Fetches a plain-language summary from Wikipedia and hands it to Ollama
so the coach persona can explain it back to you in its own voice,
instead of just dumping a raw encyclopedia paragraph on you.
"""

import wikipedia  # pip install wikipedia
from ollama_client import generate_response


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
    Look up `query` on Wikipedia, then ask the local model to explain it
    in the coach's motivational tone.
    """
    summary = _fetch_summary(query)

    if summary is None:
        return (
            f'I couldn\'t find a clear Wikipedia article for "{query}". '
            "Try rephrasing it a bit more specifically -- that's how good "
            "researchers work anyway."
        )

    prompt = (
        f'The user asked: "{query}"\n\n'
        f'Here is factual background from Wikipedia:\n"""\n{summary}\n"""\n\n'
        "Explain this to the user clearly and briefly in your own motivational "
        "coaching voice. Do not just repeat the text verbatim."
    )

    return generate_response(prompt)
