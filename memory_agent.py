# ============================================================
# memory_agent.py - An agent that remembers you across runs!
# ============================================================

import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: No API key found.")
    exit()

MEMORY_FILE = "memory.json"

# ------------------------------------------------------------
# 1. HELPER FUNCTIONS FOR MEMORY FILE
# These handle reading and writing to our JSON file.
# ------------------------------------------------------------

def load_memory() -> dict:
    """Loads memory from memory.json, or returns empty dict if file doesn't exist."""
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_memory_to_file(memory: dict):
    """Saves the memory dictionary back to memory.json."""
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memory, f, indent=4)

# ------------------------------------------------------------
# 2. DEFINING THE TOOL
# We give the agent a tool to update its memory file.
# ------------------------------------------------------------

def save_fact(key: str, value: str) -> str:
    """
    Saves a fact about the user into persistent memory.
    
    Args:
        key: The category of the fact (e.g., 'user_name', 'favourite_colour', 'pet_name').
        value: The detail to remember (e.g., 'Fisher', 'blue', 'Rex').
    """
    try:
        memory = load_memory()
        memory[key] = value
        save_memory_to_file(memory)
        return f"Successfully remembered: {key} = {value}"
    except Exception as e:
        return f"Error saving fact: {str(e)}"

# ------------------------------------------------------------
# 3. SETTING UP THE AGENT WITH PRE-LOADED MEMORY
# ------------------------------------------------------------

client = genai.Client(api_key=api_key)

# Before starting, let's load whatever facts we already have saved!
current_memory = load_memory()

# We construct a system instruction that contains the facts we loaded.
# This is how the AI "remembers" things from previous runs!
facts_text = ""
if current_memory:
    facts_text = "\nHere are facts you already know about the user:\n"
    for k, v in current_memory.items():
        facts_text += f"- {k}: {v}\n"
else:
    facts_text = "\nYou don't know anything about the user yet."

system_instruction = (
    "You are a personal assistant agent with persistent memory. "
    "You can save facts about the user using the 'save_fact' tool. "
    "Use this tool whenever the user tells you a preference, name, or fact about themselves. "
    f"{facts_text}"
)

# Start the chat session with our tool
chat = client.chats.create(
    model="gemini-2.5-flash",
    config={
        "system_instruction": system_instruction,
        "tools": [save_fact]
    }
)

# ------------------------------------------------------------
# 4. RUNNING THE LOOP
# ------------------------------------------------------------
print("=" * 50)
print("Persistent Memory Agent - Type 'quit' to exit")
print("=" * 50)

# If we have preloaded facts, let the user know we remember them
if current_memory:
    print("Agent: Welcome back! I remember some things about you:")
    for k, v in current_memory.items():
        print(f"  * {k}: {v}")
else:
    print("Agent: Hello! I'm ready to chat and remember things about you.")

while True:
    user_input = input("\nYou: ").strip()

    if user_input.lower() == "quit":
        print("Goodbye!")
        break

    if not user_input:
        print("Please type something!")
        continue

    response = chat.send_message(user_input)
    print(f"\nAgent: {response.text}")
