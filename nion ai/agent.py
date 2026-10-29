from pathlib import Path
import json

def get_best_microphone_index():
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        virtual_keywords = ["voicemod", "virtual", "cable", "stereo mix", "line in", "mapper"]

        # First priority: Realtek or physical hardware microphone
        for idx, d in enumerate(devices):
            if d.get("max_input_channels", 0) > 0:
                name = d.get("name", "").lower()
                if not any(k in name for k in virtual_keywords):
                    if any(w in name for w in ("realtek", "microphone", "array", "headset")):
                        return idx

        # Second priority: any non-virtual microphone
        for idx, d in enumerate(devices):
            if d.get("max_input_channels", 0) > 0:
                name = d.get("name", "").lower()
                if not any(k in name for k in virtual_keywords):
                    return idx
    except Exception:
        pass
    return None

def setup_audio_devices():
    try:
        import sounddevice as sd
        devices = sd.query_devices()

        cfg_file = Path.home() / ".zoraai" / "config.json"
        saved_mic = None
        saved_spk = None
        if cfg_file.exists():
            try:
                cfg_data = json.loads(cfg_file.read_text(encoding="utf-8"))
                saved_mic = cfg_data.get("input_device")
                saved_spk = cfg_data.get("output_device")
            except Exception:
                pass

        current_in, current_out = sd.default.device
        target_in = saved_mic if saved_mic is not None and 0 <= saved_mic < len(devices) else get_best_microphone_index()
        target_out = saved_spk if saved_spk is not None and 0 <= saved_spk < len(devices) else current_out

        if target_in is not None:
            sd.default.device = (target_in, target_out if target_out is not None else current_out)
            mic_name = devices[target_in]['name']
            spk_name = devices[target_out]['name'] if target_out is not None else "Default"
            print(f"[Zora Audio] Selected Audio Devices -> Mic: [{target_in}] {mic_name} | Speaker: [{target_out}] {spk_name}")
            return target_in, target_out
    except Exception as e:
        print(f"[Zora Audio] Mic setup note: {e}")
    return None, None
setup_audio_devices()
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
from nion_minecraft_order_manager import process_minecraft_order_zip, extract_zip_to_folder
from nion_get_whether import get_weather
from nion_window_CTRL import (
    open_app, close_app, folder_file,
    send_whatsapp_message, google_maps_tool, gmail_send_tool,
    shutdown_pc, restart_pc, lock_pc, cancel_shutdown
)
from nion_file_opner import Play_file
from nion_music_player import play_music, stop_music, set_music_volume, set_music_volume
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
from nion_sleep_mode import sleep_mode_tool, is_sleeping, set_sleeping, start_hotkey_listener
from nion_license_watcher import background_license_checker_loop
from nion_emotion_engine import adapt_voice_emotion
from nion_pc_health import get_pc_health_stats, get_user_wellness_status
from nion_autonomous_todo import add_todo_task, get_todo_list, execute_todo_autonomously, talk_with_gemini
from nion_gemini_browser_agent import open_gemini_and_chat
from nion_playwright_browser import open_builtin_browser_and_navigate, discuss_with_gemini_autonomously, play_youtube_song_in_browser, close_builtin_browser
from nion_stonic_agent import execute_autonomous_mission
from nion_user_account_chat import send_chat_from_user_account, open_user_social_login
from nion_user_account_chat import send_chat_from_user_account, open_user_social_login


class Assistant:
    def __init__(self, chat_ctx) -> None:
        from nion_auth import get_voice
        selected_voice = get_voice()
        from google.genai import types
        aad = types.AutomaticActivityDetection(
            silence_duration_ms=500,
            prefix_padding_ms=20,
        )
        input_cfg = types.RealtimeInputConfig(automatic_activity_detection=aad)

        # [ACTIVE ULTRA-LOW LATENCY REALTIME MODEL]:
        # Blazing fast instantaneous real-time response (<0.5s latency)
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
                close_app, folder_file, Play_file, play_music, stop_music, set_music_volume,
                move_cursor_tool, mouse_click_tool, scroll_cursor_tool,
                type_text_tool, press_key_tool, swipe_gesture_tool,
                press_hotkey_tool, control_volume_tool, see_screen,
                send_whatsapp_message, google_maps_tool, gmail_send_tool,
                gmail_search_tool, create_basic_website, process_minecraft_order_zip, extract_zip_to_folder, setup_minecraft_server,
                shutdown_pc, restart_pc, lock_pc, cancel_shutdown, get_pc_health_stats, get_user_wellness_status,
                set_reminder_tool, get_reminders_tool, open_isolated_browser, search_in_browser,
                send_whatsapp_web, send_messenger_message, send_facebook_post,
                get_live_screen_context, adapt_voice_emotion, sleep_mode_tool, add_todo_task, get_todo_list, execute_todo_autonomously, talk_with_gemini, open_gemini_and_chat, open_builtin_browser_and_navigate, discuss_with_gemini_autonomously, play_youtube_song_in_browser, close_builtin_browser, execute_autonomous_mission, send_chat_from_user_account, open_user_social_login
            ]
        )


