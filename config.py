"""
Configuration settings for the Personal Assistant.
Edit the values below to customize the assistant's behavior.
This is the ONLY file most people will need to touch to tweak things.
"""

import os

# --- Ollama settings ---
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"  # Change to whatever model you've pulled, e.g. `ollama pull llama3`

# --- Personality / System Prompt ---
# This is the instruction that shapes HOW the model talks to you.
SYSTEM_PROMPT = (
    "You are a highly motivating, supportive, and disciplined personal assistant. "
    "You speak with energy and confidence, celebrate small wins, and push the user "
    "to keep improving. Keep your responses concise -- 2 to 4 sentences unless "
    "the user clearly needs more detail. Avoid generic filler; be direct and encouraging."
)

# --- File paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WINS_FILE = os.path.join(BASE_DIR, "daily_wins.md")
