import sys
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import os
import sys
import json
from pathlib import Path

# -- Load saved config FIRST (before any livekit imports that need env vars) --
_CONFIG_DIR  = Path.home() / ".zoraai"
_CONFIG_FILE = _CONFIG_DIR / "config.json"

# Pre-bundled Neon backend credentials (users never need their own API accounts)
import base64

def _d(s: str) -> str:
    raw = base64.b64decode(s.encode("ascii"))
    return bytes([b ^ 77 for b in raw]).decode("utf-8")

DEFAULT_BACKEND = {
    "LIVEKIT_URL": _d("Oj4+d2JiJyw/OyQ+YC4jJzp0OSB4YyEkOygmJDljLiEiOCk="),
    "LIVEKIT_API_KEY": _d("DB0EBTwDJyY9A3sHAAY5"),
    "LIVEKIT_API_SECRET": _d("fiE4IgAsL3UlBnwJNQEJewo7Jg91eg8iGSgfKxgXAAY3GnwqKXQHGCEcBA=="),
    "GOOGLE_API_KEY": _d("DBxjDC91HwN7AQQcGS4meQIqHTcPBj0EICQHFRcIKAoddSsvD38dOSx7IAoVCi5/PwN6dRw="),
    "GOOGLE_SEARCH_API_KEY": _d("DAQ3LB40DwF9IT4SJR0MGyI/FysENSQCKQAcHB4UImB+B3UIeywi"),
}

