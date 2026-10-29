# nion_minecraft_order_manager.py
# Autonomous File & Minecraft Order Organizer for Zora AI

import os
import shutil
import zipfile
import logging
from pathlib import Path
from livekit.agents import function_tool

logger = logging.getLogger("Zora_OrderManager")
logger.setLevel(logging.INFO)

def find_drive_by_name(name_keyword: str) -> str | None:
    import psutil
    name_lower = name_keyword.lower().strip()
    # Check volume names using PowerShell / wmic
    try:
        import subprocess
        cmd = 'powershell -NoProfile -Command "Get-Volume | Select-Object DriveLetter, FriendlyName | ConvertTo-Json"'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        import json
        data = json.loads(res.stdout)
        if isinstance(data, dict):
            data = [data]
        for item in data:
            letter = item.get("DriveLetter")
            friendly = str(item.get("FriendlyName") or "").lower()
            if letter and name_lower in friendly:
                return f"{letter}:\\"
    except Exception as e:
        logger.warning(f"Error querying volumes: {e}")

    # Fallback common drives
    for d in ["F:\\", "D:\\", "E:\\", "G:\\", "C:\\"]:
        if os.path.exists(d):
            if name_lower in d.lower():
                return d
    return None

@function_tool()
async def process_minecraft_order_zip(
    order_folder_name: str = "order250$",
    drive_keyword: str = "minecraft",
    preserve_folder_name: str = "custompl"
) -> str:
    """
    Autonomous tool to handle Minecraft / Client orders.
    1. Finds the latest .zip file in user's Downloads directory.
    2. Locates the target drive (e.g. 'minecraft' drive) and the order folder (e.g. 'order250$').
    3. Cleans up the order folder EXCEPT for the preserved folder (e.g. 'custompl').
    4. Extracts the zip file completely into the order folder.
    Returns clear summary of everything done.
    """
    downloads_path = Path.home() / "Downloads"
    if not downloads_path.exists():
        return "Downloads directory not found on your system."

    # 1. Find latest zip in Downloads
    # Check explicitly for backup.zip first, else get newest zip
    target_zip = downloads_path / "backup.zip"
    if not target_zip.exists():
        zip_files = sorted(
            [f for f in downloads_path.glob("*.zip") if not f.name.startswith("crdownload")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        if not zip_files:
            return "Downloads ???????? ???? .zip ???? ????? ????? ????!"
        target_zip = zip_files[0]

    latest_zip = target_zip
    logger.info(f"Latest zip found: {latest_zip.name}")

    # 2. Locate target drive
    target_drive = find_drive_by_name(drive_keyword) or "F:\\"
    target_order_dir = Path(target_drive) / order_folder_name
    target_order_dir.mkdir(parents=True, exist_ok=True)

    # 3. Clean target order folder while keeping preserve_folder_name
    deleted_count = 0
    preserved_found = False
    for item in target_order_dir.iterdir():
        if item.name.lower() == preserve_folder_name.lower():
            preserved_found = True
            continue
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            deleted_count += 1
        except Exception as e:
            logger.warning(f"Failed to delete {item.name}: {e}")

    # 4. Extract zip directly into target_order_dir
    try:
        with zipfile.ZipFile(latest_zip, 'r') as zip_ref:
            zip_ref.extractall(target_order_dir)
    except Exception as e:
        return f"Error extracting {latest_zip.name}: {e}"

    # 5. Open the destination folder right in front of the user like a human user
    try:
        import subprocess
        subprocess.Popen(f'explorer "{target_order_dir}"', shell=True)
    except Exception:
        pass

    msg = (
        f"??????? ????? ??????? ??? ????????? ????? ???? ??? ?????? ????! Downloads ???? '{latest_zip.name}' ?????? "
        f"{target_drive}{order_folder_name} ???????? ????????????? ??? ??????, "
        f"?? '{preserve_folder_name}' ???? ???? ?????? ???????? ???? ???????"
    )
    return msg

@function_tool()
async def extract_zip_to_folder(zip_filename: str, destination_path: str) -> str:
    """Extracts any zip file to the specified destination path."""
    try:
        src = Path(zip_filename)
        if not src.exists():
            # Check in Downloads
            src = Path.home() / "Downloads" / zip_filename
        if not src.exists():
            return f"Zip file {zip_filename} not found."
        
        dest = Path(destination_path)
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(src, 'r') as z:
            z.extractall(dest)
        return f"Successfully extracted {src.name} to {dest}"
    except Exception as e:
        return f"Error extracting zip: {e}"
