import os
import subprocess
import shutil
import logging
import sys
import asyncio
from fuzzywuzzy import process

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool(func): 
        return func

try:
    import win32gui
    import win32con
except ImportError:
    win32gui = None
    win32con = None

try:
    import pygetwindow as gw
except ImportError:
    gw = None

# Setup encoding and logger
sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

local_app_data = os.getenv('LOCALAPPDATA')
app_data = os.getenv('APPDATA')

APP_MAPPINGS = {
    "notepad": "notepad",
    "calculator": "calc",
    "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "vlc": "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
    "command prompt": "cmd",
    "control panel": "control",
    "settings": "start ms-settings:",
    "paint": "mspaint"
}

# -------------------------
# Global focus utility
# -------------------------
async def focus_window(title_keyword: str) -> bool:
    if not gw:
        logger.warning("⚠ pygetwindow")
        return False

    await asyncio.sleep(1.5)  # Give time for window to appear
    title_keyword = title_keyword.lower().strip()

    for window in gw.getAllWindows():
        if title_keyword in window.title.lower():
            if window.isMinimized:
                window.restore()
            window.activate()
            return True
    return False

# Index files/folders
async def index_items(base_dirs):
    # Fast shallow index (do NOT crawl 200,000 files in entire drives!)
    item_index = []
    for base_dir in base_dirs:
        try:
            if not os.path.exists(base_dir):
                continue
            with os.scandir(base_dir) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        item_index.append({"name": entry.name, "path": entry.path, "type": "folder"})
                    elif entry.is_file(follow_symlinks=False):
                        item_index.append({"name": entry.name, "path": entry.path, "type": "file"})
        except Exception:
            pass
    return item_index

async def search_item(query, index, item_type):
    filtered = [item for item in index if item["type"] == item_type]
    choices = [item["name"] for item in filtered]
    if not choices:
        return None
    best_match, score = process.extractOne(query, choices)
    logger.info(f"🔍 Matched '{query}' to '{best_match}' with score {score}")
    if score > 70:
        for item in filtered:
            if item["name"] == best_match:
                return item
    return None

# File/folder actions
async def open_folder(path):
    try:
        os.startfile(path) if os.name == 'nt' else subprocess.call(['xdg-open', path])
        await focus_window(os.path.basename(path))
    except Exception as e:
        logger.error(f"❌ फ़ाइल open करने में error आया। {e}")

async def play_file(path):
    try:
        os.startfile(path) if os.name == 'nt' else subprocess.call(['xdg-open', path])
        await focus_window(os.path.basename(path))
    except Exception as e:
        logger.error(f"❌ फ़ाइल open करने में error आया।: {e}")

async def create_folder(path):
    try:
        os.makedirs(path, exist_ok=True)
        return f"✅ Folder create हो गया।: {path}"
    except Exception as e:
        return f"❌ फ़ाइल create करने में error आया।: {e}"

async def rename_item(old_path, new_path):
    try:
        os.rename(old_path, new_path)
        return f"✅ नाम बदलकर {new_path} कर दिया गया।"
    except Exception as e:
        return f"❌ नाम बदलना fail हो गया: {e}"

async def delete_item(path, confirmed: bool = False):
    if not confirmed:
        return f"[CONFIRMATION REQUIRED] Deleting files or folders is permanent. Ask Boss: 'Amar Babu, tumi ki shotti {path} delete korte chao? Confirm korle bolo.'"
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return f"[SUCCESS] Permanently deleted: {path}"
    except Exception as e:
        return f"[ERROR] Failed to delete: {e}"

