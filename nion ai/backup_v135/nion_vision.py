import os
import mss
from PIL import Image
from google import genai

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool(func): 
        return func

# No hardcoded key
_EMBEDDED_KEY = None

def _capture_screen_image() -> Image.Image:
    # 1. Try ImageGrab
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        if img:
            return img
    except Exception:
        pass

    # 2. Try mss
    try:
        with mss.MSS() as sct:
            mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            sct_img = sct.grab(mon)
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    except Exception:
        pass

    # 3. Try pyautogui
    try:
        import pyautogui
        return pyautogui.screenshot()
    except Exception as e:
        raise RuntimeError(f"All screen capture methods failed: {e}")

@function_tool()
async def see_screen(question: str = "Describe what is currently visible on the screen") -> str:
    """
    Captures the user's computer screen and analyzes it. 
    Use this tool whenever the user asks you to look at their screen, read something on their screen, or asks what is currently visible.
    Pass the user's question as the 'question' parameter so the vision model knows what to look for.
    """
    try:
        import asyncio
        def run_vision():
            img = _capture_screen_image()
            # Optimize image size for fast upload
            img.thumbnail((1280, 720))

            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                from pathlib import Path
                import json
                cfg = Path.home() / ".zoraai" / "config.json"
                if cfg.exists():
                    try:
                        api_key = json.loads(cfg.read_text(encoding="utf-8")).get("GOOGLE_API_KEY")
                    except Exception:
                        pass
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=[
                    f"You are looking at the user's screen. Answer this question accurately and concisely: {question}",
                    img
                ]
            )
            return response.text.strip()

        text = await asyncio.to_thread(run_vision)
        return f"Screen observation: {text}"
    except Exception as e:
        return f"I couldn't view the screen right now. Reason: {e}"
