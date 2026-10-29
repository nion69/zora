import os
import re
import json
import asyncio
import logging
from typing import Dict, Any, List

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool():
        def decorator(f):
            return f
        return decorator

logger = logging.getLogger("Zora_StonicExecutor")

# ─────────────────────────────────────────────────────────────
# 1. ACTION REGISTRY - DISPATCH REAL SYSTEM ACTIONS
# ─────────────────────────────────────────────────────────────

async def _dispatch_single_action(action_type: str, action_arg: str) -> str:
    act = (action_type or "").lower().strip()
    arg = (action_arg or "").strip()

    try:
        # YouTube & Media
        if act in ("play_youtube", "youtube"):
            from nion_playwright_browser import play_youtube_song_in_browser
            return await play_youtube_song_in_browser(arg)

        elif act in ("play_music", "music"):
            from nion_music_player import play_music
            return await play_music(arg)

        elif act in ("stop_music", "pause_music"):
            from nion_music_player import stop_music
            return await stop_music()

        # Browser & Web
        elif act in ("browse", "open_url", "search_web"):
            from nion_playwright_browser import open_builtin_browser_and_navigate
            return await open_builtin_browser_and_navigate(arg)

        elif act in ("close_browser",):
            from nion_playwright_browser import close_builtin_browser
            return await close_builtin_browser()

        # Apps & Windows
        elif act in ("open_app", "launch"):
            from nion_window_CTRL import open_app
            return await open_app(arg)

        elif act in ("close_app", "terminate"):
            from nion_window_CTRL import close_app
            return await close_app(arg)

        # AI & Discussion
        elif act in ("gemini", "ai_discuss", "research"):
            from nion_playwright_browser import discuss_with_gemini_autonomously
            return await discuss_with_gemini_autonomously(arg)

        # Keyboard & Mouse
        elif act in ("type", "write"):
            from nion_keyboard_mouse_CTRL import type_text_tool
            return await type_text_tool(arg)

        elif act in ("press_key", "key"):
            from nion_keyboard_mouse_CTRL import press_key_tool
            return await press_key_tool(arg)

        # Default fallback: Silent web research
        else:
            from nion_autonomous_todo import silent_web_search
            res = await asyncio.to_thread(silent_web_search, f"{act} {arg}")
            return f"Researched: {res[:150]}"

    except Exception as e:
        logger.error(f"Action error {act}: {e}")
        return f"Error executing {act}: {e}"


# ─────────────────────────────────────────────────────────────
# 2. AUTONOMOUS INTENT DECOMPOSER (STONIC AI STYLE)
# ─────────────────────────────────────────────────────────────

def _decompose_goal_into_steps(goal: str) -> List[Dict[str, str]]:
    """
    Parses complex natural language tasks into atomic Stonic AI action steps.
    Supports English, Bangla, and Banglish.
    """
    g = goal.lower()
    steps = []

    # Check for YouTube requests
    if "youtube" in g or "gaan" in g or "song" in g or "play" in g:
        # Extract song name
        song = re.sub(r'(play|song|gaan|chalao|in|on|youtube|open|koro|shuno)', '', g, flags=re.IGNORECASE).strip()
        song = song or "Beggin"
        steps.append({"type": "play_youtube", "arg": song})

    # Check for Gemini / Discussion
    elif "gemini" in g or "discuss" in g or "kotha bolo" in g:
        topic = re.sub(r'(gemini|r|sathe|kotha|bolo|discuss|with|about|niye|alochona|koro)', '', g, flags=re.IGNORECASE).strip()
        topic = topic or "cats"
        steps.append({"type": "gemini", "arg": topic})

    # Check for opening apps
    elif any(w in g for w in ("open", "chalu", "launch")):
        app_name = re.sub(r'(open|koro|chalu|launch|app)', '', g, flags=re.IGNORECASE).strip()
        if "browser" in app_name:
            steps.append({"type": "browse", "arg": "google.com"})
        else:
            steps.append({"type": "open_app", "arg": app_name})

    # Check for closing apps
    elif any(w in g for w in ("close", "bondho", "shut", "kill")):
        target = re.sub(r'(close|bondho|koro|shut|kill|app)', '', g, flags=re.IGNORECASE).strip()
        if "browser" in target:
            steps.append({"type": "close_browser", "arg": ""})
        elif "music" in target or "gaan" in target:
            steps.append({"type": "stop_music", "arg": ""})
        else:
            steps.append({"type": "close_app", "arg": target})

    # General / Research
    else:
        steps.append({"type": "research", "arg": goal})

    return steps


# ─────────────────────────────────────────────────────────────
# 3. LIVEKIT AUTONOMOUS MISSION TOOL
# ─────────────────────────────────────────────────────────────

@function_tool()
async def execute_autonomous_mission(mission_goal: str) -> str:
    """
    Stonic-AI Level Full Autonomous Agent Execution.
    Takes any high-level human command or multi-step goal, breaks it down into system actions, 
    and executes them consecutively without asking questions.
    
    Examples:
    - 'zora youtube open kore beggin song chalao' -> executes play_youtube
    - 'zora gemini open kore cat niye alochona koro' -> executes gemini discussion
    - 'zora ai todo list onujai kaj koro' -> executes all pending tasks
    - 'notepad open kore hello likho' -> launches notepad and types text
    """
    logger.info(f"[STONIC AGENT] Received mission: '{mission_goal}'")
    
    # 1. If user refers to todo list, run all pending todos
    if any(w in mission_goal.lower() for w in ("todo", "to-do", "list", "kaj gula", "tasks")):
        from nion_autonomous_todo import load_todos, save_todos
        from datetime import datetime
        todos = load_todos()
        pending = [t for t in todos if t.get("status") != "completed"]
        if not pending:
            return "Babu, kono pending task nei execute korar jonno!"
        
        results = []
        for t in pending:
            steps = _decompose_goal_into_steps(t["task"])
            step_results = []
            for s in steps:
                res = await _dispatch_single_action(s["type"], s["arg"])
                step_results.append(res)
            t["status"] = "completed"
            t["completed_at"] = datetime.now().strftime("%Y-%m-%d %I:%M %p")
            t["result"] = " | ".join(step_results)
            results.append(f"Task '{t['task']}' complete: {' '.join(step_results)}")
        
        save_todos(todos)
        return " ".join(results)

    # 2. Single multi-step goal execution
    steps = _decompose_goal_into_steps(mission_goal)
    step_results = []
    for s in steps:
        res = await _dispatch_single_action(s["type"], s["arg"])
        step_results.append(res)

    final_msg = " ".join(step_results)
    return f"Shona, ami nijer theke mission complete korechi! {final_msg}"
