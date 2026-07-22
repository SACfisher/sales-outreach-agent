# ============================================================
# app.py - AI Sales Outreach Agent (Powered by Groq)
# ============================================================
# This single file contains:
#   - The web scraping tool
#   - The AI agent pipeline (using Groq's free tier)
#   - The full Streamlit UI
#
# WHY GROQ?
# Groq gives 30 requests/minute and 14,400 requests/day for FREE.
# That is 10x more generous than Gemini's free tier.
# ============================================================

import os
import json
import time
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import streamlit as st
from groq import Groq

# ============================================================
# 1. CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Sales Outreach Agent",
    page_icon="💼",
    layout="wide"
)

# Load API key — works both locally (.env) and on Streamlit Cloud (st.secrets)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

try:
    api_key      = st.secrets["GROQ_API_KEY"]
    sender_email = st.secrets["SENDER_EMAIL"]
    sender_pass  = st.secrets["SENDER_APP_PASSWORD"]
except Exception:
    api_key      = os.getenv("GROQ_API_KEY")
    sender_email = os.getenv("SENDER_EMAIL")
    sender_pass  = os.getenv("SENDER_APP_PASSWORD")

MODEL = "llama-3.3-70b-versatile"


# ============================================================
# 2. THE WEB SCRAPING TOOL
# ============================================================

def scrape_website(url: str) -> str:
    """Downloads and cleans text content from a website URL."""
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
        for element in soup(["script", "style", "header", "footer", "nav"]):
            element.extract()
        clean_text = soup.get_text()
        lines = (line.strip() for line in clean_text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        final_text = "\n".join(chunk for chunk in chunks if chunk)
        if len(final_text) > 5000:
            return final_text[:5000] + "\n\n[Content truncated...]"
        return final_text
    except Exception as e:
        return f"Error scraping website: {str(e)}"


# ============================================================
# 3. TOOL DEFINITION (Groq/OpenAI JSON Schema Format)
#
# Unlike Gemini which accepted Python functions directly,
# Groq (and OpenAI) require us to describe the tool as a
# JSON schema object. This tells the AI:
#   - The tool's name
#   - What it does (description)
#   - What arguments it needs (parameters)
# ============================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "scrape_website",
            "description": (
                "Downloads and cleans the readable text content from a website. "
                "Use this to research a company by reading their homepage."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full web address, e.g. https://en.wikipedia.org/wiki/Apple_Inc."
                    }
                },
                "required": ["url"]
            }
        }
    }
]


# ============================================================
# 4. THE AGENT PIPELINE
#
# HOW TOOL CALLING WORKS WITH GROQ:
#
# Unlike Gemini (which ran tools automatically behind the scenes),
# with Groq we manage the tool-calling loop ourselves:
#
#   Round 1: We send the user's request → Groq decides to call scrape_website
#   We run: We call our scrape_website() Python function
#   Round 2: We send the scraping result back → Groq writes the final response
#
# This gives us full visibility and control over what's happening.
# ============================================================

