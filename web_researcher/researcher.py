# ============================================================
# researcher.py - A live web research agent
# ============================================================

import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai

# --- 1. LOAD CONFIGURATION ---
# Load .env file from the parent folder
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: No API key found. Make sure your .env file has GEMINI_API_KEY.")
    exit()

# --- 2. DEFINE THE WEB SCRAPING TOOL ---
def scrape_website(url: str) -> str:
    """
    Downloads the text content of a website and cleans it.
    Use this tool whenever the user asks you to read or research a specific URL.
    
    Args:
        url: The absolute web address (URL) starting with http:// or https://.
    """
    try:
        # A standard "User-Agent" header. This tells the website that
        # this request is coming from a normal Windows Chrome browser,
        # which prevents the website from blocking our script.
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        
        # Download the website content (timeout if it takes more than 10 seconds)
        response = requests.get(url, headers=headers, timeout=10)
        
        # Check if the download was successful (status code 200)
        response.raise_for_status()
        
        # Parse the raw HTML code using BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove all JavaScript and CSS code from the page
        for element in soup(["script", "style", "header", "footer", "nav"]):
            element.extract()
            
        # Get only the remaining readable text
        clean_text = soup.get_text()
        
        # Clean up double line breaks and empty spaces
        lines = (line.strip() for line in clean_text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        final_text = "\n".join(chunk for chunk in chunks if chunk)
        
        # Truncate the text to the first 5000 characters to keep it compact
        if len(final_text) > 5000:
            return final_text[:5000] + "\n\n[Content truncated for length...]"
        
        return final_text
        
    except Exception as e:
        return f"Error trying to scrape website: {str(e)}"

# --- 3. SET UP THE AGENT ---
client = genai.Client(api_key=api_key)

chat = client.chats.create(
    model="gemini-2.5-flash",
    config={
        "system_instruction": (
            "You are a helpful Web Research Assistant. Your job is to answer the user's "
            "questions by researching the web pages they provide.\n\n"
            "Guidelines:\n"
            "- If the user provides a URL, you MUST call the 'scrape_website' tool to read it.\n"
            "- Always tell the user that you are scraping the website.\n"
            "- Answer the user's question using ONLY the facts you read on the website.\n"
            "- Keep your summaries clear, accurate, and concise."
        ),
        "tools": [scrape_website]
    }
)

# --- 4. THE CHAT LOOP ---
print("=" * 60)
print("Live Web Research Agent - Type 'quit' to exit")
print("=" * 60)

while True:
    user_input = input("\nYou: ").strip()

    if user_input.lower() == "quit":
        print("Goodbye!")
        break

    if not user_input:
        print("Please type something!")
        continue

    # Send the user's message to Gemini
    # If the user input contains a URL, the agent will decide to call scrape_website
    response = chat.send_message(user_input)
    
    print(f"\nAgent: {response.text}")
