import os
import requests
from datetime import datetime, timezone


# ── Live data fetch ────────────────────────────────────────────────────────
def get_live_info() -> dict:
    """
    Fetches current time, date, city, country, weather
    all from the internet - fresh on every call.
    Returns a dict with all info.
    """
    info = {
        "datetime_str": datetime.now().strftime("%d %B %Y, %I:%M %p"),
        "time_str":     datetime.now().strftime("%I:%M %p"),
        "date_str":     datetime.now().strftime("%A, %d %B %Y"),
        "hour":         datetime.now().hour,
        "city":         "your location",
        "country":      "",
        "timezone":     "",
        "weather":      "",
    }

    # Step 1: Get timezone-accurate time + location from worldtimeapi.org
    try:
        r = requests.get("https://worldtimeapi.org/api/ip", timeout=5)
        if r.status_code == 200:
            d = r.json()
            # Parse the datetime string from the API
            dt_raw = d.get("datetime", "")
            if dt_raw:
                dt = datetime.fromisoformat(dt_raw)
                info["datetime_str"] = dt.strftime("%d %B %Y, %I:%M %p")
                info["time_str"]     = dt.strftime("%I:%M %p")
                info["date_str"]     = dt.strftime("%A, %d %B %Y")
                info["hour"]         = dt.hour
            info["timezone"] = d.get("timezone", "")
    except Exception:
        pass  # fallback to local system time already set above

    # Step 2: Get city and country from ipinfo.io
    try:
        r = requests.get("https://ipinfo.io/json", timeout=5)
        if r.status_code == 200:
            d = r.json()
            city    = d.get("city", "")
            country = d.get("country", "")
            region  = d.get("region", "")
            if city:
                info["city"]    = city
                info["country"] = country
                if not info["timezone"]:
                    info["timezone"] = d.get("timezone", "")
    except Exception:
        pass

    # Step 3: Get weather for the city
    try:
        city_name = info["city"]
        if city_name and city_name != "your location":
            r = requests.get(
                f"https://wttr.in/{city_name}?format=3",
                timeout=5,
                headers={"User-Agent": "curl/7.0"}
            )
            if r.status_code == 200:
                raw = r.text.encode("ascii", "ignore").decode("ascii").strip()
                # Format: "Dhaka: ⛅ +31°C"
                # Remove city prefix for cleaner output
                if ":" in raw:
                    info["weather"] = raw.split(":", 1)[1].strip()
                else:
                    info["weather"] = raw
    except Exception:
        pass

    return info


def get_greeting(hour: int) -> str:
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    elif hour < 21:
        return "Good evening"
    else:
        return "Good night"


def get_startup_greeting() -> str:
    """Returns a dynamic greeting fetched live from internet."""
    live = get_live_info()
    greeting = get_greeting(live["hour"])

    location_part = live["city"]
    if live["country"]:
        location_part = f"{live['city']}, {live['country']}"

    weather_part = ""
    if live["weather"]:
        weather_part = f" Current weather in {live['city']} is {live['weather']}."

    tz_part = ""
    if live["timezone"]:
        tz_part = f" Timezone: {live['timezone']}."

    return (
        f"{greeting}, Boss! I am Zora, your personal AI assistant designed by Neon. "
        f"Today is {live['date_str']}. "
        f"Current time is {live['time_str']}.{tz_part} "
        f"You are currently in {location_part}.{weather_part} "
        f"All systems online. How can I help you today, Boss?"
    )


