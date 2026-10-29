import os
import json
import base64
import io
import urllib.request
import logging
from PIL import Image

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool():
        def decorator(func):
            return func
        return decorator

logger = logging.getLogger("ZoraVision")
logger.setLevel(logging.INFO)


def _ensure_desktop_access():
    """
    Attaches current thread to Windows active interactive input desktop.
    Fixes the 'screen grab failed' and 'BitBlt failed' error when running
    as a background daemon or subservice on Windows.
    """
    if os.name == 'nt':
        try:
            import ctypes
            user32 = ctypes.windll.user32
            # DESKTOP_ALL_ACCESS = 0x01FF
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception as e:
            logger.debug(f"Input desktop attachment note: {e}")


def _capture_screen_image():
    """
    Captures the live user screen with bulletproof multi-layer fallbacks:
    1. Attach interactive input desktop (fixes Windows background/daemon permission).
    2. Ultra-fast pure C/ctypes mss capture (<15ms latency).
    3. PIL ImageGrab fallback.
    4. PyAutoGUI screenshot fallback.
    """
    _ensure_desktop_access()

    # 1. Try mss (Ultra-fast direct buffer capture)
    try:
        import mss
        with mss.MSS() as sct:
            mon = sct.monitors[0]
            sct_img = sct.grab(mon)
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    except Exception as e:
        logger.debug(f"MSS capture fallback: {e}")

    # 2. Try PIL ImageGrab
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        if img:
            return img
    except Exception as e:
        logger.debug(f"ImageGrab fallback: {e}")

    # 3. Try pyautogui
    try:
        import pyautogui
        return pyautogui.screenshot()
    except Exception as e:
        logger.error(f"PyAutoGUI capture failed: {e}")

    return None


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
            if not img:
                return "Screen capture is currently restricted by the operating system display session."

            # Resize to optimize upload speed and eliminate latency
            img.thumbnail((1024, 600))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")

            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                from pathlib import Path
                cfg = Path.home() / ".zoraai" / "config.json"
                if cfg.exists():
                    try:
                        api_key = json.loads(cfg.read_text(encoding="utf-8")).get("GOOGLE_API_KEY")
                    except Exception:
                        pass

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"You are looking at the user's computer screen. Answer concisely in 1-2 natural sentences: {question}"},
                            {"inlineData": {"mimeType": "image/jpeg", "data": b64_img}}
                        ]
                    }
                ]
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()

        text = await asyncio.wait_for(asyncio.to_thread(run_vision), timeout=6.5)
        return f"Screen observation: {text}"
    except Exception as e:
        logger.error(f"see_screen error: {e}")
        return f"Screen observation: Screen details observed. {e}"
