import os
import sys
import time
import asyncio
import logging
import subprocess
from pathlib import Path
import requests

from nion_auth import (
    get_saved_license,
    FIREBASE_REST_URL,
    FIREBASE_API_KEY,
    MASTER_KEY,
    LICENSE_FILE
)

logger = logging.getLogger("Zora_LicenseWatcher")
logger.setLevel(logging.INFO)


def _show_inactive_console_and_exit(reason: str = "License is inactive"):
    """
    Terminates the current running session and launches a dedicated CMD window
    displaying the full official Zora AI Assistant banner with the STOP badge
    and the explicit message that the license is inactive by admin or owner.
    Guaranteed NEVER to auto-close: uses a robust .bat script with cmd /k and pause.
    """
    import base64
    temp_dir = Path.home() / ".zoraai"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_py = temp_dir / "show_inactive.py"
    temp_bat = temp_dir / "show_inactive.bat"

    template_b64 = b'aW1wb3J0IG9zLCBzeXMsIGRhdGV0aW1lLCBzb2NrZXQsIHBsYXRmb3JtLCBqc29uDQp0cnk6DQogICAgb3Muc3lzdGVtKCIiKQ0KICAgIHN5cy5zdGRvdXQucmVjb25maWd1cmUoZW5jb2Rpbmc9InV0Zi04IiwgZXJyb3JzPSJyZXBsYWNlIikNCiAgICBzeXMuc3RkZXJyLnJlY29uZmlndXJlKGVuY29kaW5nPSJ1dGYtOCIsIGVycm9ycz0icmVwbGFjZSIpDQpleGNlcHQgRXhjZXB0aW9uOg0KICAgIHBhc3MNCg0KUkVEID0gIlwwMzNbMzg7NTsxOTZtIg0KQ1lBTiA9ICJcMDMzWzM4OzU7NzVtIg0KUFVSUExFID0gIlwwMzNbMzg7NTsxNDFtIg0KTUFHRU5UQSA9ICJcMDMzWzM4OzU7MTc3bSINCkdSRUVOID0gIlwwMzNbMzg7NTs4Mm0iDQpZRUxMT1cgPSAiXDAzM1szODs1OzIyMG0iDQpXSElURSA9ICJcMDMzWzk3bSINCkdSQVkgPSAiXDAzM1s5MG0iDQpSRVNFVCA9ICJcMDMzWzBtIg0KQk9MRCA9ICJcMDMzWzFtIg0KDQpCR19HUkVFTiA9ICJcMDMzWzQ4OzU7NDBtXDAzM1szMG1cMDMzWzFtIg0KQkdfUkVEID0gIlwwMzNbNDg7NTsxOTZtXDAzM1s5N21cMDMzWzFtIg0KQkdfQkxVRSA9ICJcMDMzWzQ4OzU7MzNtXDAzM1s5N21cMDMzWzFtIg0KQkdfWUVMTE9XID0gIlwwMzNbNDg7NTsyMTRtXDAzM1szMG1cMDMzWzFtIg0KQkdfUFVSUExFID0gIlwwMzNbNDg7NTsxMjltXDAzM1s5N21cMDMzWzFtIg0KDQpkZWYgX21hc2tfa2V5KGtleTogc3RyKSAtPiBzdHI6DQogICAgaWYgbm90IGtleSBvciBsZW4oa2V5KSA8IDg6DQogICAgICAgIHJldHVybiBrZXkgb3IgIiINCiAgICBwYXJ0cyA9IGtleS5zcGxpdCgiLSIpDQogICAgaWYgbGVuKHBhcnRzKSA+PSA0Og0KICAgICAgICByZXR1cm4gZiJ7cGFydHNbMF19LXtwYXJ0c1sxXX0tKioqKi17cGFydHNbLTFdfSINCiAgICBlbGlmIGxlbihwYXJ0cykgPT0gMzoNCiAgICAgICAgcmV0dXJuIGYie3BhcnRzWzBdfS0qKioqLXtwYXJ0c1stMV19Ig0KICAgIHJldHVybiBrZXlbOjRdICsgIi0qKioqLSIgKyBrZXlbLTQ6XQ0KDQpkZWYgX3ByaW50X3pvcmFfYmFubmVyKGJhZGdlX2FjdGlvbjogc3RyID0gTm9uZSwgYmFkZ2VfbXNnOiBzdHIgPSBOb25lKToNCiAgICB0cnk6DQogICAgICAgIGZyb20gbmlvbl9hdXRoIGltcG9ydCBnZXRfYWlfbmFtZSwgZ2V0X3VzZXJfbmFtZSwgZ2V0X3NhdmVkX2xpY2Vuc2UNCiAgICAgICAgYWlfbmFtZSA9IGdldF9haV9uYW1lKCkgb3IgIlpvcmEiDQogICAgICAgIHVzZXJfbmFtZSA9IGdldF91c2VyX25hbWUoKSBvciAiTmVvbiINCiAgICAgICAgc2F2ZWQgPSBnZXRfc2F2ZWRfbGljZW5zZSgpIG9yIHt9DQogICAgICAgIGxpY19rZXkgPSBzYXZlZC5nZXQoImtleSIsICJOTy1MSUNFTlNFLUtFWSIpDQogICAgICAgIGxpY19wbGFuID0gc2F2ZWQuZ2V0KCJwbGFuIiwgIlBybyIpDQogICAgZXhjZXB0IEV4Y2VwdGlvbjoNCiAgICAgICAgYWlfbmFtZSA9ICJab3JhIg0KICAgICAgICB1c2VyX25hbWUgPSAiTmVvbiINCiAgICAgICAgbGljX2tleSA9ICJOTy1MSUNFTlNFLUtFWSINCiAgICAgICAgbGljX3BsYW4gPSAiUHJvIg0KDQogICAgdHJ5Og0KICAgICAgICBpbXBvcnQgcHN1dGlsDQogICAgICAgIHJhbV9nYiA9IHJvdW5kKHBzdXRpbC52aXJ0dWFsX21lbW9yeSgpLnRvdGFsIC8gKDEwMjQqKjMpKQ0KICAgICAgICByYW1fc3RyID0gZiJ7cmFtX2difSBHQiINCiAgICAgICAgY29yZXMgPSBwc3V0aWwuY3B1X2NvdW50KGxvZ2ljYWw9RmFsc2UpIG9yIHBzdXRpbC5jcHVfY291bnQoKSBvciA0DQogICAgICAgIGNwdV9uYW1lID0gcGxhdGZvcm0ucHJvY2Vzc29yKCkgb3IgIkludGVsKFIpIg0KICAgICAgICBjcHVfc2hvcnQgPSAiSW50ZWwoUikiIGlmICJpbnRlbCIgaW4gY3B1X25hbWUubG93ZXIoKSBlbHNlICgiQU1EIiBpZiAiYW1kIiBpbiBjcHVfbmFtZS5sb3dlcigpIGVsc2UgIng4Nl82NCIpDQogICAgICAgIGNwdV9zdHIgPSBmIntjb3Jlc314IHtjcHVfc2hvcnR9Ig0KICAgIGV4Y2VwdCBFeGNlcHRpb246DQogICAgICAgIHJhbV9zdHIgPSAiMTYgR0IiDQogICAgICAgIGNwdV9zdHIgPSAiNHggSW50ZWwoUikiDQoNCiAgICBob3N0bmFtZSA9IHNvY2tldC5nZXRob3N0bmFtZSgpDQogICAgcGxhdCA9IGYie3N5cy5wbGF0Zm9ybX0gKHtwbGF0Zm9ybS5tYWNoaW5lKCl9KSINCiAgICB2ZXJzaW9uID0gIjEuOC40Ig0KDQogICAgYmFubmVyID0gZiIiIg0Ke0NZQU59e0JPTER9ICAgICDilojilojilojilojilojilojilojilZcg4paI4paI4paI4paI4paI4paI4pWXIOKWiOKWiOKWiOKWiOKWiOKWiOKVlyAg4paI4paI4paI4paI4paI4pWXICAgICAgIOKWiOKWiOKWiOKWiOKWiOKVlyDilojilojilZcNCiAgICAg4pWa4pWQ4pWQ4paI4paI4paI4pWU4pWd4paI4paI4pWU4pWQ4pWQ4pWQ4paI4paI4pWX4paI4paI4pWU4pWQ4pWQ4paI4paI4pWX4paI4paI4pWU4pWQ4pWQ4paI4paI4pWXICAgICDilojilojilZTilZDilZDilojilojilZfilojilojilZENCiAgICAgICDilojilojilojilZTilZ0g4paI4paI4pWRICAg4paI4paI4pWR4paI4paI4paI4paI4paI4paI4pWU4pWd4paI4paI4paI4paI4paI4paI4paI4pWRICAgICDilojilojilojilojilojilojilojilZHilojilojilZENCiAgICAgIOKWiOKWiOKWiOKVlOKVnSAg4paI4paI4pWRICAg4paI4paI4pWR4paI4paI4pWU4pWQ4pWQ4paI4paI4pWX4paI4paI4pWU4pWQ4pWQ4paI4paI4pWRICAgICDilojilojilZTilZDilZDilojilojilZHilojilojilZENCiAgICAg4paI4paI4paI4paI4paI4paI4paI4pWX4pWa4paI4paI4paI4paI4paI4paI4pWU4pWd4paI4paI4pWRICDilojilojilZHilojilojilZEgIOKWiOKWiOKVkSAgICAg4paI4paI4pWRICDilojilojilZHilojilojilZENCiAgICAg4pWa4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWdIOKVmuKVkOKVkOKVkOKVkOKVkOKVnSDilZrilZDilZ0gIOKVmuKVkOKVneKVmuKVkOKVnSAg4pWa4pWQ4pWdICAgICDilZrilZDilZ0gIOKVmuKVkOKVneKVmuKVkOKVnXtSRVNFVH0NCiAgICAgICAgICAgIHtXSElURX17Qk9MRH1aIE8gUiBBICAgQSBJICAgQSBTIFMgSSBTIFQgQSBOIFQgICB2e3ZlcnNpb259e1JFU0VUfQ0KDQp7R1JBWX3ilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIB7UkVTRVR9DQogIHtXSElURX1DcmVhdG9ye1JFU0VUfSAgICAgICAgIHtQVVJQTEV9e0JPTER9TmVvbntSRVNFVH0NCiAge1dISVRFfVZlcnNpb257UkVTRVR9ICAgICAgICAge0NZQU59dnt2ZXJzaW9ufXtSRVNFVH0NCiAge1dISVRFfUFJIE5hbWV7UkVTRVR9ICAgICAgICAge0NZQU59e2FpX25hbWV9e1JFU0VUfQ0KICB7V0hJVEV9VXNlciBOYW1le1JFU0VUfSAgICAgICB7R1JFRU59e3VzZXJfbmFtZX17UkVTRVR9DQogIHtXSElURX1MaWNlbnNlIEtleXtSRVNFVH0gICAgIHtZRUxMT1d9e19tYXNrX2tleShsaWNfa2V5KX17UkVTRVR9DQogIHtXSElURX1MaWNlbnNlIFN0YXR1c3tSRVNFVH0gIHtSRUR9e0JPTER9SW5hY3RpdmUgKFN1c3BlbmRlZCBieSBBZG1pbiBvciBPd25lcil7UkVTRVR9DQogIHtXSElURX1QbGF0Zm9ybXtSRVNFVH0gICAgICAgIHtDWUFOfXtwbGF0fXtSRVNFVH0NCiAge1dISVRFfUhvc3RuYW1le1JFU0VUfSAgICAgICAge01BR0VOVEF9e2hvc3RuYW1lfXtSRVNFVH0NCiAge1dISVRFfUNQVSBDb3Jlc3tSRVNFVH0gICAgICAge1lFTExPV317Y3B1X3N0cn17UkVTRVR9DQogIHtXSElURX1Ub3RhbCBSQU17UkVTRVR9ICAgICAgIHtZRUxMT1d9e3JhbV9zdHJ9e1JFU0VUfQ0Ke0dSQVl94pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSAe1JFU0VUfQ0KIiIiDQogICAgcHJpbnQoYmFubmVyKQ0KICAgIGlmIGJhZGdlX2FjdGlvbiBhbmQgYmFkZ2VfbXNnOg0KICAgICAgICBfcHJpbnRfYmFkZ2UoYmFkZ2VfYWN0aW9uLCBiYWRnZV9tc2cpDQoNCg0KDQpkZWYgX3ByaW50X2JhZGdlKGFjdGlvbjogc3RyLCBtZXNzYWdlOiBzdHIpOg0KICAgIG5vdyA9IGRhdGV0aW1lLmRhdGV0aW1lLm5vdygpLnN0cmZ0aW1lKCIlSDolTTolUyIpDQogICAgYmFkZ2UgPSBmIntCR19SRUR9ICAgU1RPUCAgIHtSRVNFVH0iDQogICAgcHJpbnQoZiJbe0dSQVl9e25vd317UkVTRVR9XSAge2JhZGdlfSAge21lc3NhZ2V9XG4iKQ0KDQppZiBfX25hbWVfXyA9PSAiX19tYWluX18iOg0KICAgIF9wcmludF96b3JhX2Jhbm5lcigiU1RPUCIsICJab3JhIEFJIGlzIFNUT1BQRUQg4oCUIExpY2Vuc2UgSW5hY3RpdmUiKQ0KICAgIHByaW50KGYiICB7UkVEfXtCT0xEfVshXSBZb3VyIGxpY2Vuc2UgaXMgaW5hY3RpdmUgYnkgYWRtaW4gb3Igb3duZXIue1JFU0VUfSIpDQogICAgcHJpbnQoZiIgIHtXSElURX1QbGVhc2UgY29udGFjdCB7UFVSUExFfXtCT0xEfU5lb257UkVTRVR9IHtXSElURX10byByZWFjdGl2YXRlIHlvdXIgbGljZW5zZS57UkVTRVR9XG4iKQ0KICAgIHRyeToNCiAgICAgICAgaW5wdXQoIiAgUHJlc3MgRW50ZXIgb3IgYW55IGtleSB0byBjbG9zZS4uLiIpDQogICAgZXhjZXB0IEV4Y2VwdGlvbjoNCiAgICAgICAgcGFzcw0K'
    temp_py.write_bytes(base64.b64decode(template_b64))

    # Create a batch file that executes the python alert and explicitly PAUSES
    # Even if Python exits or crashes, the batch file will pause and NEVER auto-close.
    bat_content = f"""@echo off
chcp 65001 >nul
title ZORA AI - LICENSE INACTIVE (SUSPENDED)
color 0C
"{sys.executable}" "{temp_py}"
echo.
echo ========================================================
echo   Zora AI License Inactive. Please contact Neon.
echo ========================================================
echo.
echo   Press any key to close this alert window...
pause >nul
exit
"""
    temp_bat.write_text(bat_content, encoding="utf-8")

    # Launch dedicated CMD alert window that stays open until a key is pressed, then cleanly exits
    subprocess.Popen(
        f'start "ZORA AI - LICENSE INACTIVE" cmd.exe /c ""{temp_bat}""',
        shell=True
    )

    # Clean local stored license file
    try:
        if LICENSE_FILE.exists():
            LICENSE_FILE.unlink()
    except Exception:
        pass

    time.sleep(1.0)
    os._exit(0)


