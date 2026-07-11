"""
PERSONAL ASSISTANT -- Main Entry Point

Run this file to start chatting with your offline, local coach:

    python main.py

It routes every message you type to the right module:
  - Daily wins        -> win_logger.py   (Module A)
  - Factual questions  -> wiki_lookup.py  (Module B)
  - Everything else    -> direct chat with Ollama

See README.md for setup instructions.
"""

from router import classify_input
from win_logger import log_win
from wiki_lookup import answer_factual_question
from ollama_client import generate_response


def handle_input(user_text: str) -> str:
    """
    Route a single piece of user input to the correct module and
    return the assistant's reply as a string.

    This is the "traffic controller" -- it doesn't do any work itself,
    it just decides which module should handle the request.
    """
    intent = classify_input(user_text)

    if intent == "win":
        return log_win(user_text)

    if intent == "wikipedia":
        return answer_factual_question(user_text)

    # Default: plain conversation with the coach persona
    return generate_response(user_text)


def main():
    print("=" * 55)
    print(" YOUR LOCAL AI COACH  (fully offline, powered by Ollama)")
    print(" Type 'quit' or 'exit' to stop.")
    print("=" * 55)

    while True:
        user_text = input("\nYou: ").strip()

        if not user_text:
            continue
        if user_text.lower() in ("quit", "exit"):
            print("\nCoach: Keep pushing. See you next session. 💪")
            break

        reply = handle_input(user_text)
        print(f"\nCoach: {reply}")


if __name__ == "__main__":
    main()
