import threading
import logging
import asyncio
import time

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool():
        def decorator(f):
            return f
        return decorator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------
# Global state
# ---------------------------------------------------------------
_sleep_lock = threading.Lock()
_is_sleeping = False
_hotkey_listener = None

# When we went to sleep (monotonic timestamp). Used for cooldown.
_sleep_timestamp = 0.0

# WAKE GUARD: Only True when our on_user_input handler explicitly
# detected a valid wake word. The sleep_mode_tool CHECKS this before
# allowing a wake action. This blocks the AI from auto-waking itself.
_wake_authorized = False
_wake_lock = threading.Lock()

# Global reference to the active AgentSession and its asyncio event loop
_active_session = None
_active_loop = None

# Background interrupt thread
_interrupt_thread = None
_interrupt_running = False

# Minimum seconds that must pass before wake is allowed (cooldown)
SLEEP_COOLDOWN_SECONDS = 0.0


# ---------------------------------------------------------------
# Session management
# ---------------------------------------------------------------
def set_active_session(session, loop=None):
    """Called from agent.py to register current AgentSession and loop."""
    global _active_session, _active_loop
    _active_session = session
    if loop is not None:
        _active_loop = loop
    else:
        try:
            _active_loop = asyncio.get_running_loop()
        except Exception:
            _active_loop = getattr(session, "loop", None) or getattr(session, "_loop", None)

def get_active_session():
    return _active_session

def get_active_loop():
    return _active_loop


# ---------------------------------------------------------------
# Wake authorization (ONLY set by on_user_input, not the AI itself)
# ---------------------------------------------------------------
def authorize_wake():
    """Called by on_user_input when a valid wake word is detected."""
    global _wake_authorized
    with _wake_lock:
        _wake_authorized = True
    print("[Zora] Wake authorized by explicit user command.")
    # Auto-clear after 6s in case tool call never arrives
    def _auto_clear():
        time.sleep(6.0)
        global _wake_authorized
        with _wake_lock:
            _wake_authorized = False
    threading.Thread(target=_auto_clear, daemon=True).start()

def _consume_wake_auth() -> bool:
    """Returns True and clears the flag if wake is authorized."""
    global _wake_authorized
    with _wake_lock:
        if _wake_authorized:
            _wake_authorized = False
            return True
        return False

def is_wake_in_cooldown() -> bool:
    """Returns True if we are still in the no-wake cooldown period."""
    return (time.monotonic() - _sleep_timestamp) < SLEEP_COOLDOWN_SECONDS


# ---------------------------------------------------------------
# Core sleep state
# ---------------------------------------------------------------
def is_sleeping() -> bool:
    with _sleep_lock:
        return _is_sleeping

def set_sleeping(value: bool, delayed_seconds: float = 0.0) -> bool:
    if delayed_seconds > 0 and value:
        def _delayed():
            time.sleep(delayed_seconds)
            _do_set_sleeping(True)
        threading.Thread(target=_delayed, daemon=True).start()
        return True

    _do_set_sleeping(bool(value))
    return bool(value)

def _do_set_sleeping(value: bool):
    global _is_sleeping, _sleep_timestamp, _interrupt_running, _interrupt_thread, _active_session, _active_loop
    with _sleep_lock:
        _is_sleeping = value

    sess = _active_session
    loop = _active_loop

    if value:
        _sleep_timestamp = time.monotonic()
        status = "SLEEPING (100% SILENT)"
        print(f"\n[ZORA STATE] >>> {status} <<< (Say '{_get_ai_name()} utho' / 'Wake up' / 'Silent mode off' or Ctrl+F8)\n")

        # Mute audio output on session so not a single byte reaches speakers
        if sess is not None and loop is not None and loop.is_running():
            def _mute_output():
                try:
                    if hasattr(sess, "output") and hasattr(sess.output, "set_audio_enabled"):
                        sess.output.set_audio_enabled(False)
                except Exception as e:
                    logger.debug(f"[Sleep] mute output error: {e}")
                try:
                    sess.clear_user_turn()
                except Exception:
                    pass
            loop.call_soon_threadsafe(_mute_output)

        # Force interrupt any ongoing speech immediately
        _interrupt_session_once()
        # Start background interrupt loop to keep killing any speech
        _start_interrupt_loop()
    else:
        status = "AWAKE (ACTIVE)"
        print(f"\n[ZORA STATE] >>> {status} <<<\n")
        _stop_interrupt_loop()

        # Re-enable audio output on session
        if sess is not None and loop is not None and loop.is_running():
            def _unmute_output():
                try:
                    if hasattr(sess, "output") and hasattr(sess.output, "set_audio_enabled"):
                        sess.output.set_audio_enabled(True)
                except Exception as e:
                    logger.debug(f"[Sleep] unmute output error: {e}")
            loop.call_soon_threadsafe(_unmute_output)

