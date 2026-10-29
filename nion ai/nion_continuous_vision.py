import os
import asyncio
import logging
from PIL import Image, ImageGrab

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool(func):
        return func

logger = logging.getLogger("MJ_ContinuousVision")
logger.setLevel(logging.INFO)

# Global holder for latest screen observation
_latest_screen_summary = "Screen is active. No visual analysis requested yet."
_is_monitoring = False

async def background_screen_monitor():
    """
    Continuous background loop that grabs screen snapshots and maintains live visual context.
    Runs constantly so MJ always has real-time visual awareness of your desktop.
    """
    global _latest_screen_summary, _is_monitoring
    _is_monitoring = True
    logger.info("👁️ Always-On Continuous Live Screen Monitor started.")

    from google import genai
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_API_KEY missing for continuous vision.")
        return

    client = genai.Client(api_key=api_key)

    while _is_monitoring:
        try:
            def grab_and_analyze():
                try:
                    img = ImageGrab.grab()
                    response = client.models.generate_content(
                        model='gemini-3.5-flash-lite',
                        contents=["Summarize in 1 concise sentence what active apps/windows or content are visible on this computer screen right now.", img]
                    )
                    return response.text.strip()
                except Exception as ex:
                    return f"Active screen grab: {ex}"

            summary = await asyncio.to_thread(grab_and_analyze)
            _latest_screen_summary = summary
            logger.debug(f"👁️ Live Screen Frame Update: {summary[:100]}...")
        except Exception as e:
            logger.error(f"Error in continuous vision loop: {e}")

        # Sample frame every 5 seconds to conserve API quota while staying responsive
        await asyncio.sleep(5)

@function_tool()
async def get_live_screen_context() -> str:
    """
    Returns the real-time continuous visual summary of the user's desktop screen.
    Use this whenever you need instant visual context without taking a manual screenshot.
    """
    global _latest_screen_summary
    return f"👁️ **Real-Time Desktop Screen Awareness:** {_latest_screen_summary}"