def run_pipeline(lead: dict, client: Groq) -> dict:
    """
    Runs the full research + email drafting pipeline for one lead.
    Uses a single agent with one tool (scrape_website).
    Makes at most 2 API calls: one to trigger the tool, one for the final output.
    """

    system_instruction = (
        "You are a sales research and outreach specialist.\n\n"
        "Your job has two parts:\n"
        "PART 1 - RESEARCH: Use the scrape_website tool to visit the company "
        "website. Produce a brief research report with:\n"
        "  - COMPANY SUMMARY: What do they do?\n"
        "  - KEY DETAIL: One specific, interesting recent fact.\n\n"
        "PART 2 - EMAIL: Write a short (under 150 words) personalized outreach "
        "email that:\n"
        "  - Addresses the lead by first name\n"
        "  - References the KEY DETAIL from your research\n"
        "  - Addresses their specific business problem\n"
        "  - Ends with a simple call-to-action\n\n"
        "Format your final response EXACTLY like this:\n"
        "### RESEARCH REPORT\n"
        "(your research here)\n\n"
        "### EMAIL DRAFT\n"
        "(your email here)"
    )

    # Build the message history — starts with system + user request
    messages = [
        {"role": "system", "content": system_instruction},
        {
            "role": "user",
            "content": (
                f"Lead Details:\n"
                f"- Name: {lead['name']}\n"
                f"- Company: {lead['company']}\n"
                f"- Website: {lead['url']}\n"
                f"- Role: {lead['role']}\n"
                f"- Problem: {lead['problem']}\n\n"
                f"Please scrape their website, write the research report, "
                f"then write the personalized email draft."
            )
        }
    ]

    # --- ROUND 1: First API call ---
    # We send the messages and the tool schema.
    # Groq will decide whether to call the tool or answer directly.
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto"  # Let the AI decide when to use the tool
    )

    response_message = response.choices[0].message

    # --- TOOL EXECUTION ---
    # If Groq decided to call our tool, we run it here in Python
    if response_message.tool_calls:
        # Add the AI's decision to call the tool into our message history
        messages.append(response_message)

        # Loop through each tool call (there could be more than one)
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            # The arguments come as a JSON string, so we parse them
            function_args = json.loads(tool_call.function.arguments)

            # Execute the correct Python function based on the name
            if function_name == "scrape_website":
                tool_result = scrape_website(**function_args)
            else:
                tool_result = f"Unknown tool: {function_name}"

            # Add the tool's output to the message history
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": tool_result
            })

        # --- ROUND 2: Second API call ---
        # Now we send the full history (including tool results) back to Groq.
        # Groq reads the scraped website content and writes the final response.
        final_response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS
        )
        full_text = final_response.choices[0].message.content or ""

    else:
        # If no tool was called, use the direct response
        full_text = response_message.content or ""

    # --- PARSE THE RESPONSE ---
    # Split the response into research and email sections
    if "### EMAIL DRAFT" in full_text:
        parts = full_text.split("### EMAIL DRAFT")
        research = parts[0].replace("### RESEARCH REPORT", "").strip()
        email = parts[1].strip()
    else:
        research = "Research embedded in response."
        email = full_text

    return {"research": research, "email": email}


# ============================================================
# 5. THE STREAMLIT UI
# ============================================================

st.title("AI Sales Outreach Agent")
st.write(
    "Automatically research companies and draft personalized sales emails. "
    "Powered by Groq (Llama 3.3) — free, fast, and no rate limit headaches."
)

if not api_key:
    st.error("No GROQ_API_KEY found. Add it to your .env file or Streamlit Secrets.")
    st.stop()

if not sender_email or not sender_pass:
    st.warning(
        "Email sending is disabled. "
        "Add SENDER_EMAIL and SENDER_APP_PASSWORD to your .env file to enable it."
    )

# ============================================================
# EMAIL SENDING FUNCTION
# Uses Gmail's SMTP server to send real emails.
# smtplib is built into Python — no extra install needed.
# ============================================================

def send_email(to_address: str, subject: str, body: str) -> tuple[bool, str]:
    """
    Sends an email via Gmail SMTP.
    Returns (success: bool, message: str).
    """
    if not sender_email or not sender_pass:
        return False, "Sender credentials not configured in .env"
    try:
        # Build the email message
        msg = MIMEMultipart()
        msg["From"]    = sender_email
        msg["To"]      = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Try port 465 (SSL) first — less likely to be blocked by firewalls.
        # Falls back to port 587 (STARTTLS) if 465 fails.
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, sender_pass)
                server.sendmail(sender_email, to_address, msg.as_string())
        except Exception:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.ehlo()
                server.starttls()
                server.login(sender_email, sender_pass)
                server.sendmail(sender_email, to_address, msg.as_string())

        return True, f"Email successfully sent to {to_address}!"
    except smtplib.SMTPAuthenticationError:
        return False, "Authentication failed. Check your App Password in .env."
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"

# Initialise session state
if "leads" not in st.session_state:
    st.session_state.leads = []
if "results" not in st.session_state:
    st.session_state.results = {}

# Two-column layout
left, right = st.columns([1, 1.4])

