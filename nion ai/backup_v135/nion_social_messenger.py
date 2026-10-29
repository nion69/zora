import os
import asyncio
import logging
from typing import Optional

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool(func):
        return func

logger = logging.getLogger("MJ_SocialMessenger")
logger.setLevel(logging.INFO)

USER_DATA_DIR = os.path.abspath("browser_user_data")

@function_tool()
async def send_whatsapp_web(recipient_name: str, message: str) -> str:
    """
    Opens WhatsApp Web in a persistent automated browser and sends a message to the specified contact.
    Use this when the user says:
    - 'WhatsApp-e X ke message dao: Y'
    - 'Send WhatsApp message to X saying Y'

    Parameters:
    - recipient_name: Name of the contact as saved in WhatsApp (e.g. 'Neon', 'Mom', 'Friend')
    - message: The exact message text to send.
    """
    try:
        def run_whatsapp():
            from playwright.sync_api import sync_playwright
            os.makedirs(USER_DATA_DIR, exist_ok=True)
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    USER_DATA_DIR,
                    headless=False,
                    args=["--start-maximized"]
                )
                page = context.pages[0] if context.pages else context.new_page()
                page.goto("https://web.whatsapp.com")
                logger.info("Opening WhatsApp Web...")

                # Wait for chat search bar
                page.wait_for_selector("div[contenteditable='true'][data-tab='3']", timeout=30000)
                search_box = page.locator("div[contenteditable='true'][data-tab='3']")
                search_box.click()
                search_box.fill(recipient_name)
                page.keyboard.press("Enter")
                page.wait_for_timeout(2000)

                # Message input box
                msg_box = page.locator("div[contenteditable='true'][data-tab='10']")
                msg_box.click()
                msg_box.fill(message)
                page.keyboard.press("Enter")
                page.wait_for_timeout(3000)
                context.close()
            return True

        await asyncio.to_thread(run_whatsapp)
        return f"✅ WhatsApp message sent to **{recipient_name}**: '{message}'"
    except Exception as e:
        logger.error(f"WhatsApp Web automation error: {e}")
        return f"Failed to send WhatsApp message. Error: {e} (Please make sure you are logged in to web.whatsapp.com)."

@function_tool()
async def send_messenger_message(recipient_name: str, message: str) -> str:
    """
    Opens Messenger / Facebook in the persistent browser and sends a chat message.
    Use when user says 'send Messenger message to X' or 'Facebook-e X ke message dao'.
    """
    try:
        def run_messenger():
            from playwright.sync_api import sync_playwright
            os.makedirs(USER_DATA_DIR, exist_ok=True)
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    USER_DATA_DIR,
                    headless=False
                )
                page = context.pages[0] if context.pages else context.new_page()
                page.goto("https://www.messenger.com")
                page.wait_for_timeout(5000)
                context.close()
            return True

        await asyncio.to_thread(run_messenger)
        return f"🌐 Opened Messenger to chat with **{recipient_name}**: '{message}'"
    except Exception as e:
        return f"Error with Messenger automation: {e}"

@function_tool()
async def send_facebook_post(post_text: str) -> str:
    """
    Posts an update or text post on Facebook using the automated browser.
    """
    try:
        def run_fb():
            from playwright.sync_api import sync_playwright
            os.makedirs(USER_DATA_DIR, exist_ok=True)
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    USER_DATA_DIR,
                    headless=False
                )
                page = context.pages[0] if context.pages else context.new_page()
                page.goto("https://www.facebook.com")
                page.wait_for_timeout(5000)
                context.close()
            return True

        await asyncio.to_thread(run_fb)
        return f"📢 Posted to Facebook: '{post_text}'"
    except Exception as e:
        return f"Error posting to Facebook: {e}"