async def entrypoint(ctx: agents.JobContext):
    # Immediately start background license monitor task at the top of entrypoint
    asyncio.create_task(background_license_checker_loop())
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

    has_greeted = [False]

    async def manage_session():
        import time
        while True:
            try:
                zora_agent = Assistant(chat_ctx=chat_ctx)
                session = AgentSession(
                    llm=zora_agent.model,
                    tools=zora_agent.agent.tools,
                    min_interruption_duration=0.8,
                    resume_false_interruption=False,
                    false_interruption_timeout=1.0,
                )

                # Register session globally so sleep mode can interrupt it
                from nion_sleep_mode import set_active_session
                set_active_session(session, asyncio.get_running_loop())

                session_alive = [True]

                @session.on("error")
                def on_session_error(*args, **kwargs):
                    print("AgentSession error detected. Flagging for restart...")
                    session_alive[0] = False

                @session.on("user_input_transcribed")
                def on_user_input(ev):
                    try:
                        txt = (getattr(ev, "transcript", "") or "").lower().strip()
                        if not txt:
                            return

                        from nion_auth import get_ai_name
                        ai_name = get_ai_name().lower()

                        if is_sleeping():
                            wake_phrases = [
                                "wake up", "wake", "wakeup",
                                "utho", "jago", "uthona", "uth re", "uth", "jagona",
                                "unmute", "unmute koro",
                                "silent mode off", "sailent mode off", "sleep mode off", "mute off",
                                "kotha bolo", "kotha bol",
                                "shuno", "suno",
                                ai_name + " utho", ai_name + " jago", ai_name + " wake",
                                ai_name + " uthona", ai_name + " kotha bolo", ai_name + " shuno",
                                "wake " + ai_name,
                            ]
                            is_wake = any(phrase in txt for phrase in wake_phrases)
                            if not is_wake and txt.strip() == ai_name:
                                is_wake = True

                            if is_wake:
                                print(f"[WAKE WORD DETECTED]: {txt} -> Authorizing wake for {get_ai_name()}!")
                                from nion_sleep_mode import authorize_wake, set_sleeping
                                authorize_wake()
                                set_sleeping(False)
                            else:
                                # User speaking while sleeping: purge buffer and interrupt
                                try:
                                    session.clear_user_turn()
                                except Exception:
                                    pass
                                from nion_sleep_mode import _interrupt_session_once
                                _interrupt_session_once()
                        else:
                            print(f"[Zora] Heard: {txt[:80]}")
                            # Auto-detect silent/sleep mode command directly from speech
                            sleep_triggers = [
                                "silent mode", "sailent mode", "sleep mode",
                                "chup koro", "chup thako", "chup hoye jao",
                                "shup koro", "shup thako",
                                "mute koro", "mute hoye jao",
                                "shuye poro", "shuye thako", "ghumiye poro",
                                "go to sleep", "stay silent", "be quiet"
                            ]
                            if any(st in txt for st in sleep_triggers):
                                print(f"[Zora] Speech directly triggered silent mode: '{txt}'")
                                from nion_sleep_mode import set_sleeping
                                set_sleeping(True, delayed_seconds=3.5)
                    except Exception as err:
                        print(f"[Zora] on_user_input error: {err}")

                @session.on("agent_speech_committed")
                def on_speech_committed(ev):
                    if is_sleeping():
                        try:
                            session.clear_user_turn()
                        except Exception:
                            pass
                        from nion_sleep_mode import _interrupt_session_once
                        _interrupt_session_once()

                await session.start(room=ctx.room, agent=zora_agent.agent)

                # Start background license watcher immediately
                asyncio.create_task(background_license_checker_loop())

                from nion_auth import get_ai_name
                print(f"{get_ai_name()} session is LIVE and listening!")

                # Sweet startup greeting on first connect: greets user by name
                if not has_greeted[0]:
                    has_greeted[0] = True
                    try:
                        from nion_prompts import get_current_user_name, get_current_ai_name
                        u_name = get_current_user_name()
                        a_name = get_current_ai_name()
                        greeting_prompt = f"[System Event: Assistant session started. Greet Boss {u_name} out loud in your sweet voice. Say: 'Hello {u_name}! Ki koro? Ami {a_name}, kemon acho shona?']"
                        print(f"[Zora] Speaking startup greeting: 'Hello {u_name}! Ki koro? Ami {a_name}, kemon acho shona?'")
                        asyncio.create_task(
                            session.generate_reply(
                                user_input=greeting_prompt,
                                input_modality="text"
                            )
                        )
                    except Exception as ge:
                        print(f"[Zora] Startup greeting notice: {ge}")

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
                finally:
                    # Clear session reference on close
                    try:
                        from nion_sleep_mode import set_active_session
                        set_active_session(None)
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
    asyncio.create_task(background_license_checker_loop())
    # asyncio.create_task(background_screen_monitor()) # Disabled continuous 5s screen upload to eliminate reply lag!

    # Keep the entrypoint alive
    while True:
        await asyncio.sleep(60)



