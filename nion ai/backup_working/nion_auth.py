import os
import sys
import json
import requests
from pathlib import Path

# ── Verification endpoints ─────────────────────────────────────────────────
# Priority order when verifying a key:
#   1. ZORA_AUTH_URL env var (if manually set by user)
#   2. Local test server at localhost:3000  (when running dashboard locally)
#   3. Cloudflare Pages live URL           (when deployed online)
#
# Change CLOUDFLARE_URL below to your real Cloudflare Pages URL after deploy.
CLOUDFLARE_URL   = os.getenv("ZORA_AUTH_URL", "https://zora-keys.pages.dev/api/verify")
LOCAL_TEST_URL   = "http://localhost:3000/api/verify"

# Master developer key — always works offline, no server needed
MASTER_KEY = "ZORA-DEV-MASTER-NEON-2026"

LICENSE_DIR  = Path.home() / ".zoraai"
LICENSE_FILE = LICENSE_DIR / "license.json"


# ── Storage helpers ────────────────────────────────────────────────────────
def get_saved_license() -> dict | None:
    """Reads stored license from client's machine."""
    if LICENSE_FILE.exists():
        try:
            return json.loads(LICENSE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def save_license(key: str, client_name: str, plan: str):
    """Saves verified license locally so client doesn't need to type it again."""
    LICENSE_DIR.mkdir(parents=True, exist_ok=True)
    LICENSE_FILE.write_text(
        json.dumps({"key": key, "client": client_name, "plan": plan}, indent=2),
        encoding="utf-8"
    )


# ── Core verification ──────────────────────────────────────────────────────
def _try_url(url: str, key: str) -> tuple[bool, str] | None:
    """
    Attempts to verify key at a single URL.
    Returns (is_valid, info_or_error) or None if server unreachable.
    """
    try:
        res = requests.get(f"{url}?key={key}", timeout=5)
        data = res.json()
        if res.status_code == 200 and data.get("valid"):
            client = data.get("client", "User")
            plan   = data.get("plan", "Pro")
            save_license(key, client, plan)
            return True, f"{client} ({plan})"
        else:
            return False, data.get("error", "Invalid or revoked key.")
    except requests.exceptions.ConnectionError:
        return None  # server not reachable
    except requests.exceptions.Timeout:
        return None  # server too slow
    except Exception:
        return None


def verify_key_online(key: str) -> tuple[bool, str]:
    """
    Verifies key against available servers.
    Tries localhost first (for local testing), then Cloudflare.
    Falls back to saved license if both are unreachable.
    """
    clean_key = key.strip().upper()
    if not clean_key:
        return False, "Key cannot be empty."

    # Master developer key — always passes
    if clean_key == MASTER_KEY:
        return True, "Developer (Master Key)"

    # Try local server first (fast, works when testing without Cloudflare)
    result = _try_url(LOCAL_TEST_URL, clean_key)
    if result is not None:
        return result

    # Try Cloudflare production URL
    result = _try_url(CLOUDFLARE_URL, clean_key)
    if result is not None:
        return result

    # Both servers unreachable — check if key was previously verified and saved
    saved = get_saved_license()
    if saved and saved.get("key", "").upper() == clean_key:
        return True, f"{saved.get('client', 'User')} (Offline Mode)"

    return False, (
        "Could not reach license server.\n"
        "  - If testing locally: make sure 'node server.js' is running in admin_panel/\n"
        "  - If using Cloudflare: check your internet connection."
    )


# ── Main prompt flow ───────────────────────────────────────────────────────
def verify_or_prompt_user() -> bool:
    """
    Checks stored license first. If valid, skips prompt entirely.
    Otherwise asks user to enter a key (3 attempts).
    """
    # Check if already activated on this PC
    saved = get_saved_license()
    if saved and saved.get("key"):
        valid, info = verify_key_online(saved["key"])
        if valid:
            print(f"[Zora AI] License Active — Registered to: {info}")
            return True
        else:
            print(f"[Zora AI] Stored key is no longer valid: {info}")
            if LICENSE_FILE.exists():
                LICENSE_FILE.unlink()

    # Prompt user
    print()
    print("=" * 60)
    print("            ZORA AI  —  ACTIVATION")
    print("=" * 60)
    print("  Enter the license key you received from the creator.")
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

        print("  Verifying...")
        valid, result = verify_key_online(entered_key)

        if valid:
            print(f"\n  [ACTIVATED] Welcome, {result}!")
            print("  Zora AI is now licensed on this computer.\n")
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
