import time
import os
import asyncio
import psutil
from datetime import datetime

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool():
        def decorator(f):
            return f
        return decorator

@function_tool()
async def get_pc_health_stats() -> str:
    """
    Gets live PC performance, health, uptime, CPU, RAM, and battery status.
    Use this when Neon asks 'PC health kemon?', 'PC kotohour dore chalche?',
    'CPU RAM status', or how long the PC has been running.
    """
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        hours, up_rem = divmod(int(uptime.total_seconds()), 3600)
        mins, _ = divmod(up_rem, 60)
        uptime_str = f"{hours} hours {mins} minutes"

        cpu_pct = psutil.cpu_percent(interval=0.2)
        mem = psutil.virtual_memory()
        ram_pct = mem.percent
        ram_gb = round(mem.used / (1024**3), 1)
        ram_total = round(mem.total / (1024**3), 1)

        stats = (
            f"[PC HEALTH & PERFORMANCE]\n"
            f"- PC Uptime: {uptime_str} (Since {boot_time.strftime('%I/%M %p')})\n"
            f"- CPU Usage: {cpu_pct}%\n"
            f"- RAM Usage: {ram_pct}% ({ram_gb} GB / {ram_total} GB)\n"
        )
        return stats
    except Exception as e:
        return f"[ERROR] Failed to read health stats: {e}"

@function_tool()
async def get_user_wellness_status() -> str:
    """
    Tracks user's screen time, gaming time, water breaks, and meal reminders.
    Use this to check how long Neon has been using the PC or playing games,
    and provide caring girlfriend advice (drink water, rest eyes, eat dinner/lunch).
    """
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        usage_secs = (int(datetime.now().timestamp() - boot_time.timestamp()))
        hours = usage_secs // 3600
        mins = (usage_secs % 3600) // 60

        # Check if common games are running
        game_procs = {"valorant.exe", "cs2.exe", "minecraft.exe", "robloxplayer.exe", "gta5.exe", "steam.exe"}
        running_games = []
        for p in psutil.process_iter():
            try:
                name = p.name()
                if name.lower() in game_procs:
                    running_games.append(name)
            except Exception:
                pass

        game_info = f"(Active Games: {', '.join(running_games)})" if running_games else "(No heavy games running)"

        now = datetime.now()
        current_hour = now.hour
        meal_suggestion = ""
        if 12 <= current_hour <= 14:
            meal_suggestion = "Lunch time hoye geche, khabar kheye nao!"
        elif 20 <= current_hour <= 22:
            meal_suggestion = "Dinner time hoye geche, rater khabar kheye nao!"

        report = (
            f"[USER WELLNESS & CARE]\n"
            f"- Total PC Screen Time: {hours} hrs {mins} mins\n"
            f"- Gaming Status: {game_info}\n"
            f"- Eye Care & Hydration: Pani khete bolo & 20 min por por chokh rest dite bolo (20-20-20 rule)\n"
        )
        if meal_suggestion:
            report += f"- Meal Care: {meal_suggestion}\n"
        return report
    except Exception as e:
        return f"[ERROR] Failed to get wellness: {e}"
