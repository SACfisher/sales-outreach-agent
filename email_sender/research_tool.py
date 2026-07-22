# ============================================================
# research_tool.py - Company research simulation tool
# ============================================================

# Pre-defined database to simulate a deep web search of company info.
# In a real enterprise app, this tool would call a Google Search API 
# or a web scraper. To keep it free and fast, we simulate it here!
COMPANY_DATABASE = {
    "quantum tech": {
        "summary": "Quantum Tech is a leading cloud hosting provider specializing in high-performance cloud servers for enterprise applications.",
        "recent_news": "They recently announced their new 'Quantum-Shield' security feature and celebrated crossing 10,000 active corporate clients.",
        "values": "Reliability, cutting-edge speed, and absolute security."
    },
    "green foods": {
        "summary": "Green Foods is an organic meal-delivery startup that brings healthy, pre-portioned ingredients to busy families.",
        "recent_news": "They recently partnered with local vertical farms to guarantee farm-to-table delivery within 24 hours.",
        "values": "Sustainability, healthy living, and local community support."
    },
    "buildco": {
        "summary": "BuildCo is a residential construction company specializing in custom eco-friendly home renovations and smart-home integration.",
        "recent_news": "They were recently featured in 'Modern Home' magazine for building the first fully solar-powered residential block in the city.",
        "values": "Eco-friendly design, premium quality, and client-first communication."
    }
}

def research_company(company_name: str) -> str:
    """
    Simulates searching the web for information about a company.
    Use this to find recent news, company summary, and core values.
    
    Args:
        company_name: The name of the company to research.
    """
    # Clean the input (lowercase, strip whitespace) to make matches easier
    clean_name = company_name.strip().lower()
    
    # Check if the company is in our "database"
    if clean_name in COMPANY_DATABASE:
        info = COMPANY_DATABASE[clean_name]
        return (
            f"Research Results for {company_name}:\n"
            f"- Company Summary: {info['summary']}\n"
            f"- Recent News/Milestone: {info['recent_news']}\n"
            f"- Core Values: {info['values']}"
        )
    else:
        # If they ask for a company we don't know, return a generic profile
        return (
            f"Research Results for {company_name}:\n"
            f"- Company Summary: A modern business operating in the {company_name} sector.\n"
            f"- Recent News/Milestone: Currently expanding their digital operations and client base.\n"
            f"- Core Values: Customer success and innovation."
        )
