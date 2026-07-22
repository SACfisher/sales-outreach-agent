# ============================================================
# agent_team.py - A two-agent pipeline (Researcher + Copywriter)
# ============================================================

# --- WHAT IS HAPPENING HERE? ---
# Instead of one agent doing everything, we have TWO specialized agents:
#
#   Agent 1 (Researcher): Has a web scraping tool. Its ONLY job is to
#   visit the company's website and produce a structured research report.
#
#   Agent 2 (Copywriter): Has NO tools. Its ONLY job is to take the
#   research report and write a polished, personalized sales email.
#
#   The Orchestrator: The `run_pipeline()` function connects the two.
#   It runs Agent 1, captures the output, then feeds it to Agent 2.

import os
import sys
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai

# --- 1. LOAD CONFIGURATION ---
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: No API key found.")
    exit()

client = genai.Client(api_key=api_key)
MODEL = "gemini-2.5-flash"

# ============================================================
# 2. DEFINE THE TOOLS
# Only the Researcher Agent gets tools. The Copywriter gets none.
# ============================================================

def scrape_website(url: str) -> str:
    """
    Downloads the text content of a website and cleans it.
    Use this to read a company's website and understand what they do.

    Args:
        url: The full website address starting with http:// or https://.
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove non-readable sections
        for element in soup(["script", "style", "header", "footer", "nav"]):
            element.extract()

        clean_text = soup.get_text()
        lines = (line.strip() for line in clean_text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        final_text = "\n".join(chunk for chunk in chunks if chunk)

        # Truncate to keep cost and speed manageable
        if len(final_text) > 5000:
            return final_text[:5000] + "\n\n[Content truncated for length...]"

        return final_text

    except Exception as e:
        return f"Error scraping website: {str(e)}"


# ============================================================
# 3. DEFINE THE TWO AGENTS
# ============================================================

def create_researcher_agent():
    """
    Creates and returns the Researcher Agent chat session.
    This agent is equipped with the scrape_website tool.
    Its system instruction tells it to act as a research specialist.
    """
    return client.chats.create(
        model=MODEL,
        config={
            "system_instruction": (
                "You are a specialist company research agent.\n"
                "Your ONLY job is to research companies by visiting their websites.\n\n"
                "When given a company name and URL:\n"
                "1. Use the 'scrape_website' tool to read their website.\n"
                "2. Produce a structured research report with these sections:\n"
                "   - COMPANY SUMMARY: What does the company do?\n"
                "   - PRODUCTS/SERVICES: What do they sell or offer?\n"
                "   - TONE & VALUES: What is their brand personality?\n"
                "   - KEY DETAIL: One specific interesting fact or recent update.\n\n"
                "Be factual. Only include information you read on the website."
            ),
            "tools": [scrape_website]
        }
    )


def create_copywriter_agent():
    """
    Creates and returns the Copywriter Agent chat session.
    This agent has NO tools — it only needs to write.
    Its system instruction tells it to act as a sales email writer.
    """
    return client.chats.create(
        model=MODEL,
        config={
            "system_instruction": (
                "You are an expert B2B sales copywriter.\n"
                "You will receive a research report about a company and details about a lead.\n"
                "Your ONLY job is to write a short, highly personalized outreach email.\n\n"
                "Email guidelines:\n"
                "- Address the lead by their first name.\n"
                "- Reference a SPECIFIC detail from the research report (shows you did your homework).\n"
                "- Clearly connect their business problem to a solution.\n"
                "- Keep it under 150 words (short emails get more replies).\n"
                "- End with a simple, low-pressure call-to-action.\n"
                "- Tone: Professional, warm, and confident."
            )
            # Notice: NO tools here. The Copywriter just needs to write.
        }
    )


# ============================================================
# 4. THE ORCHESTRATOR
# This function manages the conversation between the two agents.
# It runs Agent 1, captures the output, then sends it to Agent 2.
# ============================================================

def run_pipeline(lead: dict) -> dict:
    """
    Runs the full two-agent pipeline for a single lead.
    Returns a dictionary containing the research report and the final email.
    """
    name = lead["name"]
    company = lead["company"]
    url = lead["url"]
    role = lead["role"]
    problem = lead["problem"]

    print(f"\n{'=' * 60}")
    print(f"  Processing lead: {name} | {role} at {company}")
    print(f"{'=' * 60}")

    # ----- STEP 1: Run the Researcher Agent -----
    print("\n[1/2] Researcher Agent is analyzing the website...")

    researcher = create_researcher_agent()

    research_prompt = (
        f"Please research the following company:\n"
        f"- Company Name: {company}\n"
        f"- Website URL: {url}\n\n"
        f"Scrape their website and produce a structured research report."
    )

    research_response = researcher.send_message(research_prompt)
    research_report = research_response.text

    print("      Research report received!")
    print(f"\n--- RESEARCHER OUTPUT ---\n{research_report}\n")

    # ----- STEP 2: Run the Copywriter Agent -----
    # Notice: we pass the research_report TEXT directly to the Copywriter.
    # The Copywriter does not have internet access — it relies entirely
    # on what the Researcher already found.
    print("[2/2] Copywriter Agent is drafting the email...")

    copywriter = create_copywriter_agent()

    copywriter_prompt = (
        f"Here is the research report about the company:\n\n"
        f"{research_report}\n\n"
        f"Lead Details:\n"
        f"- Name: {name}\n"
        f"- Job Role: {role}\n"
        f"- Company: {company}\n"
        f"- Business Problem: {problem}\n\n"
        f"Please write the personalized sales outreach email now."
    )

    email_response = copywriter.send_message(copywriter_prompt)
    final_email = email_response.text

    print(f"\n--- COPYWRITER OUTPUT (FINAL EMAIL) ---\n{final_email}\n")

    return {
        "lead": name,
        "company": company,
        "research": research_report,
        "email": final_email
    }


# ============================================================
# 5. MAIN: RUN THE PIPELINE FOR A LIST OF LEADS
# We use REAL, publicly accessible URLs here so our scraper has
# something live to read. Wikipedia articles work perfectly!
# ============================================================

LEADS = [
    {
        "name": "Joseph",
        "company": "Techcrush",
        "url": "https://techcrush.pro",
        "role": "Head of Operations",
        "problem": "They are struggling to increase their student scale as they scale globally."
    },
    {
        "name": "Bob Jones",
        "company": "Spotify",
        "url": "https://en.wikipedia.org/wiki/Spotify",
        "role": "Marketing Director",
        "problem": "They want to increase podcast listener retention beyond the first 3 episodes."
    }
]

if __name__ == "__main__":
    print("\nMulti-Agent Pipeline Starting...")
    print(f"Processing {len(LEADS)} leads using a 2-agent team.\n")

    results = []
    for lead in LEADS:
        result = run_pipeline(lead)
        results.append(result)

    print("\n" + "=" * 60)
    print(f"  Pipeline Complete! Processed {len(results)} leads.")
    print("=" * 60)
