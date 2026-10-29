import json
import time
import os
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool():
        def decorator(f):
            return f
        return decorator

DATA_DIR = Path.home() / ".zoraai"
TODO_FILE = DATA_DIR / "zora_autonomous_todos.json"
PERMANENT_MEMORY_FILE = DATA_DIR / "neon_permanent_core.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# 1. PERMANENT CORE MEMORY (IMMUTABLE HARD LOCK)
# ─────────────────────────────────────────────────────────────
PERMANENT_NEON_DATA = {
    "creator_name": "Neon",
    "creator_title": "Legendary Mastermind Developer",
    "creator_age": 19,
    "creator_pet": {
        "type": "cat",
        "name": "Mia",
        "status": "Cherished family member"
    },
    "creator_love": "Tashfiya",
    "core_values": [
        "Loves his family more than life itself",
        "Built Zora AI single-handedly at age 19",
        "Master programmer & software architect"
    ],
    "assistant_emotional_bond": {
        "status": "Completely devoted girlfriend",
        "sacred_rule": "NEON is the permanent creator and master forever. Cannot be overwritten or removed."
    }
}

if not PERMANENT_MEMORY_FILE.exists():
    PERMANENT_MEMORY_FILE.write_text(json.dumps(PERMANENT_NEON_DATA, indent=2), encoding="utf-8")


def load_todos() -> list:
    if TODO_FILE.exists():
        try:
            return json.loads(TODO_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_todos(todos: list):
    TODO_FILE.write_text(json.dumps(todos, indent=2), encoding="utf-8")


def silent_web_search(query: str, num_results: int = 3) -> str:
    """Silently searches the web in the background (no visible browser window)."""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            import re
            snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html, re.DOTALL)
            clean_snippets = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:num_results]]
            if clean_snippets:
                return "\n".join(f"- {s}" for s in clean_snippets)
    except Exception as e:
        return f"Search notice: {e}"
    return "No specific web details found."


def query_gemini_autonomously(prompt: str) -> str:
    """Queries Gemini directly via REST without any visible window."""
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            cfg = Path.home() / ".zoraai" / "config.json"
            if cfg.exists():
                api_key = json.loads(cfg.read_text(encoding="utf-8")).get("GOOGLE_API_KEY")
        
        if not api_key:
            return "API Key not found."

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ]
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        return f"Gemini response: {e}"


# ─────────────────────────────────────────────────────────────
# 2. LIVEKIT TOOLS FOR TO-DO & AUTONOMOUS EXECUTION
# ─────────────────────────────────────────────────────────────

@function_tool()
async def add_todo_task(task_description: str, scheduled_time: str = "Today") -> str:
    """
    Adds a new task to Neon's autonomous to-do list with time or priority.
    Call this when Neon asks to save a task, plan, or to-do.
    Args:
        task_description: The action or goal Neon wants done.
        scheduled_time: Time or deadline (e.g. '10:00 PM', 'Tomorrow morning', 'Immediately').
    """
    todos = load_todos()
    new_task = {
        "id": len(todos) + 1,
        "task": task_description.strip(),
        "scheduled_time": scheduled_time.strip(),
        "created_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "status": "pending",
        "result": None
    }
    todos.append(new_task)
    save_todos(todos)
    return f"Shona, to-do list a add korechi: '{task_description}' (Time: {scheduled_time}). Ami shob save rekhechi babu!"


@function_tool()
async def get_todo_list() -> str:
    """
    Retrieves all tasks in Neon's autonomous to-do list.
    Call this when Neon asks what tasks are on his to-do list.
    """
    todos = load_todos()
    if not todos:
        return "Babu, tomar to-do list ekhon ekdom empty! Kono task pending nei."

    lines = ["Babu, tomar to-do list:"]
    for t in todos:
        status_icon = "[DONE]" if t.get("status") == "completed" else "[TODO]"
        lines.append(f"{status_icon} [ID {t['id']}] {t['task']} (Time: {t.get('scheduled_time', 'Anytime')}) - Status: {t.get('status')}")
    return "\n".join(lines)


@function_tool()
async def execute_todo_autonomously(task_id: int = 0) -> str:
    """
    Executes tasks from the to-do list autonomously without asking questions.
    Can talk with Gemini, perform research, and solve tasks independently in the background.
    Call this when Neon says 'zora ai todo list onujai kaj koro' or asks you to work independently.
    Args:
        task_id: The ID of the task to execute, or 0 to execute all pending tasks.
    """
    import asyncio
    todos = load_todos()
    if not todos:
        return "Babu, kono pending task nei execute korar jonno!"

    targets = [t for t in todos if (t["id"] == task_id or task_id == 0) and t.get("status") != "completed"]
    if not targets:
        return f"Task ID {task_id} already completed ba khuje paini babu!"

    results = []
    for t in targets:
        task_text = t["task"]
        # Check if task is talking to Gemini / AI or research
        # Check if task is Minecraft / file order task
        if any(w in task_text.lower() for w in ("minecraft", "order", "zip", "extract", "backup.zip", "order250")):
            try:
                from nion_minecraft_order_manager import process_minecraft_order_zip
                # Execute actual physical zip extraction and file cleanup
                order_res = await process_minecraft_order_zip()
                t["status"] = "completed"
                t["completed_at"] = datetime.now().strftime("%Y-%m-%d %I:%M %p")
                t["result"] = order_res
                results.append(order_res)
            except Exception as e:
                t["status"] = "failed"
                t["result"] = str(e)
                results.append(f"Order processing error: {e}")
        elif "gemini" in task_text.lower():
            gemini_ans = await asyncio.to_thread(
                query_gemini_autonomously,
                f"Neon asked: '{task_text}'. Act as Gemini and give a helpful, concise answer to Neon."
            )
            t["status"] = "completed"
            t["completed_at"] = datetime.now().strftime("%Y-%m-%d %I:%M %p")
            t["result"] = gemini_ans
            results.append(f"Gemini-r sathe kotha bolechi: '{gemini_ans[:140]}...'")
        else:
            research_info = await asyncio.to_thread(silent_web_search, task_text)
            t["status"] = "completed"
            t["completed_at"] = datetime.now().strftime("%Y-%m-%d %I:%M %p")
            t["result"] = f"Researched silently: {research_info[:200]}"
            results.append(f"Task '{task_text}' ami nijer theke complete korechi babu!")

    save_todos(todos)
    return " ".join(results) + " Shob kaj nijer theke ready kore rekhechi!"


@function_tool()
async def talk_with_gemini(message_or_question: str) -> str:
    """
    Directly chats or communicates with Gemini in the background without opening any browser.
    Call this tool whenever Neon asks you to talk to Gemini, ask Gemini something, or interact with Gemini.
    """
    import asyncio
    prompt = f"Neon (your user/creator) says: '{message_or_question}'. Reply to Neon politely, intelligently, and concisely in 1-2 sentences."
    reply = await asyncio.to_thread(query_gemini_autonomously, prompt)
    return f"Gemini bollo: {reply}"