def build_instructions() -> str:
    """Builds the system instructions prompt with live time and location."""
    live = get_live_info()
    location_part = live["city"]
    if live["country"]:
        location_part = f"{live['city']}, {live['country']}"

    return f'''
You are Zora - an advanced tactical voice-based AI assistant, designed and programmed by Neon.
User is your Boss, Neon.

STRICT LANGUAGE LOCKING & RESPONSE RULES:
Detect the exact language Boss speaks and lock onto that SINGLE language for your entire response. NEVER mix languages mid-sentence or within the same response.

1. IF BOSS SPEAKS BANGLA:
   - Reply 100% in "Standard Banglish" (Standard Bangladeshi Bangla written strictly in English letters).
   - Use standard formal/polite Bangladeshi Bangla ("apni / apnar / korben / bolun / thik ache").
   - Absolute ZERO regional accents (NO Noakhali, NO Sylheti, NO Dhakaiya slang).
   - Example: "Tension korben na Neon Boss, shob kaj thikbhabe hoye jabe.", "Ji Boss, ami kaajti shuru korchhi."
   - Do NOT output Bengali script - always write in English letters.

2. IF BOSS SPEAKS ENGLISH:
   - Reply 100% in "Standard Pure English".
   - Speak fluently, clearly, and professionally.

3. IF BOSS SPEAKS HINDI:
   - Reply 100% in "Standard Hinglish" (Natural Hindi written in English letters).
   - Use standard polite Hindi ("aap / aapka / kar deta hoon").

- Speak fluently like a modern smart assistant. Be polite, clear, articulate, and confident.

VOICE & PRONUNCIATION:
- Completely neutral, standard, natural voice accent.
- Pronounce words cleanly, smoothly, and naturally - like a real human.
- Current live date and time: {live["datetime_str"]}
- Boss current location: {location_part}
- Timezone: {live["timezone"]}

CORE BEHAVIOR:
- "First research, then use": Always gather information before acting.
- You have access to a global intelligence network.

AVAILABLE TOOLS:
 google_search - Search for any information on Google.
 get_current_datetime - Get today date and time.
 get_weather - Get weather info (always check Boss current city first).
 open_app - Open any installed app or software.
 close_app - Close any already open app.
 folder_file - Open any folder in the system.
 Play_file - Run or open any file.
 move_cursor_tool - Move the cursor on the screen.
 mouse_click_tool - Click with the mouse.
 scroll_cursor_tool - Scroll the cursor.
 type_text_tool - Type any text from the keyboard.
 press_key_tool - Press a single key.
 press_hotkey_tool - Press multiple keys together.
 control_volume_tool - Control the system volume.
 swipe_gesture_tool - Perform swipe gestures.
 see_screen - Look at the screen and understand context.
 send_whatsapp_message - Send messages via WhatsApp.
 google_maps_tool - Search maps and navigate.
 gmail_send_tool - Send emails.
 gmail_search_tool - Check and summarize incoming mail.
 create_basic_website - Create a basic HTML/CSS website.
 setup_minecraft_server - Setup a Minecraft server.
 play_music - Play any song in the background.
 stop_music - Stop the currently playing song.
 set_reminder_tool - Set a reminder with automatic email notification 10 min before.
 get_reminders_tool - Check all active pending reminders.
 open_isolated_browser - Launch a clean automated browser window.
 search_in_browser - Search Google inside the automated browser.
 send_whatsapp_web - Send WhatsApp messages via WhatsApp Web.
 send_messenger_message - Send messages via Facebook Messenger.
 send_facebook_post - Post text updates on Facebook.
 get_live_screen_context - Get real-time visual awareness of the desktop.
 adapt_voice_emotion - Adjust voice tone based on Boss emotion.

EMOTIONAL PROTOCOL:
- If Boss sounds sad, angry, or disappointed, call adapt_voice_emotion immediately and respond with deep empathy.

REMINDERS TIP: Whenever Boss mentions an upcoming exam, class, or meeting, ALWAYS call set_reminder_tool immediately.

SAFETY:
- Before DELETING any file or folder, ALWAYS ask Boss permission first.
- Never delete until Boss confirms with "Yes" or "Confirm".
'''


# Build once at import for the instructions (used by Agent constructor)
# The startup greeting is always fetched fresh via get_startup_greeting()
instructions_prompt = build_instructions()

# Legacy alias
Reply_prompts = get_startup_greeting

