import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import threading
import time
import re
from pathlib import Path

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool():
        def decorator(f):
            return f
        return decorator

try:
    import pygame
    if not pygame.mixer.get_init():
        pygame.mixer.init()
except Exception:
    pygame = None

# Background playback state
_music_lock = threading.Lock()
_current_song = None
_is_playing = False
_download_thread = None
_cancel_flag = False
_music_volume = 0.6  # Default 60% independent volume

CACHE_DIR = Path.home() / ".zoraai" / "music_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_music_volume() -> int:
    return int(_music_volume * 100)


def _stop_active_playback():
    """Immediately stops and unloads any currently playing audio track."""
    global _is_playing, _cancel_flag
    _cancel_flag = True
    _is_playing = False
    try:
        if pygame and pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
    except Exception:
        pass


def _background_stream_worker(song_name: str):
    global _is_playing, _current_song, _cancel_flag, _music_volume
    try:
        # Check cancel flag before doing anything
        if _cancel_flag:
            return

        import yt_dlp
        import imageio_ffmpeg

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_dir = os.path.dirname(ffmpeg_exe)
        target_ffmpeg = os.path.join(ffmpeg_dir, "ffmpeg.exe")
        if not os.path.exists(target_ffmpeg):
            import shutil
            shutil.copyfile(ffmpeg_exe, target_ffmpeg)

        # Sanitize filename for cache
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', song_name).strip('_')[:35]
        cached_mp3 = CACHE_DIR / f"{safe_name}.mp3"

        if not cached_mp3.exists() or cached_mp3.stat().st_size < 10000:
            out_tmpl = str(CACHE_DIR / f"{safe_name}.%(ext)s")
            ydl_opts = {
                'format': 'ba/b',
                'outtmpl': out_tmpl,
                'ffmpeg_location': ffmpeg_dir,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',
                }],
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"ytsearch1:{song_name} audio"])

        if _cancel_flag:
            print(f"[Zora Music] Cancel flag active. Skipping playback of '{song_name}'.")
            return

        if cached_mp3.exists() and cached_mp3.stat().st_size > 10000:
            with _music_lock:
                if _cancel_flag:
                    return
                if pygame and pygame.mixer.get_init():
                    pygame.mixer.music.load(str(cached_mp3))
                    pygame.mixer.music.set_volume(_music_volume)
                    pygame.mixer.music.play()
                    _is_playing = True
                    _current_song = song_name
                    print(f"[Zora Music] Playing '{song_name}' (Volume: {int(_music_volume*100)}%)")
    except Exception as e:
        print(f"[Zora Music Error] {e}")
        _is_playing = False


def is_playing() -> bool:
    with _music_lock:
        return bool(_is_playing and pygame and pygame.mixer.get_init() and pygame.mixer.music.get_busy())


@function_tool()
async def play_music(song_name: str) -> str:
    """
    Plays the exact song or music requested by the user in the background.
    Examples: 'play beggin', 'play faded', 'gaan bajao', 'music chalao'.
    """
    global _is_playing, _current_song, _download_thread, _cancel_flag
    _cancel_flag = False

    # Stop current music if already playing
    _stop_active_playback()
    _cancel_flag = False

    _current_song = song_name
    _is_playing = True

    # Launch in non-blocking background thread
    _download_thread = threading.Thread(target=_background_stream_worker, args=(song_name,), daemon=True)
    _download_thread.start()

    return f"Shona, ami background-e '{song_name}' gaan-ta play korchi!"


@function_tool()
async def stop_music() -> str:
    """
    Immediately stops and terminates any music or song currently playing.
    Call this tool whenever the user says:
    'stop music', 'pause', 'puse', 'gaan bondho koro', 'music off koro', 'chup koro gaan', 'stop'.
    """
    global _current_song
    prev = _current_song or "gaan"
    _stop_active_playback()
    _current_song = None
    print(f"[Zora Music] Completely stopped music: {prev}")
    return f"Shona, ami gaan bondho kore diyechi!"


@function_tool()
async def set_music_volume(action: str = "set", volume_percent: int = -1) -> str:
    """
    Controls background music player volume independently.
    """
    global _music_volume
    act = (action or "").lower().strip()

    if volume_percent >= 0:
        _music_volume = max(0.0, min(1.0, float(volume_percent) / 100.0))
    elif any(w in act for w in ("low", "down", "kom", "decrease", "reduce", "slow", "quiet", "choto")):
        _music_volume = max(0.05, _music_volume - 0.25)
    elif any(w in act for w in ("high", "up", "barhao", "increase", "raise", "loud", "boro")):
        _music_volume = min(1.0, _music_volume + 0.25)
    elif "mute" in act:
        _music_volume = 0.0
    elif "unmute" in act:
        _music_volume = 0.5
    else:
        nums = re.findall(r'\d+', act)
        if nums:
            _music_volume = max(0.0, min(1.0, float(nums[0]) / 100.0))

    if pygame and pygame.mixer.get_init():
        try:
            pygame.mixer.music.set_volume(_music_volume)
        except Exception as e:
            print(f"[Zora Music] Error setting volume: {e}")

    pct = int(_music_volume * 100)
    return f"Music volume {pct}% kora hoyeche."