@function_tool()
async def open_app(app_title: str) -> str:
    """
    Opens ANY installed application, software, game, or tool on Windows (e.g. Chrome, Discord, Notepad, VS Code, Roblox, Minecraft, Spotify, Steam, File Explorer, Calculator, etc.).
    Uses a bulletproof 4-layer launch engine:
    1. Known direct process/alias launch (e.g. chrome, code, notepad, explorer, spotify, discord).
    2. Protocol/URI schemes (e.g. roblox://, steam://, ms-settings:).
    3. Windows Start Menu & Installed App Shortcuts (.lnk) quick search.
    4. Fallback OS start command and AppID launcher.
    """
    import subprocess
    import os
    import json

    app_clean = app_title.lower().strip()
    for prefix in ["open ", "start ", "launch ", "run "]:
        if app_clean.startswith(prefix):
            app_clean = app_clean[len(prefix):].strip()

    # 1. Direct executable / common command mappings
    direct_commands = {
        "chrome": "start chrome",
        "google chrome": "start chrome",
        "browser": "start chrome",
        "edge": "start msedge",
        "microsoft edge": "start msedge",
        "firefox": "start firefox",
        "brave": "start brave",
        "notepad": "notepad",
        "calculator": "calc",
        "calc": "calc",
        "explorer": "explorer",
        "file explorer": "explorer",
        "files": "explorer",
        "this pc": "explorer ::{20D04FE0-3AEA-1069-A2D8-08002B30309D}",
        "downloads": "explorer shell:Downloads",
        "documents": "explorer shell:Personal",
        "desktop": "explorer shell:Desktop",
        "cmd": "start cmd",
        "command prompt": "start cmd",
        "terminal": "start wt",
        "powershell": "start powershell",
        "paint": "mspaint",
        "task manager": "taskmgr",
        "taskmgr": "taskmgr",
        "control panel": "control",
        "settings": "start ms-settings:",
        "discord": "start discord:",
        "spotify": "start spotify:",
        "steam": "start steam:",
        "roblox": "start roblox:",
        "vscode": "code",
        "code": "code",
        "vs code": "code",
    }

    if app_clean in direct_commands:
        try:
            cmd = direct_commands[app_clean]
            subprocess.Popen(cmd, shell=True)
            await asyncio.sleep(1.0)
            await focus_window(app_clean)
            return f"Successfully opened {app_title}."
        except Exception as e:
            logger.warning(f"Direct command failed for {app_clean}: {e}")

    # 2. Protocol lookup
    protocol_map = {
        "roblox": "roblox://",
        "steam": "steam://",
        "discord": "discord://",
        "spotify": "spotify://",
        "settings": "ms-settings:",
    }
    for k, proto in protocol_map.items():
        if k in app_clean:
            try:
                os.startfile(proto)
                await asyncio.sleep(1.0)
                await focus_window(k)
                return f"Successfully opened {app_title}."
            except Exception:
                pass

    # 3. Windows Start Menu Shortcuts search (.lnk)
    try:
        appdata_dir = os.environ.get("APPDATA", "")
        programdata_dir = os.environ.get("ALLUSERSPROFILE", "")
        start_menu_dirs = [
            os.path.join(appdata_dir, "Microsoft", "Windows", "Start Menu", "Programs"),
            os.path.join(programdata_dir, "Microsoft", "Windows", "Start Menu", "Programs")
        ]
        matched_lnk = None
        for sm_dir in start_menu_dirs:
            if not os.path.exists(sm_dir):
                continue
            for root, _, files in os.walk(sm_dir):
                for f in files:
                    if f.lower().endswith(".lnk") and app_clean in f.lower():
                        matched_lnk = os.path.join(root, f)
                        break
                if matched_lnk:
                    break
            if matched_lnk:
                break

        if matched_lnk:
            os.startfile(matched_lnk)
            await asyncio.sleep(1.0)
            await focus_window(app_clean)
            return f"Successfully opened {app_title}."
    except Exception as e:
        logger.warning(f"Start Menu link search error: {e}")

    # 4. Fallback: OS start command
    try:
        subprocess.Popen(f'start "" "{app_clean}"', shell=True)
        await asyncio.sleep(1.0)
        await focus_window(app_clean)
        return f"Successfully opened {app_title}."
    except Exception as e:
        logger.error(f"Failed to open app {app_title}: {e}")
        return f"Could not launch {app_title}. Error: {e}"