def _get_ai_name() -> str:
    try:
        from nion_auth import get_ai_name
        return get_ai_name()
    except Exception:
        return "Zora"

def _interrupt_session_once():
    """Single interrupt call on the active session, safely scheduled on the active loop."""
    global _active_session, _active_loop
    try:
        sess = _active_session
        loop = _active_loop
        if sess is None:
            return

        if loop is None or not loop.is_running():
            try:
                loop = asyncio.get_running_loop()
                _active_loop = loop
            except Exception:
                loop = getattr(sess, "loop", None) or getattr(sess, "_loop", None)
                if loop is not None and loop.is_running():
                    _active_loop = loop

        if loop is not None and loop.is_running():
            # Clear user turn buffer so LLM doesn't process user speech
            try:
                loop.call_soon_threadsafe(sess.clear_user_turn)
            except Exception:
                pass
            # Force interrupt current speech/turn
            try:
                asyncio.run_coroutine_threadsafe(sess.interrupt(force=True), loop)
            except Exception:
                try:
                    asyncio.run_coroutine_threadsafe(sess.interrupt(), loop)
                except Exception:
                    pass
    except Exception as e:
        logger.debug(f"[Sleep] interrupt error: {e}")

def _start_interrupt_loop():
    """Aggressively clear turns and interrupt every 0.4s while sleeping."""
    global _interrupt_running, _interrupt_thread
    _interrupt_running = True
    if _interrupt_thread and _interrupt_thread.is_alive():
        return

    def _loop():
        while _interrupt_running and is_sleeping():
            _interrupt_session_once()
            time.sleep(0.15)
        print("[Zora] Interrupt loop stopped.")

    _interrupt_thread = threading.Thread(target=_loop, daemon=True)
    _interrupt_thread.start()

def _stop_interrupt_loop():
    global _interrupt_running
    _interrupt_running = False


# ---------------------------------------------------------------
# Hotkey
# ---------------------------------------------------------------
def toggle_sleep() -> bool:
    sleeping = is_sleeping()
    if sleeping:
        # Hotkey always can wake
        authorize_wake()
        _do_set_sleeping(False)
        return False
    else:
        _do_set_sleeping(True)
        return True

def wake_up() -> bool:
    authorize_wake()
    return set_sleeping(False)

def put_to_sleep() -> bool:
    return set_sleeping(True)

def start_hotkey_listener():
    """Starts a non-blocking background keyboard listener for Ctrl+F8 to toggle mic/sleep."""
    global _hotkey_listener
    if _hotkey_listener is not None:
        return

    try:
        from pynput import keyboard
        hotkeys = keyboard.GlobalHotKeys({
            "<ctrl>+<f8>": toggle_sleep
        })
        hotkeys.daemon = True
        hotkeys.start()
        print("[Zora] Global Hotkey (Ctrl+F8) active for Sleep / Wake toggle.")
    except Exception as e:
        logger.warning(f"[Zora] Could not register global hotkey: {e}")


# ---------------------------------------------------------------
# Tool (AI-callable)
# ---------------------------------------------------------------
@function_tool()
async def sleep_mode_tool(action: str) -> str:
    """
    Controls Zora sleep and silent mode.
    Use when user asks to sleep, go silent, sailent mode, mute, or wake up.
    action="sleep" -> go to sleep / silent mode
    action="wake"  -> wake up (ONLY if explicitly requested by Boss)
    """
    act = (action or "").lower().strip()

    # --- SLEEP action ---
    if any(w in act for w in ("sleep", "mute", "silent", "sailent", "shuye", "chup", "bondho", "quiet", "ghum")):
        set_sleeping(True, delayed_seconds=3.0)
        return "[SLEEP_ACTIVE] Going to silent mode in 3 seconds. Will stay silent until Boss says wake up."

    # --- WAKE action ---
    elif any(w in act for w in ("wake", "unmute", "active", "utho", "jag", "uth", "bolo", "kotha", "off")):
        # GUARD: Only allow wake if explicitly authorized by on_user_input or hotkey
        if is_sleeping():
            # Check cooldown first
            if is_wake_in_cooldown():
                secs = SLEEP_COOLDOWN_SECONDS - (time.monotonic() - _sleep_timestamp)
                print(f"[Sleep] Wake blocked: cooldown ({secs:.1f}s remaining)")
                return "[BLOCKED] Still in sleep cooldown. Stay silent."

            # Check wake authorization
            if not _consume_wake_auth():
                print("[Sleep] Wake blocked: not authorized by user wake word.")
                return "[BLOCKED] Wake not authorized. Stay completely silent and do not speak."

        _do_set_sleeping(False)
        return "[AWAKE_ACTIVE] Zora is now awake! Greet Boss warmly in Banglish."

    # --- STATUS ---
    curr = "Sleeping (Silent)" if is_sleeping() else "Awake (Active)"
    return f"[STATUS] Zora is currently {curr}."
