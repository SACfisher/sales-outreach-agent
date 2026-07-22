import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

try:
    print("Testing gemini-2.5-flash...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Say 'Hello' back to me."
    )
    print("SUCCESS! Response:")
    print(response.text.strip())
except Exception as e:
    print("ERROR:", e)