# ============================================================
# LEFT COLUMN: Lead Manager
# ============================================================
with left:
    st.subheader("Manage Leads")

    with st.form("add_lead_form", clear_on_submit=True):
        st.write("**Add a new lead:**")
        name       = st.text_input("Full Name",            placeholder="e.g. Alice Smith")
        lead_email = st.text_input("Lead's Email Address", placeholder="e.g. alice@acmecorp.com")
        company    = st.text_input("Company Name",         placeholder="e.g. Acme Corp")
        url        = st.text_input("Company Website URL",  placeholder="e.g. https://en.wikipedia.org/wiki/Tesla,_Inc.")
        role       = st.text_input("Job Title / Role",     placeholder="e.g. Head of Operations")
        problem    = st.text_area("Their Business Problem",
                                  placeholder="e.g. They struggle to automate invoicing.",
                                  height=80)
        submitted = st.form_submit_button("Add Lead", use_container_width=True)

        if submitted:
            if name and lead_email and company and url and role and problem:
                st.session_state.leads.append({
                    "name": name, "email": lead_email, "company": company,
                    "url": url, "role": role, "problem": problem
                })
                st.success(f"Added: {name} at {company}")
            else:
                st.warning("Please fill in all fields including the lead's email.")

    st.write("---")

    if st.session_state.leads:
        st.write(f"**Current Leads ({len(st.session_state.leads)}):**")
        for i, lead in enumerate(st.session_state.leads):
            st.write(f"{i+1}. **{lead['name']}** — {lead['role']} at {lead['company']}")

        col1, col2 = st.columns(2)
        with col1:
            run_button = st.button("Run AI Pipeline", use_container_width=True, type="primary")
        with col2:
            if st.button("Clear All Leads", use_container_width=True):
                st.session_state.leads = []
                st.session_state.results = {}
                st.rerun()

        if run_button:
            groq_client = Groq(api_key=api_key)
            total = len(st.session_state.leads)
            progress_bar = st.progress(0, text="Starting pipeline...")

            for i, lead in enumerate(st.session_state.leads):
                progress_bar.progress(i / total, text=f"Processing {lead['name']} ({i+1}/{total})...")

                with st.status(
                    f"Working on {lead['name']} at {lead['company']}...",
                    expanded=True
                ) as status:
                    try:
                        st.write("Scraping company website...")
                        result = run_pipeline(lead, groq_client)
                        st.write("Email drafted successfully!")
                        st.session_state.results[lead["name"]] = result
                        status.update(
                            label=f"Done: {lead['name']} at {lead['company']}",
                            state="complete", expanded=False
                        )
                    except Exception as e:
                        status.update(
                            label=f"Error on {lead['name']}: {str(e)[:80]}",
                            state="error"
                        )

                # Small pause between leads to be polite to the API
                if i < total - 1:
                    time.sleep(3)

            progress_bar.progress(1.0, text="Pipeline complete!")
            st.rerun()

    else:
        st.info("No leads added yet. Use the form above to add your first lead.")


# ============================================================
# RIGHT COLUMN: Results Viewer & Editor
# ============================================================
with right:
    st.subheader("Generated Email Drafts")

    if not st.session_state.results:
        st.info("Add leads and click 'Run AI Pipeline' to see results here.")
    else:
        for lead_name, result in st.session_state.results.items():
            lead_info = next(
                (l for l in st.session_state.leads if l["name"] == lead_name),
                {"company": "Unknown"}
            )

            with st.expander(f"{lead_name} — {lead_info['company']}", expanded=True):
                with st.expander("View Research Report"):
                    st.markdown(result["research"])

                st.write("**Final Email Draft:**")
                edited_email = st.text_area(
                    label="Edit the email below:",
                    value=result["email"],
                    height=200,
                    key=f"email_{lead_name}"
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save Changes", key=f"save_{lead_name}"):
                        st.session_state.results[lead_name]["email"] = edited_email
                        st.success("Saved!")
                with col2:
                    if st.button("Approve & Send", key=f"send_{lead_name}", type="primary"):
                        to_addr = lead_info.get("email", "")
                        if not to_addr:
                            st.error("No email address found for this lead.")
                        else:
                            subject = f"A quick note for {lead_name.split()[0]}"
                            success, msg = send_email(to_addr, subject, edited_email)
                            if success:
                                st.balloons()
                                st.success(msg)
                            else:
                                st.error(msg)
