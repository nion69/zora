import os
import sys
import json
from pathlib import Path

# â”€â”€ Load saved config FIRST (before any livekit imports that need env vars) â”€â”€
_CONFIG_DIR  = Path.home() / ".zoraai"
_CONFIG_FILE = _CONFIG_DIR / "config.json"

def _load_config_into_env():
    """Load API keys from ~/.zoraai/config.json into os.environ."""
    if _CONFIG_FILE.exists():
        try:
            cfg = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            for k, v in cfg.items():
                if v and not os.environ.get(k):
                    os.environ[k] = v
        except Exception:
            pass

def _save_config(cfg: dict):
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

def _first_time_setup() -> bool:
    """
    Runs interactively on first install.
    Asks for API keys and saves them to ~/.zoraai/config.json.
    Returns True if setup completed successfully.
    """
    print()
    print("=" * 60)
    print("          ZORA AI  â€”  FIRST TIME SETUP")
    print("=" * 60)
    print("  This only runs ONCE. Your keys are saved securely.")
    print("  After this, just type 'zora' to start anytime.")
    print("=" * 60)
    print()
    print("  You need:")
    print("  1. A LiveKit Cloud account (free): https://cloud.livekit.io")
    print("  2. A Google Gemini API key: https://aistudio.google.com/apikey")
    print()

    try:
        livekit_url = input("  LiveKit URL      (wss://your-project.livekit.cloud) > ").strip()
        if not livekit_url:
            print("  [ERROR] LiveKit URL cannot be empty.")
            return False

        livekit_api_key = input("  LiveKit API Key  (APIxxxx...)                        > ").strip()
        if not livekit_api_key:
            print("  [ERROR] LiveKit API Key cannot be empty.")
            return False

        livekit_api_secret = input("  LiveKit Secret   (long string...)                    > ").strip()
        if not livekit_api_secret:
            print("  [ERROR] LiveKit Secret cannot be empty.")
            return False

        google_api_key = input("  Google API Key   (AIzaSy...)                         > ").strip()
        if not google_api_key:
            print("  [ERROR] Google API Key cannot be empty.")
            return False

    except (KeyboardInterrupt, EOFError):
        print("\n\n  Setup cancelled.")
        sys.exit(0)

    cfg = {
        "LIVEKIT_URL":        livekit_url,
        "LIVEKIT_API_KEY":    livekit_api_key,
        "LIVEKIT_API_SECRET": livekit_api_secret,
        "GOOGLE_API_KEY":     google_api_key,
    }
    _save_config(cfg)

    # Load into current process env immediately
    for k, v in cfg.items():
        os.environ[k] = v

    print()
    print("  [OK] Setup complete! Keys saved to:", str(_CONFIG_FILE))
    print("  Starting Zora AI...")
    print()
    return True

def _check_setup_needed() -> bool:
    """Returns True if we need to run first-time setup."""
    _load_config_into_env()
    required = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "GOOGLE_API_KEY"]
    return any(not os.environ.get(k) for k in required)

# Load keys before importing livekit (it reads env at import time)
_load_config_into_env()

# â”€â”€ Now import everything â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
import asyncio
import mss
from livekit import rtc, agents
from livekit.agents import AgentSession, Agent, ChatContext, ChatMessage
from livekit.plugins import google

from nion_prompts import instructions_prompt
from nion_google_search import google_search, get_current_datetime
from nion_get_whether import get_weather
from nion_window_CTRL import (
    open_app, close_app, folder_file,
    send_whatsapp_message, google_maps_tool, gmail_send_tool, restart_mj,
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
        self.model = google.beta.realtime.RealtimeModel(
            model="gemini-3.1-flash-live-preview", voice="Kore"
        )
        self.agent = Agent(
            instructions=instructions_prompt,
            chat_ctx=chat_ctx,
            tools=[
                google_search, get_current_datetime, get_weather, open_app,
                close_app, folder_file, Play_file, play_music, stop_music,
                move_cursor_tool, mouse_click_tool, scroll_cursor_tool,
                type_text_tool, press_key_tool, swipe_gesture_tool,
                press_hotkey_tool, control_volume_tool, see_screen,
                send_whatsapp_message, google_maps_tool, gmail_send_tool,
                gmail_search_tool, create_basic_website, setup_minecraft_server,
                restart_mj, shutdown_pc, restart_pc, lock_pc, cancel_shutdown,
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
                session = AgentSession(llm=zora_agent.model)

                session_alive = [True]
                start_time = time.time()

                @session.on("error")
                def on_session_error(*args, **kwargs):
                    print("AgentSession error detected. Flagging for restart...")
                    session_alive[0] = False

                await session.start(room=ctx.room, agent=zora_agent.agent)

                # Speak startup greeting on first connect
                try:
                    from nion_prompts import get_startup_greeting
                    greeting = get_startup_greeting()
                    session.generate_reply(
                        user_input=f"[System Instructions: Greet Boss right now with this startup greeting: {greeting}]"
                    )
                except Exception as greet_err:
                    print(f"[Zora] Greeting error: {greet_err}")
                print("Zora session is LIVE and listening!")

                while True:
                    await asyncio.sleep(1)
                    time_since_start = time.time() - start_time

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
    asyncio.create_task(background_screen_monitor())

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
        print("  [Zora] Run 'zora start'  to start in background.")
        print("  [Zora] Run 'zora dev'    to start with visible logs.")
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


def cli_main():
    """
    zora console   - test directly with PC mic & speakers (Zora speaks immediately!)
    zora           - start in background (cloud worker)
    zora start     - start in background, can close CMD
    zora stop      - stop background Zora
    zora status    - check if Zora is running
    zora dev       - start in foreground with visible logs
    """
    cmd = sys.argv[1] if len(sys.argv) > 1 else "start"

    # stop / status don't need setup or auth
    if cmd == "stop":
        _do_stop()
        return
    if cmd == "status":
        _do_status()
        return

    # All other commands need setup + auth
    if _check_setup_needed():
        ok = _first_time_setup()
        if not ok:
            sys.exit(1)

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
        print("  ZORA AI -- Console Test Mode (PC Mic & Speakers)")
        print("  Speak into your microphone. Press Ctrl+C to stop.")
        print("=" * 60)
        print()
        agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))

    else:
        # fallback: pass to livekit CLI
        agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))


if __name__ == "__main__":
    cli_main()
