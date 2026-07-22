# ============================================================
# outreach_engine.py - The main orchestrator of the agent
# ============================================================

import os
import csv
from dotenv import load_dotenv
from google import genai
from research_tool import research_company

# --- 1. LOAD CONFIGURATION ---
# Load the .env file from the parent directory because it lives in ai-agent-learner/
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: No API key found. Make sure your .env file in the parent folder has GEMINI_API_KEY.")
    exit()

# --- 2. SET UP DIRECTORIES ---
# Define paths relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADS_FILE = os.path.join(BASE_DIR, "leads.csv")
DRAFTS_DIR = os.path.join(BASE_DIR, "drafts")

# Create the drafts directory if it does not exist
os.makedirs(DRAFTS_DIR, exist_ok=True)

# --- 3. SET UP THE AI CLIENT & AGENT ---
client = genai.Client(api_key=api_key)

# We define the system instructions. This tells the AI:
# - Who it is (an expert sales outreach agent).
# - What its tone should be (professional, concise).
# - What tools it has and when it MUST use them.
system_instruction = (
    "You are an expert sales outreach assistant. Your job is to draft personalized "
    "sales outreach emails to potential clients.\n\n"
    "Step 1: You MUST research the company first using the 'research_company' tool.\n"
    "Step 2: Read the research results carefully.\n"
    "Step 3: Draft a professional, highly personalized email pitch.\n\n"
    "Guidelines for the email:\n"
    "- Keep it short and punchy (no more than 3 paragraphs).\n"
    "- Address it to the lead by name.\n"
    "- Mention a specific detail from the research findings (like their recent news or values) "
    "to prove you actually researched them.\n"
    "- Address their specific problem (found in the prompt) and explain how we can help.\n"
    "- Keep the tone professional but warm and friendly.\n"
    "- End with a clear call-to-action (e.g., 'Are you open to a quick 10-minute call next week?')."
)

# --- 4. THE OUTREACH LOOP ---
print("=" * 60)
print("Sales Outreach Agent - Starting Automation Engine...")
print("=" * 60)

# Read the leads from our CSV file
try:
    with open(LEADS_FILE, mode='r', encoding='utf-8') as f:
        # csv.DictReader reads each row as a dictionary where keys are the column headers
        reader = csv.DictReader(f)
        leads = list(reader)
except FileNotFoundError:
    print(f"ERROR: Leads file not found at {LEADS_FILE}")
    exit()

print(f"Loaded {len(leads)} leads. Starting research and drafting...\n")

# Process each lead
for index, lead in enumerate(leads, 1):
    name = lead["Name"]
    company = lead["Company"]
    role = lead["Role"]
    problem = lead["Problem"]
    
    print(f"[{index}/{len(leads)}] Processing {name} ({role} at {company})...")
    
    # Start a fresh chat session for this lead so the history from the previous 
    # lead's email doesn't bleed into this one!
    chat = client.chats.create(
        model="gemini-2.5-flash",
        config={
            "system_instruction": system_instruction,
            "tools": [research_company]
        }
    )
    
    # We construct a prompt with the lead's details
    prompt = (
        f"Lead Details:\n"
        f"- Name: {name}\n"
        f"- Company: {company}\n"
        f"- Job Role: {role}\n"
        f"- Specific Pain Point: {problem}\n\n"
        f"Please research this company and draft the personalized email pitch."
    )
    
    # The API call automatically triggers our research_company function under the hood,
    # passes the output back to Gemini, and returns the final email text.
    response = chat.send_message(prompt)
    email_content = response.text
    
    # Save the generated email draft to a file
    # Clean the name to make a safe filename (replace spaces with underscores)
    safe_name = name.lower().replace(" ", "_")
    safe_company = company.lower().replace(" ", "_")
    filename = f"{safe_name}_{safe_company}.txt"
    filepath = os.path.join(DRAFTS_DIR, filename)
    
    with open(filepath, "w", encoding="utf-8") as out_file:
        out_file.write(email_content)
        
    print(f"   -> Saved email draft to drafts/{filename}\n")

print("=" * 60)
print("Automation Completed! All drafts saved in 'email_sender/drafts/' folder.")
print("=" * 60)
