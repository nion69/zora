import os
import requests
import logging
from dotenv import load_dotenv
from livekit.agents import function_tool  # ✅ Correct decorator
from datetime import datetime
from livekit import agents

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import os
import requests
import logging
from livekit.agents import function_tool

logger = logging.getLogger(__name__)

@function_tool()
async def google_search(query: str) -> str:
    """
    Searches the web and returns the top 3 results with heading and summary only.
    No raw links are included to make speech output sound natural.
    """

    logger.info(f"Query प्राप्त हुई: {query}")

    try:
        from duckduckgo_search import DDGS
        import asyncio
        logger.info("DuckDuckGo से search किया जा रहा है...")
        
        def run_search():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=3))
                
        search_results = await asyncio.to_thread(run_search)
        
        if not search_results:
            return "कोई results नहीं मिले।"

        formatted = "Here are the top results:\n"
        for i, item in enumerate(search_results, start=1):
            title = item.get("title", "No title")
            snippet = item.get("body", "").strip()
            formatted += f"{i}. {title}. {snippet}\n\n"

        return formatted.strip()

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return f"Web Search fail ho gaya: {e}"


@function_tool()
async def get_current_datetime() -> str:
    """
    Returns the current date and time in a human-readable format.

    Use this tool when the user asks for the current time, date, or wants to know what day it is.
    Example prompts:
    - "अब क्या time हो रहा है?"
    - "आज की तारीख क्या है?"
    - "What’s the time right now?"
    """

    now = datetime.now()
    formatted = now.strftime("%d %B %Y, %I:%M %p")  # Example: 31 July 2025, 04:22 PM
    return formatted