APP_PROCESS_MAP = {
    "chrome": ["chrome.exe"],
    "google chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "microsoft edge": ["msedge.exe"],
    "firefox": ["firefox.exe"],
    "brave": ["brave.exe"],
    "notepad": ["notepad.exe"],
    "calculator": ["CalculatorApp.exe", "calc.exe"],
    "calc": ["CalculatorApp.exe", "calc.exe"],
    "vlc": ["vlc.exe"],
    "spotify": ["Spotify.exe"],
    "word": ["WINWORD.EXE"],
    "excel": ["EXCEL.EXE"],
    "powerpoint": ["POWERPNT.EXE"],
    "code": ["Code.exe"],
    "vscode": ["Code.exe"],
    "vs code": ["Code.exe"],
    "discord": ["Discord.exe"],
    "cmd": ["cmd.exe"],
    "command prompt": ["cmd.exe"],
    "powershell": ["powershell.exe", "pwsh.exe"],
    "explorer": ["explorer.exe"],
    "file explorer": ["explorer.exe"],
    "paint": ["mspaint.exe"],
    "task manager": ["Taskmgr.exe"],
    "steam": ["steam.exe"],
    "telegram": ["Telegram.exe"],
    "whatsapp": ["WhatsApp.exe"],
}

@function_tool()
async def close_app(window_title: str) -> str:
    """
    Closes an open application window or running desktop software by its title or name.

    Use this tool when the user asks to close any app, window, or program.
    Example prompts:
    - 'Notepad bondho koro' / 'Close notepad'
    - 'Chrome close koro' / 'Close Chrome'
    - 'VLC close kore dao'
    - 'Close calculator'
    """
    target = window_title.strip().lower()
    closed_count = 0
    closed_names = []

    # 1. Graceful window close via win32gui WM_CLOSE
    if win32gui and win32con:
        def enum_handler(hwnd, _):
            nonlocal closed_count
            try:
                if win32gui.IsWindowVisible(hwnd):
                    text = win32gui.GetWindowText(hwnd).strip()
                    if text and (target in text.lower() or any(k in target and k in text.lower() for k in APP_PROCESS_MAP)):
                        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                        closed_count += 1
                        closed_names.append(text[:30])
            except Exception:
                pass

        try:
            win32gui.EnumWindows(enum_handler, None)
        except Exception as e:
            logger.warning(f"Error enumerating windows: {e}")

    # 2. Process-level termination fallback if recognized app or if graceful close didn't close enough
    matched_procs = []
    for app_key, procs in APP_PROCESS_MAP.items():
        if app_key in target or target in app_key:
            matched_procs.extend(procs)

    if matched_procs:
        for proc in set(matched_procs):
            try:
                res = subprocess.run(
                    ["taskkill", "/F", "/IM", proc],
                    capture_output=True,
                    text=True
                )
                if res.returncode == 0:
                    closed_count += 1
                    closed_names.append(proc)
            except Exception:
                pass

    if closed_count > 0:
        names_str = ", ".join(set(closed_names)) if closed_names else target
        return f"[SUCCESS] Closed '{window_title}' successfully ({names_str})."
    else:
        return f"[NOT FOUND] Could not find any open window or running process for '{window_title}'. Please ensure it is currently open."

