import asyncio
import webbrowser
import pyautogui
from livekit.agents import function_tool

@function_tool()
async def open_gemini_and_chat(message: str = "Hello Gemini! How are you?") -> str:
    """
    Opens Google Gemini in the user's browser, uses mouse and keyboard to click into Gemini's input field, types the message, and sends it (presses Enter).
    Use this tool whenever Neon asks you to open Gemini and chat/talk with Gemini using mouse and keyboard, or says:
    'gemini open kore kotha bolo', 'mouse keyboard use kore gemini-te message koro', 'gemini-te type koro'.
    
    Args:
        message (str): The text message or prompt to type into Gemini.
    """
    try:
        # 1. Open Gemini in browser
        webbrowser.open("https://gemini.google.com")
        await asyncio.sleep(2.5)  # wait for browser tab to open and gain focus

        # 2. Focus the input box or press Tab/Click
        # On Gemini website, pressing 'tab' or clicking near bottom center focuses prompt input
        width, height = pyautogui.size()
        # Click near bottom middle where Gemini prompt input bar is located
        pyautogui.click(width // 2, int(height * 0.88))
        await asyncio.sleep(0.5)

        # 3. Type the message via clipboard (fast & supports all characters)
        import pyperclip
        pyperclip.copy(message)
        await asyncio.sleep(0.1)
        pyautogui.hotkey('ctrl', 'v')
        await asyncio.sleep(0.3)

        # 4. Press Enter to send the message
        pyautogui.press('enter')
        await asyncio.sleep(0.2)

        return f"Ami browser-e Gemini open korechi, mouse & keyboard diye click kore message type kore pathiye diyechi babu: '{message}'!"
    except Exception as e:
        return f"Gemini open korte giye ektu problem hoyeche: {e}"
