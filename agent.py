# ============================================================
# agent.py - A true AI Agent with local tools
# ============================================================

import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: No API key found.")
    exit()

# ------------------------------------------------------------
# 1. DEFINE THE TOOLS
# These are normal Python functions. 
# Google Gemini reads the function name, arguments, and docstring (the """ text)
# to understand when and how to use them.
# ------------------------------------------------------------

def list_files() -> str:
    """Lists all files in the current project directory."""
    try:
        files = os.listdir('.')
        # Filter out venv, __pycache__, and hidden files like .env to keep it clean
        clean_files = [f for f in files if f not in ['venv', '__pycache__'] and not f.startswith('.')]
        if not clean_files:
            return "The directory is empty."
        return "Files in directory:\n" + "\n".join(f"- {f}" for f in clean_files)
    except Exception as e:
        return f"Error listing files: {str(e)}"

def read_file(filename: str) -> str:
    """
    Reads the content of a file in the project directory.
    
    Args:
        filename: The exact name of the file to read.
    """
    try:
        # Security check: don't let the agent read files outside this folder
        if '/' in filename or '\\' in filename or filename.startswith('.'):
            return "Access denied: You can only read files in the local directory."
            
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File '{filename}' not found."
    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_file(filename: str, content: str) -> str:
    """
    Creates a new file or overwrites an existing file with content.
    
    Args:
        filename: The name of the file to write.
        content: The text content to write into the file.
    """
    try:
        # Security check
        if '/' in filename or '\\' in filename or filename.startswith('.'):
            return "Access denied: You can only write files in the local directory."
            
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Success: Written content to '{filename}'."
    except Exception as e:
        return f"Error writing file: {str(e)}"


# ------------------------------------------------------------
# 2. CONFIGURE THE CLIENT AND CHAT
# ------------------------------------------------------------

client = genai.Client(api_key=api_key)

# We start a chat session, but this time we provide the "tools" parameter!
# We pass a list of our actual Python functions.
# The Gemini SDK handles all the back-and-forth communication automatically.
chat = client.chats.create(
    model="gemini-2.5-flash",
    config={
        "system_instruction": (
            "You are a helpful File Assistant Agent. You can inspect, read, and write "
            "files in the current directory using your tools. Always tell the user "
            "what action you are taking."
        ),
        "tools": [list_files, read_file, write_file]
    }
)

# ------------------------------------------------------------
# 3. RUN THE AGENT LOOP
# ------------------------------------------------------------
print("=" * 50)
print("File Manager Agent - Type 'quit' to exit")
print("=" * 50)

while True:
    user_input = input("\nYou: ").strip()

    if user_input.lower() == "quit":
        print("Goodbye!")
        break

    if not user_input:
        print("Please type something!")
        continue

    # Send message to the agent.
    # Because we gave it tools, if the agent decides it needs to run a tool,
    # the SDK will:
    # 1. Receive the request from Gemini
    # 2. Execute our local Python function automatically
    # 3. Send the result back to Gemini
    # 4. Return the final text answer to us
    response = chat.send_message(user_input)

    print(f"\nAgent: {response.text}")
