import os
import threading
import urllib.parse
import urllib.request
import re
import webbrowser
try:
    import pygame
    pygame.mixer.init()
except Exception:
    pygame = None
from livekit.agents import llm



is_playing = False

def _instant_play(song_name: str):
    global is_playing
    try:
        query = urllib.parse.quote(song_name)
        search_url = f"https://www.youtube.com/results?search_query={query}"
        
        # Fast extraction of top YouTube video ID (< 0.4s)
        req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        html = urllib.request.urlopen(req, timeout=4).read().decode("utf-8")
        video_ids = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html)
        
        if video_ids:
            top_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
            print(f"[Zora Music] Playing top result: {top_url}")
            webbrowser.open(top_url)
        else:
            print(f"[Zora Music] Opening YouTube search: {search_url}")
            webbrowser.open(search_url)
            
        is_playing = True
    except Exception as e:
        print(f"[Zora Music] Playback fallback: {e}")
        try:
            query = urllib.parse.quote(song_name)
            webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
            is_playing = True
        except Exception:
            is_playing = False


@llm.function_tool(description="Play any song, track, or music requested by the user. Use this whenever the user asks to play a song or music.")
async def play_music(song_name: str):
    """
    Plays music instantly in the background or default browser.
    Responds immediately so the assistant does not delay.
    """
    global is_playing
    print(f"[Zora] Instant play request for: {song_name}")
    
    # Run in background thread so tool returns in 0 milliseconds
    t = threading.Thread(target=_instant_play, args=(song_name,), daemon=True)
    t.start()
    
    return f"Main abhi tumhare liye {song_name} play kar rahi hoon jaan!"


def do_stop():
    global is_playing
    is_playing = False
    try:
        if pygame and hasattr(pygame, 'mixer') and pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
    except Exception:
        pass

    # Send media pause & stop to pause any browser/desktop music
    try:
        from pynput.keyboard import Key, Controller
        keyboard = Controller()
        keyboard.tap(Key.media_stop)
        keyboard.tap(Key.media_play_pause)
    except Exception:
        pass
    print("[Zora Music] Music stopped.")


@llm.function_tool(description="Stop the currently playing music, song, or video. Use this whenever the user asks to stop, pause, or mute the music.")
async def stop_music():
    """
    Stops music playback immediately.
    """
    do_stop()
    return "Maine music band kar diya hai jaan!"


# Global hotkey listener (Ctrl+M to stop music instantly if mic has echo from loud speakers)
def _start_hotkey_listener():
    try:
        from pynput import keyboard
        def on_press(key):
            try:
                # Check for Ctrl+M
                if key == keyboard.KeyCode.from_char('m') and (keyboard.Controller()._is_ctrl_pressed if hasattr(keyboard.Controller(), '_is_ctrl_pressed') else False):
                    do_stop()
            except Exception:
                pass

        # Use GlobalHotKeys for clean cross-platform shortcut
        hotkeys = keyboard.GlobalHotKeys({
            '<ctrl>+m': do_stop,
            '<ctrl>+<shift>+s': do_stop
        })
        hotkeys.daemon = True
        hotkeys.start()
    except Exception as e:
        pass

_start_hotkey_listener()
