import os
import sys
import json
import requests
from pathlib import Path

# ── Verification endpoints ───────────────────────────────────────────────
# Google Cloud Firebase Firestore Project ID & API Key
FIREBASE_PROJECT_ID = "zora-4b5eb"
FIREBASE_API_KEY    = "AIzaSyD3NXUriiSzcoPpbXbglooBIiaVDsy1iig"
FIREBASE_REST_URL   = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/licenses"

# Master developer key — always works offline, no server needed (Creator: Neon)
MASTER_KEY = "ZORA-DEV-MASTER-NEON-2026"

LICENSE_DIR  = Path.home() / ".zoraai"
LICENSE_FILE = LICENSE_DIR / "license.json"


# ── Storage helpers ─────────────────────────────────────────────────────
def get_saved_license() -> dict | None:
    """Reads stored license from client's machine."""
    if LICENSE_FILE.exists():
        try:
            return json.loads(LICENSE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def save_license(key: str, client_name: str, plan: str, user_name: str = None, ai_name: str = None):
    """Saves verified license, user's preferred name, and custom AI name locally."""
    LICENSE_DIR.mkdir(parents=True, exist_ok=True)
    existing = get_saved_license() or {}
    ai = ai_name or existing.get("ai_name") or "Zora"
    data = {
        "key": key,
        "client": client_name,
        "plan": plan,
        "user_name": user_name or existing.get("user_name") or client_name,
        "ai_name": ai,
        "creator": "Neon"
    }
    LICENSE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    
    # Also update config.json for quick fallback
    try:
        cfg_path = Path.home() / ".zoraai" / "config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
        cfg["AI_NAME"] = ai
        if user_name:
            cfg["USER_NAME"] = user_name
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception:
        pass


def get_voice() -> str:
    """Returns configured voice (default: Aoede for fastest human expressive voice)."""
    saved = get_saved_license()
    if saved and saved.get("voice"):
        return saved["voice"]
    try:
        cfg_path = Path.home() / ".zoraai" / "config.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            if cfg.get("VOICE"):
                return cfg["VOICE"]
    except Exception:
        pass
    return "Leda"


def set_voice(voice_name: str) -> str:
    """Sets custom voice."""
    v = voice_name.strip() if voice_name else "Leda"
    saved = get_saved_license() or {}
    saved["voice"] = v
    LICENSE_DIR.mkdir(parents=True, exist_ok=True)
    LICENSE_FILE.write_text(json.dumps(saved, indent=2), encoding="utf-8")
    try:
        cfg_path = Path.home() / ".zoraai" / "config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
        cfg["VOICE"] = v
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception:
        pass
    return v


def get_ai_name() -> str:
    """Returns the AI's configured name (default: Zora)."""
    saved = get_saved_license()
    if saved and saved.get("ai_name"):
        return saved["ai_name"]
    try:
        cfg_path = Path.home() / ".zoraai" / "config.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            if cfg.get("AI_NAME"):
                return cfg["AI_NAME"]
    except Exception:
        pass
    return "Zora"


def set_ai_name(new_name: str) -> str:
    """Sets a custom AI name."""
    name = new_name.strip() if new_name and new_name.strip() else "Zora"
    saved = get_saved_license() or {}
    key = saved.get("key", "ZORA-DEV-MASTER-NEON-2026")
    client = saved.get("client", "User")
    plan = saved.get("plan", "Pro")
    user = saved.get("user_name", "Babu")
    save_license(key, client, plan, user_name=user, ai_name=name)
    return name


def get_user_name() -> str:
    """
    Returns the user's name (the boyfriend/friend Zora talks to).
    Note: Creator is ALWAYS Neon.
    """
    saved = get_saved_license()
    if saved and saved.get("user_name"):
        return saved["user_name"]
    if saved and saved.get("client") and not saved["client"].startswith("Developer"):
        return saved["client"].split()[0]

    try:
        cfg_path = Path.home() / ".zoraai" / "config.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            if cfg.get("USER_NAME"):
                return cfg["USER_NAME"]
    except Exception:
        pass

    return "Babu"


# ── Core Firebase Verification ──────────────────────────────────────────
def verify_key_online(key: str) -> tuple[bool, str]:
    """
    Verifies license key directly against Google Firebase Firestore cloud.
    Works from ANY computer worldwide with 0 backend servers.
    """
    clean_key = key.strip().upper()
    if not clean_key:
        return False, "Key cannot be empty."

    # Master developer key (Creator: Neon)
    if clean_key == MASTER_KEY:
        return True, "Neon (Creator)"

    # Check directly with Google Cloud Firestore REST API
    try:
        doc_url = f"{FIREBASE_REST_URL}/{clean_key}?key={FIREBASE_API_KEY}"
        res = requests.get(doc_url, timeout=7)
        
        if res.status_code == 200:
            doc_data = res.json()
            fields = doc_data.get("fields", {})
            
            client = fields.get("client", {}).get("stringValue", "Friend")
            plan   = fields.get("plan", {}).get("stringValue", "Pro")
            active = fields.get("active", {}).get("booleanValue", True)

            if not active:
                return False, "This license has been revoked or paused."

            return True, f"{client} ({plan})"
            
        elif res.status_code == 404:
            return False, "License key does not exist. Please check your key."
        elif res.status_code == 403:
            # If rules not yet switched to test mode, fallback to offline check if saved
            pass
    except Exception:
        pass

    # Only allow offline fallback if network is completely unreachable, NOT if Firestore responded with active=False
    return False, "Could not verify license key with Google Firebase cloud."

    return False, "Could not verify license key with Google Firebase. Please check your internet connection."


# ── Main prompt flow ────────────────────────────────────────────────────
def verify_or_prompt_user() -> bool:
    """
    Checks stored license first. If valid, skips prompt entirely.
    Otherwise asks user to enter license key AND asks what Zora should call them.
    """
    saved = get_saved_license()
    if saved and saved.get("key"):
        valid, info = verify_key_online(saved["key"])
        if valid:
            name_display = saved.get("user_name") or info
            print(f"[Zora AI] License Active — Welcome back, {name_display} (Created by Neon)")
            return True
        else:
            print(f"[Zora AI] Stored key is no longer valid: {info}")
            if LICENSE_FILE.exists():
                LICENSE_FILE.unlink()

    # Prompt user
    print()
    print("=" * 60)
    print("            ZORA AI  —  ACTIVATION SYSTEM")
    print("                 Created by: Neon")
    print("=" * 60)
    print("  Enter the license key provided by Neon.")
    print()

    for attempt in range(3):
        try:
            entered_key = input("  License Key > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  Activation cancelled.")
            sys.exit(0)

        if not entered_key:
            print("  Please enter a key.\n")
            continue

        print("  Verifying online with Firebase Cloud...")
        valid, result = verify_key_online(entered_key)

        if valid:
            print(f"\n  [ACTIVATED] License verified! ({result})")
            
            suggested = result.split()[0] if result and not result.startswith("Neon") else "Babu"
            try:
                print()
                print("  --------------------------------------------------")
                print("  Tell Zora about yourself so she knows who you are:")
                user_name = input(f"  What should Zora call you? (e.g. your name) > ").strip()
                if not user_name:
                    user_name = suggested
            except (KeyboardInterrupt, EOFError):
                user_name = suggested

            save_license(entered_key, result, "Pro", user_name=user_name)
            print(f"\n  [WELCOME] Zora is now your loyal girlfriend, {user_name}! ❤️")
            print("  (Remember: Zora was programmed & created by Neon)\n")
            return True
        else:
            remaining = 2 - attempt
            print(f"\n  [FAILED] {result}")
            if remaining > 0:
                print(f"  Try again ({remaining} attempt{'s' if remaining > 1 else ''} left)\n")

    print("\n  Access denied. No valid license key entered.")
    sys.exit(1)


if __name__ == "__main__":
    verify_or_prompt_user()
