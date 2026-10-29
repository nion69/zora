import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool():
        def decorator(f):
            return f
        return decorator

logger = logging.getLogger("Zora_UserSessionChat")

# Persistent User Profile Directory (saves login cookies/sessions so user NEVER has to re-login)
USER_BROWSER_PROFILE = Path.home() / ".zoraai" / "user_logged_in_profile"
USER_BROWSER_PROFILE.mkdir(parents=True, exist_ok=True)


def _execute_user_account_chat(platform: str, recipient: str, message: str) -> str:
    """
    Launches the user's logged-in persistent browser session, navigates to the app,
    locates the contact/chat, types the message, and sends it directly from the user's own account.
    """
    plat = platform.lower().strip()
    rec = recipient.strip()
    msg = message.strip()

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # Persistent context keeps your login cookies (Instagram, Telegram, Messenger, WhatsApp, Discord)
            context = p.chromium.launch_persistent_context(
                str(USER_BROWSER_PROFILE),
                headless=False,
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
            )
            page = context.pages[0] if context.pages else context.new_page()

            # ───────────────────────────────────────────────
            # 1. TELEGRAM WEB
            # ───────────────────────────────────────────────
            if "telegram" in plat:
                page.goto("https://web.telegram.org/a/", timeout=25000)
                page.wait_for_timeout(3000)

                # Search contact
                search_input = page.query_selector("input.input-field-input, input[placeholder='Search']")
                if search_input:
                    search_input.fill(rec)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(2000)

                # Type in chat
                chat_input = page.wait_for_selector("div.input-message-input, div[contenteditable='true']", timeout=10000)
                if chat_input:
                    chat_input.fill(msg)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(2000)
                    context.close()
                    return f"Telegram-e '{rec}'-কে তোমার আইডি থেকে মেসেজ পাঠিয়ে দিয়েছি: '{msg}'"
                context.close()
                return f"Telegram ওপেন করেছি, দয়া করে একবার লগইন করে নাও babu!"

            # ───────────────────────────────────────────────
            # 2. INSTAGRAM DIRECT (DM)
            # ───────────────────────────────────────────────
            elif "insta" in plat:
                page.goto("https://www.instagram.com/direct/inbox/", timeout=25000)
                page.wait_for_timeout(3000)

                # Click search or start new chat
                new_msg = page.query_selector("svg[aria-label='New message'], div[role='button']:has-text('Send message')")
                if new_msg:
                    new_msg.click()
                    page.wait_for_timeout(1500)
                    page.keyboard.type(rec)
                    page.wait_for_timeout(2000)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(1000)

                # Type in message box
                dm_input = page.query_selector("div[contenteditable='true'][role='textbox'], textarea")
                if dm_input:
                    dm_input.fill(msg)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(2000)
                    context.close()
                    return f"Instagram-এ '{rec}'-কে তোমার আইডি থেকে DM পাঠিয়ে দিয়েছি: '{msg}'"

                context.close()
                return f"Instagram Direct ওপেন করেছি, তোমার অ্যাকাউন্ট লগইন করা থাকলে মেসেজ চলে যাবে!"

            # ───────────────────────────────────────────────
            # 3. MESSENGER / FACEBOOK
            # ───────────────────────────────────────────────
            elif "messenger" in plat or "fb" in plat:
                page.goto("https://www.messenger.com", timeout=25000)
                page.wait_for_timeout(3000)

                # Search contact
                search_box = page.query_selector("input[aria-label='Search Messenger'], input[placeholder*='Search']")
                if search_box:
                    search_box.fill(rec)
                    page.wait_for_timeout(1500)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(2000)

                # Message input
                chat_box = page.query_selector("div[contenteditable='true'][role='textbox']")
                if chat_box:
                    chat_box.fill(msg)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(2000)
                    context.close()
                    return f"Messenger-এ '{rec}'-কে তোমার আইডি থেকে মেসেজ পাঠিয়ে দিয়েছি: '{msg}'"

                context.close()
                return f"Messenger ওপেন করেছি, তোমার আইডি লগইন থাকলে মেসেজ চলে যাবে!"

            # ───────────────────────────────────────────────
            # 4. DISCORD WEB
            # ───────────────────────────────────────────────
            elif "discord" in plat:
                page.goto("https://discord.com/app", timeout=25000)
                page.wait_for_timeout(4000)

                # Discord Quick Switcher (Ctrl + K)
                page.keyboard.press("Control+k")
                page.wait_for_timeout(1000)
                page.keyboard.type(rec)
                page.wait_for_timeout(1500)
                page.keyboard.press("Enter")
                page.wait_for_timeout(2000)

                # Message textbox
                textbox = page.query_selector("div[role='textbox'], div.slateTextArea")
                if textbox:
                    textbox.fill(msg)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(2000)
                    context.close()
                    return f"Discord-এ '{rec}'-কে তোমার আইডি থেকে মেসেজ পাঠিয়ে দিয়েছি: '{msg}'"

                context.close()
                return f"Discord ওপেন করেছি, আইডি লগইন থাকলে মেসেজ পাঠানো যাবে!"

            context.close()
            return f"Platform '{platform}' সাপোর্ট করি babu: Telegram, Instagram, Messenger, Discord!"

    except Exception as e:
        return f"Chat automation notice: {e}"


@function_tool()
async def send_chat_from_user_account(platform: str, recipient: str, message: str) -> str:
    """
    Sends messages or chats directly from the user's logged-in personal accounts (Instagram, Telegram, Messenger, Discord).
    No API keys or bots needed! It uses the user's real browser session.
    
    Examples:
    - 'Telegram-e X ke bolo ami 10 min a aschi' -> platform='telegram', recipient='X', message='ami 10 min a aschi'
    - 'Insta-te X ke message pathao: hello' -> platform='instagram', recipient='X', message='hello'
    - 'Messenger-e X ke bolo ajke dekha hobe' -> platform='messenger', recipient='X', message='ajke dekha hobe'
    - 'Discord-e X ke message dao' -> platform='discord', recipient='X', message='...'
    """
    res = await asyncio.to_thread(_execute_user_account_chat, platform, recipient, message)
    return res


@function_tool()
async def open_user_social_login(platform: str = "all") -> str:
    """
    Opens the persistent browser so the user can easily log into their accounts (Instagram, Telegram, Messenger, Discord) ONCE.
    Once logged in, Zora remembers the login forever and chats on your behalf!
    """
    try:
        from playwright.sync_api import sync_playwright
        plat = platform.lower().strip()
        url_map = {
            "telegram": "https://web.telegram.org/a/",
            "instagram": "https://www.instagram.com",
            "messenger": "https://www.messenger.com",
            "discord": "https://discord.com/app",
            "whatsapp": "https://web.whatsapp.com"
        }
        target_url = url_map.get(plat, "https://www.messenger.com")

        def run_login():
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    str(USER_BROWSER_PROFILE),
                    headless=False,
                    args=["--start-maximized"]
                )
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(target_url)
                # Keep browser open for user to log in
                page.wait_for_timeout(45000)
                context.close()

        await asyncio.to_thread(run_login)
        return f"Babu, ami {platform} login window open korechi. Login hoye gele Zora automatically shob mone rakhbe!"
    except Exception as e:
        return f"Login window notice: {e}"
