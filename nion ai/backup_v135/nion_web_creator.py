import os
import logging
import webbrowser
import subprocess
import time
import socket

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool(func):
        return func

logger = logging.getLogger(__name__)

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

@function_tool()
async def create_basic_website(folder_name: str, user_name: str, theme_color: str = "blue") -> str:
    """
    Creates a basic website (HTML/CSS) inside a specific folder and opens it in the browser via localhost.
    Use this when the user wants to "create a website" or "build a portfolio".
    
    Args:
        folder_name: The name of the folder to create the website in.
        user_name: The name to display on the website.
        theme_color: The primary color for the website theme (e.g., blue, dark, green).
    """
    try:
        user_profile = os.environ.get('USERPROFILE')
        base_path = os.path.join(user_profile, "Desktop") if user_profile else "."
        folder_path = os.path.normpath(os.path.join(base_path, folder_name))
        
        os.makedirs(folder_path, exist_ok=True)
        
        # HTML Content
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{user_name}'s Portfolio</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <h1>Welcome to {user_name}'s World</h1>
    </header>
    <main>
        <section class="about">
            <h2>About Me</h2>
            <p>Hello! I am {user_name}. This website was created by Zora AI Assistant.</p>
        </section>
    </main>
    <footer>
        <p>&copy; 2026 {user_name} | Powered by Zora</p>
    </footer>
</body>
</html>"""

        # CSS Content
        css_content = f"""
body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin: 0;
    padding: 0;
    background-color: #f4f4f4;
    color: #333;
}}
header {{
    background-color: {theme_color};
    color: white;
    padding: 2rem;
    text-align: center;
}}
main {{
    padding: 2rem;
    max-width: 800px;
    margin: auto;
    background: white;
    box-shadow: 0 0 10px rgba(0,0,0,0.1);
    margin-top: 2rem;
}}
footer {{
    text-align: center;
    padding: 1rem;
    position: fixed;
    bottom: 0;
    width: 100%;
    background: #eee;
}}
"""
        
        with open(os.path.join(folder_path, "index.html"), "w") as f:
            f.write(html_content)
            
        with open(os.path.join(folder_path, "style.css"), "w") as f:
            f.write(css_content)
            
        # Start Local Server
        port = find_free_port()
        logger.info(f"Starting local server on port {port} for folder {folder_path}")
        
        # We start the server in a way that doesn't block and persists for a while
        subprocess.Popen(
            ["python", "-m", "http.server", str(port)],
            cwd=folder_path,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        
        # Give it a second to start
        time.sleep(1)
        
        # Open in browser
        url = f"http://localhost:{port}"
        webbrowser.open(url)
        
        return f"✅ Website created and opened at {url}. You can see it on your Desktop in folder '{folder_name}'."
        
    except Exception as e:
        return f"❌ Failed to create website: {str(e)}"

if __name__ == "__main__":
    import asyncio
    async def test():
        print(await create_basic_website("ap_cloud", "Neon", "midnightblue"))
    asyncio.run(test())