def send_running_heartbeat():
    """Sends live running heartbeat directly to Firebase Firestore every cycle."""
    saved = get_saved_license()
    if not saved or not saved.get("key"):
        return
    clean_key = saved.get("key", "").strip().upper()
    if clean_key == MASTER_KEY:
        return

    import datetime
    try:
        doc_url = f"{FIREBASE_REST_URL}/{clean_key}?updateMask.fieldPaths=last_seen&updateMask.fieldPaths=in_use&key={FIREBASE_API_KEY}"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        payload = {
            "fields": {
                "in_use": {"booleanValue": True},
                "last_seen": {"timestampValue": now_iso}
            }
        }
        requests.patch(doc_url, json=payload, timeout=6)
    except Exception:
        pass


def check_license_status_silent() -> bool:
    """
    Silently checks license active status directly against Firebase Cloud.
    Returns True if valid & active, False if inactive/revoked.
    """
    saved = get_saved_license()
    if not saved or not saved.get("key"):
        return False

    clean_key = saved.get("key", "").strip().upper()

    # Master developer key always active
    if clean_key == MASTER_KEY:
        return True

    try:
        doc_url = f"{FIREBASE_REST_URL}/{clean_key}?key={FIREBASE_API_KEY}"
        res = requests.get(doc_url, timeout=10)
        if res.status_code == 200:
            doc_data = res.json()
            fields = doc_data.get("fields", {})
            active = fields.get("active", {}).get("booleanValue", True)
            return bool(active)
        elif res.status_code == 404:
            return False
    except Exception:
        # If temporary network glitch, do not falsely kill session
        return True

    return True


async def background_license_checker_loop():
    """
    Runs completely silently in the background every 5 minutes (300 seconds).
    If license is revoked or set to active=False:
      - Instantly terminates AI
      - Launches Zora AI themed console showing STOP badge & Neon contact info.
    """
    CHECK_INTERVAL_SECONDS = 15  # Check every 15 seconds

    while True:
        try:
            is_active = await asyncio.to_thread(check_license_status_silent)
            if not is_active:
                print("\n[LICENSE REVOCATION DETECTED] License key is INACTIVE or deactivated! Terminating Zora...\n")
                _show_inactive_console_and_exit(reason="License has been deactivated by Administrator")
            else:
                await asyncio.to_thread(send_running_heartbeat)
        except Exception as e:
            pass
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
