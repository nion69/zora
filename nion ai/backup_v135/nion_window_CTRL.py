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
    item_index = []
    for base_dir in base_dirs:
        for root, dirs, files in os.walk(base_dir):
            for d in dirs:
                item_index.append({"name": d, "path": os.path.join(root, d), "type": "folder"})
            for f in files:
                item_index.append({"name": f, "path": os.path.join(root, f), "type": "file"})
    logger.info(f"✅ Indexed {len(item_index)} items.")
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

async def delete_item(path):
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return f"🗑️ Deleted: {path}"
    except Exception as e:
        return f"❌ Delete नहीं हुआ।: {e}"

# App control
@function_tool()
async def open_app(app_title: str) -> str:

    """
    open_app a desktop app like Notepad, Chrome, VLC, etc.

    Use this tool when the user asks to launch an application on their computer.
    Example prompts:
    - "Notepad खोलो"
    - "Chrome open करो"
    - "VLC media player चलाओ"
    - "Calculator launch करो"
    """


    app_title = app_title.lower().strip()
    app_command = APP_MAPPINGS.get(app_title)
    try:
        if app_command:
            await asyncio.create_subprocess_shell(f'start "" "{app_command}"', shell=True)
        else:
            # Dynamic fallback: Use Windows Start Menu to search and open ANY app!
            import pyautogui
            pyautogui.press('win')
            await asyncio.sleep(0.5)
            pyautogui.write(app_title)
            await asyncio.sleep(0.5)
            pyautogui.press('enter')
            
        focused = await focus_window(app_title)
        if focused:
            return f"🚀 App launch hua aur focus mein hai: {app_title}."
        else:
            return f"🚀 {app_title} Launch kiya gaya, lekin window par focus nahi ho paya."
    except Exception as e:
        return f"❌ {app_title} Launch nahi ho paya: {e}"

@function_tool()
async def close_app(window_title: str) -> str:

    """
    Closes the applications window by its title.

    Use this tool when the user wants to close any app or window on their desktop.
    Example prompts:
    - "Notepad बंद करो"
    - "Close VLC"
    - "Chrome की window बंद कर दो"
    - "Calculator को बंद करो"
    """


    if not win32gui:
        return "❌ win32gui"

    def enumHandler(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            if window_title.lower() in win32gui.GetWindowText(hwnd).lower():
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

    win32gui.EnumWindows(enumHandler, None)
    return f"❌ Window बंद हो गई है।: {window_title}"

# Jarvis command logic
@function_tool()
async def folder_file(command: str) -> str:

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
            return await delete_item(item["path"])
        return "❌ Delete करने के लिए item नहीं मिला।"

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
async def send_whatsapp_message(contact_name: str, message: str) -> str:
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
async def gmail_send_tool(recipient: str, subject: str, body: str, auto_send: bool = True) -> str:
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

