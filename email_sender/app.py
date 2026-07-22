# ============================================================
# app.py - Web Dashboard for our Sales Outreach Agent
# ============================================================

import os
import csv
import streamlit as st
from google import genai
from dotenv import load_dotenv
from research_tool import research_company

# --- 1. LOAD CONFIGURATION ---
# Load the .env file from the parent directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
api_key = os.getenv("GEMINI_API_KEY")

# --- 2. STREAMLIT PAGE CONFIGURATION ---
# This sets the browser tab title and layout
st.set_page_config(
    page_title="Sales Outreach AI Dashboard",
    page_icon="💼",
    layout="wide"
)

# Branded Header
st.title("💼 Sales Outreach AI Agent Dashboard")
st.write("Automatically research leads and draft highly personalized outreach emails using Gemini.")

# Check for API Key
if not api_key:
    st.error("⚠️ GEMINI_API_KEY not found in .env file! Please add it to run this app.")
    st.stop()

# Define Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADS_FILE = os.path.join(BASE_DIR, "leads.csv")
DRAFTS_DIR = os.path.join(BASE_DIR, "drafts")

# Ensure drafts directory exists
os.makedirs(DRAFTS_DIR, exist_ok=True)

# Define the System Instruction for our agent
SYSTEM_INSTRUCTION = (
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

# Helper: Load leads from CSV
def load_leads():
    leads = []
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            leads = list(reader)
    return leads

# Helper: Load a specific draft from file
def load_draft(filename):
    filepath = os.path.join(DRAFTS_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

# Helper: Save an edited draft
def save_draft(filename, content):
    filepath = os.path.join(DRAFTS_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# --- 3. LAYOUT: TWO COLUMNS ---
col1, col2 = st.columns([1, 1])

# --- COLUMN 1: LEAD VIEWER & CONTROLS ---
with col1:
    st.subheader("📋 Active Sales Leads")
    
    leads = load_leads()
    if leads:
        # Show leads in a nice interactive data table
        st.dataframe(leads, use_container_width=True)
    else:
        st.warning("No leads found in leads.csv.")
        
    st.write("---")
    st.subheader("🤖 Agent Controls")
    
    # Button to trigger AI generation
    if st.button("🚀 Run AI Research & Draft Emails", use_container_width=True):
        if not leads:
            st.error("No leads to process.")
        else:
            # Connect client
            client = genai.Client(api_key=api_key)
            
            # Setup progress bar and status text
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for index, lead in enumerate(leads):
                name = lead["Name"]
                company = lead["Company"]
                role = lead["Role"]
                problem = lead["Problem"]
                
                # Update status text
                status_text.write(f"Researching & writing draft for **{name}** ({company})...")
                
                # Create a fresh chat session for this lead
                chat = client.chats.create(
                    model="gemini-2.5-flash",
                    config={
                        "system_instruction": SYSTEM_INSTRUCTION,
                        "tools": [research_company]
                    }
                )
                
                prompt = (
                    f"Lead Details:\n"
                    f"- Name: {name}\n"
                    f"- Company: {company}\n"
                    f"- Job Role: {role}\n"
                    f"- Specific Pain Point: {problem}\n\n"
                    f"Please research this company and draft the personalized email pitch."
                )
                
                # Call Gemini API
                response = chat.send_message(prompt)
                email_content = response.text
                
                # Save draft
                safe_name = name.lower().replace(" ", "_")
                safe_company = company.lower().replace(" ", "_")
                filename = f"{safe_name}_{safe_company}.txt"
                save_draft(filename, email_content)
                
                # Update progress bar
                progress = (index + 1) / len(leads)
                progress_bar.progress(progress)
                
            status_text.success("🎉 All drafts successfully created!")
            st.rerun() # Refresh page to show the new files in Column 2

# --- COLUMN 2: DRAFT VIEWER & EDITOR ---
with col2:
    st.subheader("✉️ Generated Email Drafts")
    
    # Get a list of all txt files inside the drafts directory
    draft_files = []
    if os.path.exists(DRAFTS_DIR):
        draft_files = [f for f in os.listdir(DRAFTS_DIR) if f.endswith(".txt")]
        
    if not draft_files:
        st.info("No drafts generated yet. Click the button on the left to start.")
    else:
        # Create a dropdown list of draft filenames
        selected_file = st.selectbox(
            "Select a draft to review & edit:",
            draft_files,
            format_func=lambda x: x.replace(".txt", "").replace("_", " ").title()
        )
        
        if selected_file:
            # Load the text of the selected file
            current_content = load_draft(selected_file)
            
            # Create a text area so the user can edit the email!
            edited_content = st.text_area(
                "Email Content:",
                value=current_content,
                height=300
            )
            
            # Save button for manual modifications
            if st.button("💾 Save Changes"):
                save_draft(selected_file, edited_content)
                st.success("Draft saved successfully!")
                
            # Send button simulation
            if st.button("✉️ Approve & Send Email", type="primary"):
                # Simulating an email send
                st.balloons() # Fun Streamlit animation!
                st.success(f"Sent email using draft '{selected_file}'!")