@function_tool()
async def folder_file(command: str, confirmed: bool = False) -> str:
    """
    Manages and opens folders and files on your PC like a human user.
    Supports opening Downloads, Documents, Desktop, Pictures, Minecraft drive, or any folder name.
    """
    user_profile = os.environ.get('USERPROFILE') or str(Path.home())
    cmd_lower = command.lower().strip()

    # Fast direct path lookup
    direct_paths = {
        "downloads": os.path.join(user_profile, "Downloads"),
        "download": os.path.join(user_profile, "Downloads"),
        "documents": os.path.join(user_profile, "Documents"),
        "document": os.path.join(user_profile, "Documents"),
        "desktop": os.path.join(user_profile, "Desktop"),
        "pictures": os.path.join(user_profile, "Pictures"),
        "photos": os.path.join(user_profile, "Pictures"),
        "music": os.path.join(user_profile, "Music"),
        "videos": os.path.join(user_profile, "Videos"),
        "file manager": user_profile,
        "file explorer": user_profile,
        "explorer": user_profile,
        "this pc": "::{20D04FE0-3AEA-1069-A2D8-08002B30309D}",
        "minecraft": "F:\\",
    }

    for key, pth in direct_paths.items():
        if key in cmd_lower:
            if os.path.exists(pth) or key == "this pc":
                import subprocess
                subprocess.Popen(f'explorer "{pth}"', shell=True)
                await asyncio.sleep(1.0)
                await focus_window(key)
                return f"?? {key.capitalize()} ??????? ???? ??? ????? ???? ????? ????!"

    # Check drive letters like C, D, E, F, G
    for d in ["c:", "d:", "e:", "f:", "g:"]:
        if d in cmd_lower:
            drive_path = f"{d.upper()}\\"
            if os.path.exists(drive_path):
                import subprocess
                subprocess.Popen(f'explorer "{drive_path}"', shell=True)
                await asyncio.sleep(1.0)
                return f"?? {d.upper()} ?????? ???? ??? ??????!"

    # Create folder handling
    if "create folder" in cmd_lower:
        folder_name = cmd_lower.replace("create folder", "").strip()
        path = os.path.join(user_profile, "Desktop", folder_name)
        os.makedirs(path, exist_ok=True)
        return f"?? {folder_name} ??????? ???? ??? ???????"

    # General open folder fallback using explorer
    clean_target = cmd_lower.replace("folder", "").replace("open", "").replace("koro", "").strip()
    if clean_target:
        # Search Desktop and UserProfile
        for base in [os.path.join(user_profile, "Desktop"), user_profile, "F:\\", "D:\\"]:
            cand = os.path.join(base, clean_target)
            if os.path.exists(cand):
                import subprocess
                subprocess.Popen(f'explorer "{cand}"', shell=True)
                await asyncio.sleep(1.0)
                return f"?? {clean_target} ??????? ???? ??? ????? ???? ?????!"

    # Default fallback: open Windows File Explorer
    import subprocess
    subprocess.Popen('explorer', shell=True)
    return "?? ???? ????????? ???? ??? ?????? ????!"


@function_tool()
async def close_app(window_title: str) -> str:
    """
    Closes an open application window or running desktop software by its title or name.

    Use this tool when the user asks to close any app, window, or program.
    Example prompts:
    - 'Notepad bondho koro' / 'Close notepad'
    - 'Chrome close koro' / 'Close Chrome'
    - 'VLC close kore dao'
    - 'Close calculator'
    """
    target = window_title.strip().lower()
    closed_count = 0
    closed_names = []

    # 1. Graceful window close via win32gui WM_CLOSE
    if win32gui and win32con:
        def enum_handler(hwnd, _):
            nonlocal closed_count
            try:
                if win32gui.IsWindowVisible(hwnd):
                    text = win32gui.GetWindowText(hwnd).strip()
                    if text and (target in text.lower() or any(k in target and k in text.lower() for k in APP_PROCESS_MAP)):
                        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                        closed_count += 1
                        closed_names.append(text[:30])
            except Exception:
                pass

        try:
            win32gui.EnumWindows(enum_handler, None)
        except Exception as e:
            logger.warning(f"Error enumerating windows: {e}")

    # 2. Process-level termination fallback if recognized app or if graceful close didn't close enough
    matched_procs = []
    for app_key, procs in APP_PROCESS_MAP.items():
        if app_key in target or target in app_key:
            matched_procs.extend(procs)

    if matched_procs:
        for proc in set(matched_procs):
            try:
                res = subprocess.run(
                    ["taskkill", "/F", "/IM", proc],
                    capture_output=True,
                    text=True
                )
                if res.returncode == 0:
                    closed_count += 1
                    closed_names.append(proc)
            except Exception:
                pass

    if closed_count > 0:
        names_str = ", ".join(set(closed_names)) if closed_names else target
        return f"[SUCCESS] Closed '{window_title}' successfully ({names_str})."
    else:
        return f"[NOT FOUND] Could not find any open window or running process for '{window_title}'. Please ensure it is currently open."