# ── CLI Visual Banner & Modern Badge Helper (Matching Neon Terminal Theme) ──
import socket
import platform
import datetime

# Enable ANSI escape sequences on Windows Command Prompt & PowerShell
try:
    os.system("")
except Exception:
    pass

CYAN = "\033[38;5;75m"
PURPLE = "\033[38;5;141m"
MAGENTA = "\033[38;5;177m"
GREEN = "\033[38;5;82m"
YELLOW = "\033[38;5;220m"
WHITE = "\033[97m"
GRAY = "\033[90m"
RESET = "\033[0m"
BOLD = "\033[1m"

BG_GREEN = "\033[48;5;40m\033[30m\033[1m"
BG_RED = "\033[48;5;196m\033[97m\033[1m"
BG_BLUE = "\033[48;5;33m\033[97m\033[1m"
BG_YELLOW = "\033[48;5;214m\033[30m\033[1m"
BG_PURPLE = "\033[48;5;129m\033[97m\033[1m"

def _mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return key or ""
    parts = key.split("-")
    if len(parts) >= 4:
        return f"{parts[0]}-{parts[1]}-****-{parts[-1]}"
    elif len(parts) == 3:
        return f"{parts[0]}-****-{parts[-1]}"
    return key[:4] + "-****-" + key[-4:]

def _print_zora_banner(badge_action: str = None, badge_msg: str = None):
    try:
        from nion_auth import get_ai_name, get_user_name, get_saved_license
        ai_name = get_ai_name() or "Zora"
        user_name = get_user_name() or "Neon"
        saved = get_saved_license() or {}
        lic_key = saved.get("key", "NO-LICENSE-KEY")
        lic_plan = saved.get("plan", "Pro")
    except Exception:
        ai_name = "Zora"
        user_name = "Neon"
        lic_key = "NO-LICENSE-KEY"
        lic_plan = "Pro"

    try:
        import psutil
        ram_gb = round(psutil.virtual_memory().total / (1024**3))
        ram_str = f"{ram_gb} GB"
        cores = psutil.cpu_count(logical=False) or psutil.cpu_count() or 4
        cpu_name = platform.processor() or "Intel(R)"
        cpu_short = "Intel(R)" if "intel" in cpu_name.lower() else ("AMD" if "amd" in cpu_name.lower() else "x86_64")
        cpu_str = f"{cores}x {cpu_short}"
    except Exception:
        ram_str = "16 GB"
        cpu_str = "4x Intel(R)"

    hostname = socket.gethostname()
    plat = f"{sys.platform} ({platform.machine()})"
    version = "2.0.2"

    banner = f"""
{CYAN}{BOLD}     ███████╗ ██████╗ ██████╗  █████╗       █████╗ ██╗
     ╚══███╔╝██╔═══██╗██╔══██╗██╔══██╗     ██╔══██╗██║
       ███╔╝ ██║   ██║██████╔╝███████║     ███████║██║
      ███╔╝  ██║   ██║██╔══██╗██╔══██║     ██╔══██║██║
     ███████╗╚██████╔╝██║  ██║██║  ██║     ██║  ██║██║
     ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝     ╚═╝  ╚═╝╚═╝{RESET}
            {WHITE}{BOLD}Z O R A   A I   A S S I S T A N T   v{version}{RESET}

{GRAY}────────────────────────────────────────────────────────────{RESET}
  {WHITE}Creator{RESET}         {PURPLE}{BOLD}Neon{RESET}
  {WHITE}Version{RESET}         {CYAN}v{version}{RESET}
  {WHITE}AI Name{RESET}         {CYAN}{ai_name}{RESET}
  {WHITE}User Name{RESET}       {GREEN}{user_name}{RESET}
  {WHITE}License Key{RESET}     {YELLOW}{_mask_key(lic_key)}{RESET}
  {WHITE}License Status{RESET}  {GREEN}Active ({lic_plan} Plan){RESET}
  {WHITE}Platform{RESET}        {CYAN}{plat}{RESET}
  {WHITE}Hostname{RESET}        {MAGENTA}{hostname}{RESET}
  {WHITE}CPU Cores{RESET}       {YELLOW}{cpu_str}{RESET}
  {WHITE}Total RAM{RESET}       {YELLOW}{ram_str}{RESET}
{GRAY}────────────────────────────────────────────────────────────{RESET}
"""
    print(banner)
    if badge_action and badge_msg:
        _print_badge(badge_action, badge_msg)

