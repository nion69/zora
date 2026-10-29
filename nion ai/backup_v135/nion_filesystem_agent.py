import os
import shutil
import subprocess
import sys
import ctypes

from langchain_core.tools import tool
from langchain.agents import initialize_agent, AgentType
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# 4. Ensure the script runs with necessary administrator or root privileges
def is_admin():
    """Check if the script is running with administrator privileges."""
    try:
        # Check for Windows admin privileges
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        # Fallback for non-Windows or other errors
        return os.getuid() == 0 if hasattr(os, 'getuid') else False

if not is_admin():
    print("This script requires Administrator privileges to perform system operations.")
    try:
        if sys.platform == 'win32':
            # Relaunch the script with admin privileges on Windows
            print("Attempting to elevate privileges...")
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            sys.exit()
        else:
            print("Please run this script with 'sudo'.")
            sys.exit()
    except Exception as e:
        print(f"Failed to elevate privileges: {e}")
        sys.exit(1)


# 1 & 2. Define standard libraries and custom functions for system/file operations
@tool
def create_file(file_path: str, content: str) -> str:
    """Creates a file at the specified path with the given content."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully created file at {file_path}"
    except Exception as e:
        return f"Error creating file: {str(e)}"

@tool
def read_file(file_path: str) -> str:
    """Reads the content of a file at the specified path."""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return f"File {file_path} does not exist."
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool
def delete_folder(folder_path: str) -> str:
    """Deletes a folder and all its contents at the specified path."""
    try:
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            return f"Successfully deleted folder at {folder_path}"
        else:
            return f"Folder {folder_path} does not exist."
    except Exception as e:
        return f"Error deleting folder: {str(e)}"

@tool
def move_file(source: str, destination: str) -> str:
    """Moves or renames a file or folder from source to destination."""
    try:
        shutil.move(source, destination)
        return f"Successfully moved {source} to {destination}"
    except Exception as e:
        return f"Error moving file: {str(e)}"

@tool
def copy_file(source: str, destination: str) -> str:
    """Copies a file or folder from source to destination."""
    try:
        if os.path.isdir(source):
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
        return f"Successfully copied {source} to {destination}"
    except Exception as e:
        return f"Error copying file: {str(e)}"

@tool
def run_command(command: str) -> str:
    """Runs a system command in the terminal and returns the output."""
    try:
        # Use subprocess to run the command
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return f"Command executed successfully:\n{result.stdout}"
        else:
            return f"Command failed with error:\n{result.stderr}"
    except Exception as e:
        return f"Error executing command: {str(e)}"

@tool
def list_directory(directory_path: str) -> str:
    """Lists all files and folders in the specified directory."""
    try:
        if not os.path.exists(directory_path):
            return f"Directory {directory_path} does not exist."
        items = os.listdir(directory_path)
        return f"Contents of {directory_path}:\n" + "\n".join(items)
    except Exception as e:
        return f"Error listing directory: {str(e)}"


# 3. Integrate these tools with an AI framework like Langchain
def main():
    print("\n" + "="*50)
    print(" Zora - Filesystem Specialist Agent ".center(50, "="))
    print("="*50)
    print("Status: Running with Administrator/Root privileges.")
    
    # Define the list of tools available to the agent
    tools = [
        create_file,
        read_file,
        delete_folder,
        move_file,
        copy_file,
        run_command,
        list_directory
    ]
    
    # Try to initialize Gemini first, fallback to OpenAI
    try:
        if os.getenv("GOOGLE_API_KEY"):
            print("Using Google Gemini Model...")
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
        elif os.getenv("OPENAI_API_KEY"):
            print("Using OpenAI GPT-4 Model...")
            llm = ChatOpenAI(model="gpt-4", temperature=0)
        else:
            print("Error: No API keys found in .env file.")
            return
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        return
    
    # Initialize the agent
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True
    )
    
    print("Agent initialized. Ready for commands. (Type 'exit' to quit)")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("\nNeon Boss > ")
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("Exiting Filesystem Agent. Goodbye!")
                break
            
            if not user_input.strip():
                continue
                
            response = agent.invoke({"input": user_input})
            print(f"\nZora > {response['output']}")
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()