@function_tool()
async def folder_file(command: str, confirmed: bool = False) -> str:

    """
    Handles folder and file actions like open, create, rename, or delete based on user command.

    Use this tool when the user wants to manage folders or files using natural language.
    Example prompts:
    - "Projects folder बनाओ"
    - "OldName को NewName में rename करो"
    - "xyz.mp4 delete कर दो"
    - "Music folder खोलो"
    - "Resume.pdf चलाओ"
    """


    # Dynamically find common user folders
    user_profile = os.environ.get('USERPROFILE')
    folders_to_index = []
    if user_profile:
        for folder in ["Downloads", "Documents", "Desktop", "Pictures", "Music", "Videos"]:
            path = os.path.join(user_profile, folder)
            if os.path.exists(path):
                folders_to_index.append(path)
    
    # Add other drives if they exist
    for drive in ["D:/", "E:/", "F:/"]:
        if os.path.exists(drive):
            folders_to_index.append(drive)

    index = await index_items(folders_to_index)
    command_lower = command.lower()

    if "create folder" in command_lower:
        folder_name = command.replace("create folder", "").strip()
        # Default to Desktop if profile found, else D:/
        base = os.path.join(user_profile, "Desktop") if user_profile else "D:/"
        path = os.path.join(base, folder_name)
        return await create_folder(path)

    if "rename" in command_lower:
        parts = command_lower.replace("rename", "").strip().split("to")
        if len(parts) == 2:
            old_name = parts[0].strip()
            new_name = parts[1].strip()
            item = await search_item(old_name, index, "folder")
            if item:
                new_path = os.path.join(os.path.dirname(item["path"]), new_name)
                return await rename_item(item["path"], new_path)
        return "❌ rename command valid नहीं है।"

    if "delete" in command_lower:
        item = await search_item(command, index, "folder") or await search_item(command, index, "file")
        if item:
            is_confirmed = any(w in command_lower for w in ("confirm", "yes", "haan", "ha", "sure", "kore dao", "pakka")) or confirmed
            return await delete_item(item["path"], confirmed=is_confirmed)
        return "❌ Delete korar jonno item paoa jayni."

    if "folder" in command_lower or "open folder" in command_lower:
        item = await search_item(command, index, "folder")
        if item:
            await open_folder(item["path"])
            return f"✅ Folder opened: {item['name']}"
        return "❌ Folder नहीं मिला।."

    item = await search_item(command, index, "file")
    if item:
        await play_file(item["path"])
        return f"✅ File opened: {item['name']}"

    return "⚠ कुछ भी match नहीं हुआ।"

@function_tool()
async def send_whatsapp_message(contact_name: str, message: str, confirmed: bool = False) -> str:
    if not confirmed:
        return f"[CONFIRMATION REQUIRED] Sending WhatsApp message to '{contact_name}' with text: '{message}'. Please ask Boss: 'Amar Babu, ami ki {contact_name}-ke ei message ta pathiye debo? Confirm korle bolo.'"
    """
    Sends a WhatsApp message to a specific contact automatically.
    
    Use this tool when the user says something like:
    - "Send a message on WhatsApp to Nahian MC saying hello"
    - "WhatsApp pe Rahul ko message karo 'I am busy'"
    
    Args:
        contact_name (str): The exact name of the contact as saved in WhatsApp.
        message (str): The message content to send.
    """
    import pyautogui
    import asyncio
    try:
        # Open WhatsApp
        await asyncio.create_subprocess_shell('start whatsapp:', shell=True)
        await asyncio.sleep(4)  # Wait for WhatsApp to open and load fully
        
        # Focus search bar
        pyautogui.hotkey('ctrl', 'f')
        await asyncio.sleep(0.5)
        
        # Type contact name
        pyautogui.write(contact_name)
        await asyncio.sleep(2)  # Wait for search results
        
        # Select the first result and open chat
        pyautogui.press('down')
        await asyncio.sleep(0.5)
        pyautogui.press('enter')
        await asyncio.sleep(1)
        
        # Type the message
        pyautogui.write(message)
        await asyncio.sleep(0.5)
        
        # Press Enter to send
        pyautogui.press('enter')
        
        return f"✅ Message '{message}' successfully sent to {contact_name} on WhatsApp."
    except Exception as e:
        return f"❌ Failed to send WhatsApp message: {e}"

