"""
Automatic PyPI Release & Build Tool for Zora AI
Creator: Neon
"""

import os
import sys
import re
import json
import shutil
import urllib.request
import subprocess
from pathlib import Path

# Enable ANSI escape sequences and UTF-8 on Windows
try:
    os.system("")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

CYAN = "\033[38;5;75m"
PURPLE = "\033[38;5;141m"
MAGENTA = "\033[38;5;177m"
YELLOW = "\033[38;5;220m"
GREEN = "\033[38;5;82m"
WHITE = "\033[97m"
GRAY = "\033[90m"
RESET = "\033[0m"
BOLD = "\033[1m"
BG_GREEN = "\033[48;5;40m\033[30m\033[1m"
BG_BLUE = "\033[48;5;33m\033[97m\033[1m"
BG_YELLOW = "\033[48;5;214m\033[30m\033[1m"

def print_banner(current_ver, next_ver):
    print(f"""
{CYAN}{BOLD}     ███████╗ ██████╗ ██████╗  █████╗       █████╗ ██╗
     ╚══███╔╝██╔═══██╗██╔══██╗██╔══██╗     ██╔══██╗██║
       ███╔╝ ██║   ██║██████╔╝███████║     ███████║██║
      ███╔╝  ██║   ██║██╔══██╗██╔══██║     ██╔══██║██║
     ███████╗╚██████╔╝██║  ██║██║  ██║     ██║  ██║██║
     ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝     ╚═╝  ╚═╝╚═╝{RESET}
            {WHITE}{BOLD}AUTO PyPI PUBLISHER -- CREATOR NEON{RESET}

{GRAY}────────────────────────────────────────────────────────────{RESET}
  {WHITE}Current Local Version{RESET} : {YELLOW}v{current_ver}{RESET}
  {WHITE}New Release Version{RESET}   : {GREEN}v{next_ver}{RESET}
  {WHITE}Target Repository{RESET}     : {CYAN}https://pypi.org/project/zoraai/{RESET}
{GRAY}────────────────────────────────────────────────────────────{RESET}
""")

def get_latest_pypi_version(pkg_name="zoraai"):
    try:
        url = f"https://pypi.org/pypi/{pkg_name}/json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=5).read())
        return data["info"]["version"]
    except Exception:
        return None

def bump_version(v_str):
    parts = [int(x) for x in v_str.split(".")]
    parts[-1] += 1
    return ".".join(str(x) for x in parts)

def main():
    root = Path(__file__).resolve().parent
    pyproject_path = root / "pyproject.toml"
    agent_path = root / "agent.py"
    token_file = Path.home() / ".zoraai" / "pypi_token.txt"

    if not pyproject_path.exists():
        print("Error: pyproject.toml not found!")
        sys.exit(1)

    if not token_file.exists():
        print(f"Error: PyPI token file not found at {token_file}")
        sys.exit(1)

    token = token_file.read_text(encoding="utf-8").strip()

    content = pyproject_path.read_text(encoding="utf-8")
    m = re.search(r'version\s*=\s*"([^"]+)"', content)
    current_ver = m.group(1) if m else "1.6.8"

    pypi_ver = get_latest_pypi_version("zoraai")
    base_ver = pypi_ver if pypi_ver else current_ver

    if len(sys.argv) > 1 and sys.argv[1].replace(".", "").isdigit():
        next_ver = sys.argv[1]
    else:
        next_ver = bump_version(base_ver)

    print_banner(current_ver, next_ver)

    print(f"[{CYAN}1/4{RESET}] Updating pyproject.toml to v{next_ver}...")
    new_pyproject = re.sub(r'version\s*=\s*"[^"]+"', f'version = "{next_ver}"', content)
    pyproject_path.write_text(new_pyproject, encoding="utf-8")

    if agent_path.exists():
        ag_code = agent_path.read_text(encoding="utf-8")
        ag_code = re.sub(r'version = "[0-9\.]+"', f'version = "{next_ver}"', ag_code)
        ag_code = re.sub(r'v[0-9\.]+\{RESET\}', f'v{next_ver}{{RESET}}', ag_code)
        agent_path.write_text(ag_code, encoding="utf-8")

    print(f"[{CYAN}2/4{RESET}] Cleaning previous build artifacts...")
    for d in [root / "dist", root / "build", root / "zoraai.egg-info"]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)

    print(f"[{CYAN}3/4{RESET}] Compiling wheels and sdist packages (python -m build)...")
    build_proc = subprocess.run([sys.executable, "-m", "build"], cwd=root, capture_output=True, text=True)
    if build_proc.returncode != 0:
        print(f"\nBuild failed: {build_proc.stderr}")
        sys.exit(1)

    dist_files = [f for f in (root / "dist").iterdir() if f.suffix in (".whl", ".gz")]
    print(f"  -> Built {len(dist_files)} distribution files.")

    print(f"[{CYAN}4/4{RESET}] Uploading v{next_ver} to PyPI via twine...")
    twine_cmd = [
        sys.executable, "-m", "twine", "upload",
        "--username", "__token__",
        "--password", token,
        "--non-interactive"
    ] + [str(f) for f in dist_files]

    upload_proc = subprocess.run(twine_cmd, capture_output=True, text=True)
    if upload_proc.returncode == 0:
        print(f"\n{BG_GREEN}  SUCCESS  {RESET} Version {next_ver} published live on PyPI!")
        print(f"  Live URL: {CYAN}https://pypi.org/project/zoraai/{next_ver}/{RESET}")
        print(f"\nAnyone worldwide can now install or upgrade using:")
        print(f"  {YELLOW}pip install --upgrade zoraai{RESET}\n")
    else:
        print(f"\nUpload failed: {upload_proc.stderr or upload_proc.stdout}")

if __name__ == "__main__":
    main()
