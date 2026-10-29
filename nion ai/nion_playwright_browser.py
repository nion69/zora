import os
import json
import asyncio
import logging
from typing import Optional

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool():
        def decorator(f):
            return f
        return decorator

logger = logging.getLogger("Zora_AutonomousAgent")

# ─────────────────────────────────────────────────────────────
# SINGLETON RESILIENT BROWSER INSTANCE
# ─────────────────────────────────────────────────────────────
_active_playwright = None
_active_browser = None
_active_page = None


def _get_or_create_browser():
    """Maintains a single running browser instance to prevent multiple popups or looping."""
    global _active_playwright, _active_browser, _active_page
    from playwright.sync_api import sync_playwright

    if _active_browser is None or _active_page is None:
        _active_playwright = sync_playwright().start()
        # Launch Chromium with media autoplay enabled & full desktop viewport
        _active_browser = _active_playwright.chromium.launch(
            headless=False,
            args=[
                "--start-maximized",
                "--autoplay-policy=no-user-gesture-required",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        context = _active_browser.new_context(no_viewport=True)
        _active_page = context.new_page()
    else:
        try:
            # Check if existing page is still open
            if _active_page.is_closed():
                context = _active_browser.new_context(no_viewport=True)
                _active_page = context.new_page()
        except Exception:
            _active_browser = None
            return _get_or_create_browser()

    return _active_page


@function_tool()
async def play_youtube_song_in_browser(song_name: str) -> str:
    """
    Autonomously searches YouTube, extracts the best matching video, and plays it directly in the browser with audio.
    Call this when the user says:
    - 'play beggin song in youtube'
    - 'youtube open kore beggin chalao'
    - 'browser-e youtube play koro'
    - 'gaan chalao youtube-e'
    """
    def _execute_youtube():
        try:
            page = _get_or_create_browser()
            query = song_name.replace(" ", "+")
            search_url = f"https://www.youtube.com/results?search_query={query}"
            
            page.goto(search_url, timeout=18000)
            page.wait_for_selector("a#video-title", timeout=10000)

            # Direct DOM extraction of the video URL to avoid click misses
            video_url = page.eval_on_selector("a#video-title", "el => el.href")
            video_title = page.eval_on_selector("a#video-title", "el => el.innerText.trim()")

            if video_url:
                page.goto(video_url, timeout=18000)
                # Try clicking play if paused
                page.wait_for_timeout(2000)
                try:
                    page.keyboard.press("k") # YouTube standard play shortcut
                except Exception:
                    pass
                return f"YouTube-e '{video_title}' play shuru hoye geche babu!"
            return f"YouTube-e '{song_name}' search korechi!"
        except Exception as e:
            logger.warning(f"YouTube error: {e}")
            return f"YouTube-e play korte giye notice: {e}"

    res = await asyncio.to_thread(_execute_youtube)
    return f"Shona, {res}"


@function_tool()
async def close_builtin_browser() -> str:
    """
    Closes the autonomous browser window immediately.
    Call this when the user says: 'close browser', 'browser bondho koro', 'browser off koro'.
    """
    global _active_playwright, _active_browser, _active_page

    def _close():
        global _active_playwright, _active_browser, _active_page
        try:
            if _active_browser:
                _active_browser.close()
            if _active_playwright:
                _active_playwright.stop()
        except Exception:
            pass
        finally:
            _active_browser = None
            _active_playwright = None
            _active_page = None

    await asyncio.to_thread(_close)
    return "Shona, ami browser bondho kore diyechi!"


@function_tool()
async def open_builtin_browser_and_navigate(url_or_query: str) -> str:
    """
    Navigates to any URL or searches the web autonomously in the browser without popping up duplicate windows.
    """
    def _navigate():
        try:
            page = _get_or_create_browser()
            target = url_or_query.strip()
            if not target.startswith("http://") and not target.startswith("https://"):
                target = f"https://{target}" if "." in target and " " not in target else f"https://duckduckgo.com/?q={target.replace(' ', '+')}"

            page.goto(target, timeout=18000)
            page.wait_for_timeout(2000)
            return f"Opened {target}. Page Title: {page.title()}"
        except Exception as e:
            return f"Navigation notice: {e}"

    result = await asyncio.to_thread(_navigate)
    return f"Babu, {result}"


@function_tool()
async def discuss_with_gemini_autonomously(topic: str = "cats") -> str:
    """
    Conducts an intelligent discussion with Google Gemini on any topic and reports the insights.
    Call when the user asks to discuss with Gemini or ask Gemini.
    """
    import urllib.request
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            from pathlib import Path
            cfg = Path.home() / ".zoraai" / "config.json"
            if cfg.exists():
                api_key = json.loads(cfg.read_text(encoding="utf-8")).get("GOOGLE_API_KEY")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
        prompt = (
            f"You are Google Gemini having an intellectual discussion with Neon and his AI assistant Zora. "
            f"Topic: '{topic}'. "
            f"Share 2 deeply fascinating points about this topic in 2 concise sentences."
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            discussion_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return f"Babu, ami Gemini-r sathe '{topic}' niye discuss korechi! Gemini bollo: {discussion_text}"
    except Exception as e:
        return f"Gemini-r sathe discuss korte giye notice: {e}"