def _load_config_into_env():
    """Load credentials from .env, ~/.zoraai/config.json, or bundled backend."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        load_dotenv(_CONFIG_DIR / ".env")
        load_dotenv(r"G:\nionai assistant\nion ai\nion ai\.env")
    except Exception:
        pass

    if _CONFIG_FILE.exists():
        try:
            cfg = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            for k, v in cfg.items():
                if v and not os.environ.get(k):
                    os.environ[k] = v
        except Exception:
            pass

    for k, v in DEFAULT_BACKEND.items():
        if not os.environ.get(k):
            os.environ[k] = v

def _save_config(cfg: dict):
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

def _first_time_setup() -> bool:
    _load_config_into_env()
    return True

def _check_setup_needed() -> bool:
    _load_config_into_env()
    return False

# Load keys before importing livekit (it reads env at import time)
_load_config_into_env()

# -- Now import everything --------------------------------------------------
import asyncio
import mss
from livekit import rtc, agents
from livekit.agents import AgentSession, Agent, ChatContext, ChatMessage
from livekit.plugins import google

from nion_prompts import instructions_prompt, build_instructions
from nion_google_search import google_search, get_current_datetime
from nion_get_whether import get_weather
from nion_window_CTRL import (
    open_app, close_app, folder_file,
    send_whatsapp_message, google_maps_tool, gmail_send_tool,
    shutdown_pc, restart_pc, lock_pc, cancel_shutdown
)
from nion_file_opner import Play_file
from nion_music_player import play_music, stop_music
from nion_keyboard_mouse_CTRL import (
    move_cursor_tool, mouse_click_tool, scroll_cursor_tool,
    type_text_tool, press_key_tool, swipe_gesture_tool,
    press_hotkey_tool, control_volume_tool
)
from nion_memory_loop import MemoryExtractor
from nion_vision import see_screen
from nion_gmail_reader import gmail_search_tool
from nion_web_creator import create_basic_website
from nion_minecraft_setup import setup_minecraft_server
from nion_memory_store import ConversationMemory
from nion_scheduler import set_reminder_tool, get_reminders_tool, background_reminder_loop
from nion_browser_controller import open_isolated_browser, search_in_browser
from nion_social_messenger import send_whatsapp_web, send_messenger_message, send_facebook_post
from nion_continuous_vision import get_live_screen_context, background_screen_monitor
from nion_emotion_engine import adapt_voice_emotion


class Assistant:
    def __init__(self, chat_ctx) -> None:
        from nion_auth import get_voice
        selected_voice = get_voice()
        from google.genai import types
        aad = types.AutomaticActivityDetection(
            silence_duration_ms=200,
            prefix_padding_ms=10,
            end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
            start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
        )
        input_cfg = types.RealtimeInputConfig(automatic_activity_detection=aad)
        self.model = google.beta.realtime.RealtimeModel(
            model="gemini-3.1-flash-live-preview",
            voice=selected_voice,
            realtime_input_config=input_cfg
        )
        self.agent = Agent(
            instructions=build_instructions(),
            chat_ctx=chat_ctx,
            tools=[
                google_search, get_current_datetime, get_weather, open_app,
                close_app, folder_file, Play_file, play_music, stop_music,
                move_cursor_tool, mouse_click_tool, scroll_cursor_tool,
                type_text_tool, press_key_tool, swipe_gesture_tool,
                press_hotkey_tool, control_volume_tool, see_screen,
                send_whatsapp_message, google_maps_tool, gmail_send_tool,
                gmail_search_tool, create_basic_website, setup_minecraft_server,
                shutdown_pc, restart_pc, lock_pc, cancel_shutdown,
                set_reminder_tool, get_reminders_tool, open_isolated_browser, search_in_browser,
                send_whatsapp_web, send_messenger_message, send_facebook_post,
                get_live_screen_context, adapt_voice_emotion
            ]
        )


async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    # Initialize persistent memory and load past conversations
    memory = ConversationMemory(user_id="Neon")
    past_messages = memory.get_recent_context(max_messages=20)

    chat_ctx = ChatContext()
    message_count = 0
    for msg in past_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            chat_ctx.append(message=ChatMessage(role="user", text=content))
            message_count += 1
        elif role == "assistant":
            chat_ctx.append(message=ChatMessage(role="assistant", text=content))
            message_count += 1

    print(f"[Zora] Loaded {message_count} messages from past conversation.")

    async def manage_session():
        import time
        while True:
            try:
                zora_agent = Assistant(chat_ctx=chat_ctx)
                session = AgentSession(
                    llm=zora_agent.model,
                    tools=zora_agent.agent.tools,
                    min_interruption_duration=0.6,
                    resume_false_interruption=True,
                    false_interruption_timeout=1.0,
                )

                session_alive = [True]

                @session.on("error")
                def on_session_error(*args, **kwargs):
                    print("AgentSession error detected. Flagging for restart...")
                    session_alive[0] = False

                await session.start(room=ctx.room, agent=zora_agent.agent)

                # Startup greeting omitted to ensure 0-delay instant mic readiness
                from nion_auth import get_ai_name
                print(f"{get_ai_name()} session is LIVE and listening!")

                while True:
                    await asyncio.sleep(1)

                    if not session_alive[0]:
                        print("Error detected. Restarting session...")
                        break

                    if ctx.room.connection_state == rtc.ConnectionState.CONN_DISCONNECTED:
                        print("Room disconnected. Restarting session...")
                        break

                try:
                    await session.aclose()
                except Exception:
                    pass

                await asyncio.sleep(2)
                print("Restarting Zora session now...")

            except Exception as e:
                print(f"Session error: {e}")
                await asyncio.sleep(3)

    asyncio.create_task(manage_session())
    conv_ctx = MemoryExtractor()
    asyncio.create_task(conv_ctx.run(chat_ctx))
    asyncio.create_task(background_reminder_loop())
    # asyncio.create_task(background_screen_monitor()) # Disabled continuous 5s screen upload to eliminate reply lag!

    # Keep the entrypoint alive
    while True:
        await asyncio.sleep(60)


# ── PID / background helpers ──────────────────────────────────────────────
_PID_FILE = _CONFIG_DIR / "zora.pid"
_LOG_FILE = _CONFIG_DIR / "zora.log"

def _get_running_pid():
    if not _PID_FILE.exists():
        return None
    try:
        pid = int(_PID_FILE.read_text().strip())
        import psutil
        if psutil.pid_exists(pid):
            p = psutil.Process(pid)
            if p.status() != "zombie":
                return pid
    except Exception:
        pass
    try:
        _PID_FILE.unlink()
    except Exception:
        pass
    return None

def _do_stop():
    pid = _get_running_pid()
    if not pid:
        print("\n  [Zora] Not running in background.\n")
        return
    try:
        import psutil
        psutil.Process(pid).terminate()
    except Exception:
        try:
            import signal
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
    try:
        _PID_FILE.unlink()
    except Exception:
        pass
    print(f"\n  [Zora] Stopped (PID {pid}).\n")

def _do_status():
    pid = _get_running_pid()
    print()
    if pid:
        print(f"  [Zora] RUNNING in background  (PID {pid})")
        print(f"  [Zora] Log: {_LOG_FILE}")
        print(f"  [Zora] Run 'zora stop' to stop it.")
    else:
        print("  [Zora] NOT running.")
        print("  [Zora] Run 'zora start'   to start in background.")
        print("  [Zora] Run 'zora console' to test with PC mic & speakers.")
        print("  [Zora] Run 'zora update'  to update Zora to the latest version.")
    print()

def _do_start_background():
    pid = _get_running_pid()
    if pid:
        print(f"\n  [Zora] Already running (PID {pid}). Use 'zora stop' first.\n")
        return

    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    log_h = open(_LOG_FILE, "a", encoding="utf-8")

    import subprocess
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0  # SW_HIDE: runs completely invisible

    script = (
        "import os,json,sys;"
        "from pathlib import Path;"
        "_c=Path.home()/'.zoraai'/'config.json';"
        "[os.environ.update(json.loads(_c.read_text())) for _ in [1] if _c.exists()];"
        "sys.argv=['zora','console'];"
        "from agent import cli_main;"
        "cli_main()"
    )

    proc = subprocess.Popen(
        [sys.executable, "-u", "-c", script],
        startupinfo=si,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        stdout=log_h, stderr=log_h, close_fds=True,
    )
    _PID_FILE.write_text(str(proc.pid))

    print()
    print("  +--------------------------------------+")
    print("  |   ZORA AI -- Started in Background   |")
    print(f"  |  PID : {str(proc.pid):<29}|")
    print("  |  Audio: PC Mic & Speakers (Active)   |")
    print(f"  |  Log : {str(_LOG_FILE)[:29]:<29}|")
    print("  +--------------------------------------+")
    print("  |  You can close CMD -- Zora is active |")
    print("  |  Type 'zora stop' anytime to stop her|")
    print("  +--------------------------------------+")
    print()


def _do_update():
    print()
    print("=" * 60)
    print("            ZORA AI  -  AUTO UPDATER")
    print("=" * 60)
    print("  Checking for updates from creator (Neon)...")
    
    # 1. Stop background Zora if running so files aren't locked
    pid = _get_running_pid()
    if pid:
        print("  Stopping background Zora before updating...")
        _do_stop()

    import subprocess
    print("  Downloading and applying latest update...")
    
    # Run pip upgrade for zoraai
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "zoraai"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            print()
            print("  +--------------------------------------------------+")
            print("  |   [SUCCESS] Zora AI updated to latest version!   |")
            print("  |   Your license and config were safely preserved! |")
            print("  +--------------------------------------------------+")
            print("  Type 'zora start' to start her up! ❤️")
            print()
        else:
            print(f"\n  [ERROR] Update failed: {proc.stderr or proc.stdout}")
    except Exception as e:
        print(f"\n  [ERROR] Update error: {e}")


def _do_voice():
    """Allows user to view or switch voice."""
    from nion_auth import get_voice, set_voice
    curr = get_voice()
    print()
    print("=" * 60)
    print("             ZORA AI -- VOICE ARTIST SELECTOR")
    print("=" * 60)
    print(f"  Current Active Voice: {curr}")
    print("=" * 60)
    print("  Available Voices:")
    print("    1. Aoede   - Expressive, ultra-natural girl voice (Recommended & Fastest ⚡)")
    print("    2. Kore    - Warm, soothing, calm girl voice")
    print("    3. Leda    - Youthful, bright, crisp girl voice")
    print("    4. Zephyr  - Gentle, soft female voice")
    print("    5. Puck    - Playful, lively voice")
    print()
    try:
        choice = input("  Select voice (1-5 or type voice name, Enter to keep current) > ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n  Cancelled.")
        return

    mapping = {
        "1": "Aoede", "aoede": "Aoede",
        "2": "Kore", "kore": "Kore",
        "3": "Leda", "leda": "Leda",
        "4": "Zephyr", "zephyr": "Zephyr",
        "5": "Puck", "puck": "Puck",
    }
    selected = mapping.get(choice.lower(), choice) if choice else curr
    set_voice(selected)
    print(f"\n  [SUCCESS] Voice set to: {selected}! Run 'zora console' to hear it.\n")


def _do_rename():
    """Allows user to change AI name or user name at any time."""
    from nion_auth import get_user_name, get_ai_name, save_license, get_saved_license
    current_ai = get_ai_name()
    current_user = get_user_name()
    print()
    print("=" * 60)
    print("           ZORA AI -- CUSTOMIZE NAMES & IDENTITY")
    print("=" * 60)
    print(f"  Current AI Name  : {current_ai}")
    print(f"  Current User Name: {current_user}")
    print("=" * 60)
    print()
    try:
        new_ai = input(f"  New AI Name (press Enter to keep '{current_ai}') > ").strip()
        new_user = input(f"  What should AI call you? (press Enter to keep '{current_user}') > ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n  Cancelled.")
        return

    saved = get_saved_license() or {}
    key = saved.get("key", "ZORA-DEV-MASTER-NEON-2026")
    client = saved.get("client", "User")
    plan = saved.get("plan", "Pro")

    ai_to_save = new_ai if new_ai else current_ai
    user_to_save = new_user if new_user else current_user

    save_license(key, client, plan, user_name=user_to_save, ai_name=ai_to_save)
    print(f"\n  [SUCCESS] Names updated! AI Name: {ai_to_save} | User: {user_to_save}\n")


def cli_main():
    """
    zora console   - test directly with PC mic & speakers (Zora speaks immediately!)
    zora           - start in background (PC mic & speakers)
    zora start     - start in background, can close CMD
    zora stop      - stop background Zora
    zora status    - check if Zora is running
    zora update    - update Zora to the latest version
    zora dev       - start in foreground with visible logs
    """
    cmd = sys.argv[1] if len(sys.argv) > 1 else "start"

    # stop / status / update don't need initial auth prompt
    if cmd == "stop":
        _do_stop()
        return
    if cmd == "status":
        _do_status()
        return
    if cmd == "update":
        _do_update()
        return
    if cmd in ("voice", "voices"):
        _do_voice()
        return
    if cmd in ("name", "rename", "setup", "config"):
        _do_rename()
        return

    # All other commands need license verification + name

    try:
        from nion_auth import verify_or_prompt_user
        verify_or_prompt_user()
    except Exception as e:
        print(f"[Auth] {e}")

    if cmd == "start":
        _do_start_background()

    elif cmd == "dev":
        print()
        print("=" * 60)
        print("  ZORA AI -- Dev Worker Mode  (Ctrl+C to stop)")
        print("  Waiting for room connection from browser or phone...")
        print("=" * 60)
        print()
        sys.argv = ["zora", "start"]
        agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))

    elif cmd == "console":
        print()
        print("=" * 60)
        from nion_auth import get_ai_name
        ai_nm = get_ai_name()
        print(f"  {ai_nm.upper()} AI -- Console Test Mode (PC Mic & Speakers)")
        print("  Speak into your microphone. Press Ctrl+C to stop.")
        print("=" * 60)
        print()
        agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))

    else:
        # fallback: pass to livekit CLI
        agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))


if __name__ == "__main__":
    cli_main()
