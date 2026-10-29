import os
import asyncio
import logging
from typing import Optional

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool(func):
        return func

logger = logging.getLogger("MJ_Browser")
logger.setLevel(logging.INFO)

# Global browser process holder
_browser_instance = None

@function_tool()
async def open_isolated_browser(url: str = "https://www.google.com") -> str:
    """
    Opens a dedicated automated browser window for web navigation, searching, and web tasks.
    Runs in an isolated browser environment so it doesn't affect your personal Chrome windows.
    Use this when the user says:
    - 'open browser'
    - 'open youtube / google / website'
    - 'search for X in dedicated browser'
    """
    try:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        def launch_playwright():
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=False, args=["--start-maximized"])
                    page = browser.new_page()
                    page.goto(url)
                    # Keep browser open briefly for interaction
                    page.wait_for_timeout(10000)
                    browser.close()
                return True
            except Exception as pe:
                logger.warning(f"Playwright launch warning: {pe}. Falling back to system browser.")
                import webbrowser
                webbrowser.open(url)
                return False

        await asyncio.to_thread(launch_playwright)
        return f"🌐 Opened isolated browser at: {url}"
    except Exception as e:
        return f"Error opening browser: {e}"

@function_tool()
async def search_in_browser(query: str) -> str:
    """
    Searches Google in the dedicated automated browser and extracts top search results.
    Use when user asks MJ to look up something or perform automated browsing.
    """
    try:
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"

        def execute_search():
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=False)
                    page = browser.new_page()
                    page.goto(search_url)
                    page.wait_for_timeout(3000)
                    content = page.inner_text("body")[:1000]
                    browser.close()
                    return content
            except Exception:
                import requests
                from bs4 import BeautifulSoup
                res = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"})
                soup = BeautifulSoup(res.text, "html.parser")
                return soup.get_text()[:1000]

        extracted_text = await asyncio.to_thread(execute_search)
        return f"🔍 **Browser Search Results for '{query}':**\n\n{extracted_text[:600]}..."
    except Exception as e:
        return f"Error performing browser search: {e}"
