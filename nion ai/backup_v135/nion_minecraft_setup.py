import os
import requests
import subprocess
import logging

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool(func):
        return func

logger = logging.getLogger(__name__)

@function_tool()
async def setup_minecraft_server(folder_name: str = "ap_cloud", ram_gb: int = 2) -> str:
    """
    Sets up a Minecraft server (PaperMC) in a specific folder.
    Creates folder, downloads server JAR, accepts EULA, and creates a start script.
    
    Args:
        folder_name: The name of the folder for the server.
        ram_gb: Amount of RAM to allocate in GB.
    """
    try:
        user_profile = os.environ.get('USERPROFILE')
        base_path = os.path.join(user_profile, "Desktop") if user_profile else "."
        server_path = os.path.normpath(os.path.join(base_path, folder_name))
        
        os.makedirs(server_path, exist_ok=True)
        logger.info(f"Setting up Minecraft server in: {server_path}")

        # 1. Get latest PaperMC build information
        project = "paper"
        version = "1.20.4" # Defaulting to a stable version, can be updated
        api_url = f"https://api.papermc.io/v2/projects/{project}/versions/{version}"
        
        response = requests.get(api_url)
        if response.status_code != 200:
            return f"❌ Failed to fetch Minecraft version info from PaperMC API."
            
        latest_build = response.json()["builds"][-1]
        jar_name = f"{project}-{version}-{latest_build}.jar"
        download_url = f"{api_url}/builds/{latest_build}/downloads/{jar_name}"
        
        jar_path = os.path.join(server_path, "server.jar")
        
        # 2. Download the JAR
        if not os.path.exists(jar_path):
            logger.info(f"Downloading {jar_name}...")
            r = requests.get(download_url, stream=True)
            with open(jar_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info("Download complete.")
        else:
            logger.info("Server JAR already exists, skipping download.")

        # 3. Create eula.txt
        with open(os.path.join(server_path, "eula.txt"), "w") as f:
            f.write("eula=true\n")
            
        # 4. Create start.bat
        start_script = f"""@echo off
title Minecraft Server - {folder_name}
java -Xmx{ram_gb}G -Xms{ram_gb}G -jar server.jar nogui
pause
"""
        with open(os.path.join(server_path, "run.bat"), "w") as f:
            f.write(start_script)
            
        # 5. Launch the server in a new console
        subprocess.Popen(
            ["cmd.exe", "/c", "start", "run.bat"],
            cwd=server_path,
            shell=True
        )
        
        return f"✅ Minecraft server ({version}) setup complete in '{folder_name}'! The server is now starting in a new window with {ram_gb}GB RAM."
        
    except Exception as e:
        logger.error(f"Minecraft setup error: {e}")
        return f"❌ Failed to setup Minecraft server: {str(e)}"

if __name__ == "__main__":
    import asyncio
    async def test():
        print(await setup_minecraft_server())
    asyncio.run(test())