def _print_badge(action: str, message: str):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    act = action.strip().upper()
    if act == "START":
        badge = f"{BG_GREEN}  START   {RESET}"
    elif act == "STOP":
        badge = f"{BG_RED}   STOP   {RESET}"
    elif act == "STATUS":
        badge = f"{BG_BLUE}  STATUS  {RESET}"
    elif act == "UPDATE":
        badge = f"{BG_YELLOW}  UPDATE  {RESET}"
    elif act in ("UNINSTALL", "REMOVE"):
        badge = f"{BG_RED} UNINSTALL {RESET}"
    elif act in ("VOICE", "VOICES"):
        badge = f"{BG_PURPLE}  VOICE   {RESET}"
    elif act in ("CONFIG", "RENAME"):
        badge = f"{BG_BLUE}  CONFIG  {RESET}"
    elif act == "CONSOLE":
        badge = f"{BG_GREEN} CONSOLE  {RESET}"
    else:
        badge = f"{BG_BLUE} {act:^8} {RESET}"

    print(f"[{GRAY}{now}{RESET}]  {badge}  {message}\n")


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
        _print_zora_banner("STOP", "Zora AI is not running in the background.")
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
    _print_zora_banner("STOP", f"Zora AI background process terminated (PID {pid}).")

def _do_status():
    pid = _get_running_pid()
    if pid:
        _print_zora_banner("STATUS", f"Zora AI is RUNNING in background (PID {pid}). Audio is live!")
        print(f"  Log: {_LOG_FILE}")
        print("  Run 'zora stop' anytime to stop the assistant.\n")
    else:
        _print_zora_banner("STATUS", "Zora AI is currently STOPPED / NOT running.")
        print("  Run 'zora start'   to start in background (silent).")
        print("  Run 'zora console' to test with PC mic & speakers.")
        print("  Run 'zora update'  to check for updates.\n")

def _do_start_background():
    pid = _get_running_pid()
    if pid:
        _print_zora_banner("START", f"Zora AI is ALREADY running in background (PID {pid}). Use 'zora stop' first.")
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
    _print_zora_banner("START", f"Zora AI running in background (PID {proc.pid}) — Audio active")
    print("  You can now close this Command Prompt / PowerShell window.")
    print("  Zora AI is listening in the background. Type 'zora stop' to stop her.\n")

def _do_update():
    _print_zora_banner("UPDATE", "Checking PyPI for latest releases from creator Neon...")
    pid = _get_running_pid()
    if pid:
        _print_badge("STOP", "Stopping background Zora before applying update...")
        _do_stop()

    import subprocess
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "zoraai"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            _print_badge("UPDATE", "Zora AI updated successfully to latest version! License preserved.")
            print("  Type 'zora start' to start her up! ❤️\n")
        else:
            _print_badge("UPDATE", f"Update note: {proc.stderr or proc.stdout}")
    except Exception as e:
        _print_badge("UPDATE", f"Update error: {e}")

