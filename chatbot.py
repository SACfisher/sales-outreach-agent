# ============================================================
# chatbot.py - Our very first AI chatbot!
# ============================================================

# --- IMPORTS ---
# Think of imports like "turning on" tools we need.

import os                        # Lets us read environment variables (like our API key)
from dotenv import load_dotenv   # Reads our .env file and loads the variables inside it
from google import genai         # This is Google's NEW official Gemini library (google-genai)

# --- LOAD THE API KEY ---
# This reads the .env file and makes GEMINI_API_KEY available via os.getenv()
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Safety check: if there's no API key, stop and tell the user
if not api_key:
    print("ERROR: No API key found. Please add your key to the .env file.")
    exit()

# --- CREATE THE CLIENT ---
# In the new library, we create a "client" object using our API key.
# The client is our connection to Google's AI service.
client = genai.Client(api_key=api_key)

# --- START A CHAT SESSION ---
# This creates a chat session that remembers the conversation history.
# "gemini-2.0-flash" is a fast, free-tier model - perfect for learning.
# We also pass a system instruction to give the AI its role/personality.
chat = client.chats.create(
    model="gemini-2.5-flash",
    config={
        "system_instruction": "You are a friendly and helpful assistant. Keep your answers clear and concise."
    }
)

# --- THE MAIN CHAT LOOP ---
print("=" * 50)
print("AI Chatbot - Type 'quit' to exit")
print("=" * 50)

# A "while loop" keeps running forever until we tell it to stop with "break"
while True:
    # Get the user's message from the terminal
    user_input = input("\nYou: ").strip()

    # If the user types 'quit', break out of the loop and end the program
    if user_input.lower() == "quit":
        print("Goodbye!")
        break

    # If the user just pressed Enter without typing anything, ask again
    if not user_input:
        print("Please type something!")
        continue

    # Send the message to Gemini and get a response.
    # This is the actual API call - it sends your message over the internet
    # to Google's servers, and returns the AI's reply.
    response = chat.send_message(user_input)

    # Print the AI's reply.
    # response.text contains the text content of the AI's answer.
    print(f"\nBot: {response.text}")
