# Local AI Coach — Offline Personal Assistant

A fully private, offline-first assistant powered by your local Ollama install.
No cloud calls except to Wikipedia's public API for factual lookups (everything
else, including all AI generation, stays on your machine).

## 1. Project structure

```
personal_assistant/
├── config.py          # Settings: model name, personality prompt, file paths
├── ollama_client.py   # The ONLY file that talks to Ollama
├── win_logger.py       # Module A: logs your daily wins to daily_wins.md
├── wiki_lookup.py      # Module B: Wikipedia lookup + AI explanation
├── router.py           # Decides: win / wikipedia / plain chat
├── main.py             # Entry point — run this
└── daily_wins.md        # Created automatically the first time you log a win
```

Each module only knows about what it needs. `main.py` just wires them together,
so you can add a "Module C" later (calendar, weather, etc.) without touching
the existing modules.

## 2. Install dependencies

You need Python 3.8+ and these three lightweight libraries:

```bash
pip install requests wikipedia python-dateutil
```

- `requests` — talks to Ollama's local API
- `wikipedia` — thin wrapper around Wikipedia's public API
- `python-dateutil` — parses time expressions like "2 PM" or "14:30"

No LangChain, no vector databases, no heavy ML libraries — keeps RAM usage low.

## 3. Set up Ollama

Make sure Ollama is running and you've pulled a model:

```bash
ollama serve            # starts the local server (if not already running)
ollama pull llama3      # or any model you prefer, e.g. mistral, phi3, gemma2
```

If you use a different model name, update `MODEL_NAME` in `config.py`.

## 4. Run it

```bash
python main.py
```

Then just talk to it:

```
You: Log that I woke up at 6 AM
Coach: Logged: "Woke up" at 2026-07-11 06:00 AM

You: Log that I studied at 2 PM
Coach: Logged: "Studied" at 2026-07-11 02:00 PM

You: What is a transistor?
Coach: [Wikipedia summary explained in coach voice]

You: I'm feeling unmotivated today
Coach: [normal encouraging chat reply]
```

Type `quit` or `exit` to leave.

## 5. How the routing works

`router.py` uses simple keyword matching — no extra AI call needed just to
figure out what you meant:

- Contains phrases like *"log that"*, *"I finished"*, *"I woke up"* → **Win Logger**
- Contains phrases like *"what is"*, *"who was"*, *"explain"*, or ends in `?` → **Wikipedia**
- Anything else → plain chat with the coach persona

**Known limitation:** because "ends in `?`" triggers the Wikipedia path, a casual
question like *"How are you today?"* will incorrectly get routed to Wikipedia
instead of chat. This is the trade-off of a fast, free, keyword-only router.
If it bothers you, an easy upgrade is to replace `classify_input()` with a tiny
Ollama call that returns one word (`win`/`wiki`/`chat`) — nothing else in the
codebase needs to change, since every module only cares about that one string.

## 6. Extending it (adding your own "Module C")

1. Create a new file, e.g. `weather_module.py`, with one clear function like
   `get_weather(query: str) -> str`.
2. Add a trigger list for it in `router.py` and a new `elif` branch.
3. Import and call it from `main.py`'s `handle_input()`.

That's the whole pattern — every module in this project follows it.

## 7. Notes on the Win Logger's time parsing

- If you mention a time ("at 2 PM", "at 14:30"), it uses that time, today's date.
- If you don't mention a time, it uses the current system time.
- Entries are appended to `daily_wins.md` in this format:

  ```
  * [2026-07-11 06:00 AM] Woke up
  * [2026-07-11 02:00 PM] Studied
  ```