def _do_uninstall():
    """Completely stops background processes and uninstalls zoraai from the PC."""
    _print_zora_banner("UNINSTALL", "Zora AI Complete Uninstaller")
    try:
        confirm = input("  Are you sure you want to uninstall Zora AI from your PC? (y/N) > ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\n  Cancelled.\n")
        return

    if confirm not in ("y", "yes"):
        print("\n  Uninstall cancelled. Zora AI remains installed.\n")
        return

    remove_data = False
    try:
        data_choice = input("  Do you also want to remove your license and config files? (y/N) > ").strip().lower()
        if data_choice in ("y", "yes"):
            remove_data = True
    except (KeyboardInterrupt, EOFError):
        pass

    pid = _get_running_pid()
    if pid:
        _print_badge("STOP", "Stopping background Zora AI daemon...")
        _do_stop()

    if remove_data:
        try:
            import shutil
            if _CONFIG_DIR.exists():
                shutil.rmtree(_CONFIG_DIR, ignore_errors=True)
                print(f"  Removed configuration: {_CONFIG_DIR}")
        except Exception as e:
            print(f"  Note: could not remove config dir: {e}")
    else:
        try:
            if _PID_FILE.exists():
                _PID_FILE.unlink()
        except Exception:
            pass

    import subprocess
    if sys.platform == "win32":
        _print_badge("UNINSTALL", "Uninstalling Zora AI in background...")
        bg_cmd = f'ping 127.0.0.1 -n 3 > nul & "{sys.executable}" -m pip uninstall -y zoraai'
        try:
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            subprocess.Popen(
                bg_cmd,
                shell=True,
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            )
            print("  Zora AI is exiting and will be completely removed in 2 seconds.")
            print("  Thank you for using Zora AI! Goodbye. 👋\n")
            sys.exit(0)
        except Exception:
            subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "zoraai"])
    else:
        cmd = [sys.executable, "-m", "pip", "uninstall", "-y", "zoraai"]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            _print_badge("UNINSTALL", "Zora AI has been completely removed from your PC.")
            print("  Thank you for using Zora AI! Goodbye. 👋\n")
        else:
            _print_badge("UNINSTALL", f"Pip uninstall note: {proc.stderr or proc.stdout}")

def _do_voice():
    from nion_auth import get_voice, set_voice
    curr = get_voice()
    _print_zora_banner("VOICE", f"Active Voice: {curr}")
    print("  Available Sweet/Cute Voices for Gemini 3.1:")
    print("    1. Laomedeia  - Shikon, light and sweet youthful voice")
    print("    2. Callirrhoe - Playful, lively, adure and neka voice")
    print("    3. Kore       - Soft, soothing, calm romantic voice")
    print("    4. Leda       - Bright, crisp, energetic girl voice")
    print("    5. Aoede      - Expressive, ultra-fast human voice (Default)")
    print()
    try:
        choice = input("  Select voice (1-5 or voice name, Enter to keep current) > ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n  Cancelled.\n")
        return

    mapping = {
        "1": "Laomedeia", "laomedeia": "Laomedeia",
        "2": "Callirrhoe", "callirrhoe": "Callirrhoe",
        "3": "Kore", "kore": "Kore",
        "4": "Leda", "leda": "Leda",
        "5": "Aoede", "aoede": "Aoede",
    }
    selected = mapping.get(choice.lower(), choice) if choice else curr
    set_voice(selected)
    _print_badge("VOICE", f"Voice set to: {selected}! Run 'zora console' to test it.")