@function_tool()
async def google_maps_tool(query: str, auto_navigate: bool = False) -> str:
    """
    Opens Google Maps for a specific search.
    If auto_navigate is True, it starts the navigation to the destination.
    """
    import webbrowser
    import pyautogui
    import asyncio
    
    if auto_navigate:
        url = f"https://www.google.com/maps/dir/?api=1&destination={query.replace(' ', '+')}"
    else:
        url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        
    webbrowser.open(url)
    
    if auto_navigate:
        await asyncio.sleep(5)
        pyautogui.press('enter') # Often needed to confirm route
        return f"🚀 Starting navigation to: {query}"
    
    return f"🚀 Google Maps opened for: {query}"

@function_tool()
async def gmail_send_tool(recipient: str, subject: str, body: str, auto_send: bool = True, confirmed: bool = False) -> str:
    if not confirmed:
        return f"[CONFIRMATION REQUIRED] Sending email to '{recipient}' with subject '{subject}'. Please ask Boss: 'Amar Babu, ami ki {recipient}-ke email ta pathiye debo? Confirm korle bolo.'"
    """
    Automates sending an email via Gmail.
    Opens the browser, fills the data, and automatically presses Send if auto_send is True.
    """
    import webbrowser
    import urllib.parse
    import pyautogui
    import asyncio
    
    base_url = "https://mail.google.com/mail/?view=cm&fs=1"
    params = []
    if recipient: params.append(f"to={urllib.parse.quote(recipient)}")
    if subject: params.append(f"su={urllib.parse.quote(subject)}")
    if body: params.append(f"body={urllib.parse.quote(body)}")
    
    final_url = base_url + ("&" + "&".join(params) if params else "")
    webbrowser.open(final_url)
    
    if auto_send:
        print("⏳ Waiting for Gmail to load before sending...")
        await asyncio.sleep(8) # Wait for UI to load fully
        pyautogui.hotkey('ctrl', 'enter')
        return f"✅ Email to {recipient} has been automatically typed and sent!"
    
    return f"🚀 Gmail compose window ready for {recipient}. You can check and click Send."

@function_tool()
async def shutdown_pc(confirmed: bool = False) -> str:
    """
    Shuts down the computer.
    CRITICAL SAFETY REQUIREMENT: You must ask the user for confirmation BEFORE calling this tool with confirmed=True!
    If the user has not confirmed yet, do NOT call this tool; ask them: 'Are you sure you want to shut down your PC?'
    Only pass confirmed=True when the user explicitly says 'Yes', 'Confirm', 'Kore dao', or 'Haan'.
    """
    if not confirmed:
        return "Please ask user for confirmation before shutting down."
    try:
        os.system("shutdown /s /t 10")
        return "[OK] PC will shut down in 10 seconds. Call cancel_shutdown if needed."
    except Exception as e:
        return f"[FAIL] Shutdown failed: {e}"

@function_tool()
async def restart_pc(confirmed: bool = False) -> str:
    """
    Restarts the computer.
    CRITICAL SAFETY REQUIREMENT: You must ask the user for confirmation BEFORE calling this tool with confirmed=True!
    If the user has not confirmed yet, do NOT call this tool; ask them: 'Are you sure you want to restart your PC?'
    Only pass confirmed=True when the user explicitly says 'Yes', 'Confirm', 'Kore dao', or 'Haan'.
    """
    if not confirmed:
        return "Please ask user for confirmation before restarting."
    try:
        os.system("shutdown /r /t 10")
        return "[OK] PC will restart in 10 seconds. Call cancel_shutdown if needed."
    except Exception as e:
        return f"[FAIL] Restart failed: {e}"

@function_tool()
async def lock_pc() -> str:
    """
    Locks the computer screen.
    Use this when the user says 'PC lock koro', 'Lock my PC', 'Screen lock karo', 
    'Lock screen', etc.
    """
    try:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return "🔒 PC is now locked."
    except Exception as e:
        return f"❌ Lock failed: {e}"

@function_tool()
async def cancel_shutdown() -> str:
    """
    Cancels a pending shutdown or restart.
    Use this when the user says 'Shutdown cancel koro', 'Cancel shutdown', 
    'Restart cancel karo', 'Stop shutdown', etc.
    """
    try:
        os.system("shutdown /a")
        return "✅ Shutdown/Restart has been cancelled."
    except Exception as e:
        return f"❌ Cancel failed: {e}"

