"""
Handles all communication with the local Ollama instance.
Kept deliberately lightweight: just the `requests` library, no frameworks.
Every other module that needs the AI's "brain" imports generate_response()
from here -- this is the single point of contact with Ollama.
"""

import requests
from config import OLLAMA_URL, MODEL_NAME, SYSTEM_PROMPT


def generate_response(prompt: str, system_prompt: str = SYSTEM_PROMPT, temperature: float = 0.7) -> str:
    """
    Send a prompt to the local Ollama model and return its text response.

    Args:
        prompt: The user-facing question / instruction for the model.
        system_prompt: The "personality" instructions. Defaults to the coach persona.
        temperature: Controls randomness. Lower (e.g. 0.2) = more consistent/predictable,
            good for structured extraction tasks. Higher (e.g. 0.7-1.0) = more varied,
            good for natural conversation. Defaults to 0.7 for normal chat.

    Returns:
        The model's reply as a plain string. Returns a friendly error message
        (instead of raising an exception) if Ollama is unreachable, so the
        rest of the assistant keeps working even if the model is offline.
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,  # simplest option for a beginner script: wait for the full reply
        "options": {
            "temperature": temperature,
        },
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()

    except requests.exceptions.ConnectionError:
        return (
            "\u26a0\ufe0f Could not reach Ollama. Is it running? "
            "Try `ollama serve` in a terminal, then try again."
        )
    except requests.exceptions.Timeout:
        return "\u26a0\ufe0f Ollama took too long to respond. Try again or use a smaller/faster model."
    except Exception as e:
        return f"\u26a0\ufe0f Unexpected error talking to Ollama: {e}"