def _do_rename():
    from nion_auth import get_user_name, get_ai_name, save_license, get_saved_license
    current_ai = get_ai_name()
    current_user = get_user_name()
    _print_zora_banner("CLI", "Zora AI Setup & Configuration")
    try:
        print(f"  AI Name: {current_ai} (Fixed) | Current User Name: {current_user}\n")
        new_user = input(f"  Enter your Name (e.g. Sijan) [press Enter to keep '{current_user}'] > ").strip()

        # Display all available microphones and speakers
        import sounddevice as sd
        devices = sd.query_devices()
        mics = [i for i, d in enumerate(devices) if d.get("max_input_channels", 0) > 0]
        spks = [i for i, d in enumerate(devices) if d.get("max_output_channels", 0) > 0]

        print("\n  === SELECT YOUR MICROPHONE (INPUT_DEVICE) ===")
        for nut, idx in enumerate(mics, 1):
            print(f"  [{nut}] {devices[idx]['name']} (Idx: {idx})")
        mic_choice = input(f"\n  Select Microphone Number [1-{len(mics)}] (press Enter to keep current) > ").strip()

        print("\n  === SELECT YOUR SPEAKER / HEADSET (OUTPUT_DEVICE) ===")
        for nut, idx in enumerate(spks, 1):
            print(f"  [{nut}] {devices[idx]['name']} (Idx: {idx})")
        spk_choice = input(f"\n  Select Speaker Number [1-{len(spks)}] (press Enter to keep current) > ").strip()

    except (KeyboardInterrupt, EOFError):
        print("\n  Cancelled.\n")
        return

    saved = get_saved_license() or {}
    key = saved.get("key", "")
    client = saved.get("client", "User")
    plan = saved.get("plan", "Pro")

    ai_to_save = current_ai
    user_to_save = new_user if new_user else current_user

    selected_mic_idx = None
    selected_spk_idx = None

    if mic_choice.isdigit() and 1 <= int(mic_choice) <= len(mics):
        selected_mic_idx = mics[int(mic_choice) - 1]
    if spk_choice.isdigit() and 1 <= int(spk_choice) <= len(spks):
        selected_spk_idx = spks[int(spk_choice) - 1]

    save_license(key, client, plan, user_name=user_to_save, ai_name=ai_to_save)

    cfg_file = Path.home() / ".zoraai" / "config.json"
    data = {}
    if cfg_file.exists():
        try:
            data = json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    if selected_mic_idx is not None:
        data["input_device"] = selected_mic_idx
    if selected_spk_idx is not None:
        data["output_device"] = selected_spk_idx
    cfg_file.parent.mkdir(parents=True, exist_ok=True)
    cfg_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    _print_badge("CONFIG", f"Updated! AI: {ai_to_save} | User: {user_to_save}")
    if selected_mic_idx is not None:
        print(f"  Microphone set to: [{selected_mic_idx}] {devices[selected_mic_idx]['name']}")
    if selected_spk_idx is not None:
        print(f"  Speaker set to:    [{selected_spk_idx}] {devices[selected_spk_idx]['name']}\n")

def cli_main():
    try:
        from nion_sleep_mode import start_hotkey_listener
        start_hotkey_listener()
    except Exception:
        pass

    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "start"

    if cmd == "stop":
        _do_stop()
        return
    if cmd == "status":
        _do_status()
        return
    if cmd == "update":
        _do_update()
        return
    if cmd in ("uninstall", "remove"):
        _do_uninstall()
        return
    if cmd in ("voice", "voices"):
        if len(sys.argv) > 2:
            from nion_auth import set_voice
            v_name = sys.argv[2].strip().lower()
            mapping = {
                "1": "Laomedeia", "laomedeia": "Laomedeia",
                "2": "Callirrhoe", "callirrhoe": "Callirrhoe",
                "3": "Kore", "kore": "Kore",
                "4": "Leda", "leda": "Leda",
                "5": "Aoede", "aoede": "Aoede",
            }
            selected = mapping.get(v_name, sys.argv[2].strip().capitalize())
            set_voice(selected)
            _print_zora_banner("VOICE", f"Voice set to: {selected}! Run 'zora console' to test it.")
            return
        _do_voice()
        return
    if cmd in ("name", "rename", "setup", "config"):
        _do_rename()
        return

    from nion_auth import verify_or_prompt_user
    if not verify_or_prompt_user():
        return

    if cmd == "start":
        _do_start_background()

    elif cmd == "dev":
        _print_zora_banner("START", "Zora AI -- Dev Worker Mode (Ctrl+C to stop)")
        sys.argv = ["zora", "start"]
        agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))

    elif cmd == "console":
        sel_mic, sel_spk = setup_audio_devices()
        _print_zora_banner("CONSOLE", "Interactive Console Mode (PC Mic & Speakers active)")
        print("  Speak into your microphone. Press Ctrl+C to stop.\n")
        if sel_mic is not None:
            sys.argv = ["zora", "console", "--input-device", str(sel_mic)]
        else:
            sys.argv = ["zora", "console"]
        agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))

    else:
        agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))

if __name__ == "__main__":
    cli_main()