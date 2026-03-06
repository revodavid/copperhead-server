#!/usr/bin/env python3
"""
CopperHead Server Launcher

This script starts the CopperHead server and displays connection information
prominently for beginners. It also provides a direct link to the client.
"""

import os
import sys
import subprocess
import time

# Force unbuffered output for Codespaces visibility
os.environ["PYTHONUNBUFFERED"] = "1"

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ANSI colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def log(message):
    """Print and flush immediately."""
    print(message, flush=True)

def print_banner():
    """Print a welcome banner."""
    log("")
    log(f"{GREEN}{'='*60}{RESET}")
    log(f"{GREEN}{BOLD}       🐍 COPPERHEAD SNAKE GAME SERVER 🐍{RESET}")
    log(f"{GREEN}{'='*60}{RESET}")
    log("")

def get_connection_info():
    """Get the WebSocket URL based on environment."""
    codespace_name = os.environ.get("CODESPACE_NAME")
    github_domain = os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "app.github.dev")
    
    if codespace_name:
        ws_url = f"wss://{codespace_name}-8765.{github_domain}/ws/"
        is_codespace = True
    else:
        ws_url = "ws://localhost:8765/ws/"
        is_codespace = False
    
    return ws_url, is_codespace

def update_readme_with_url(ws_url):
    """Update README.md with connection info from README-Codespaces.md template."""
    import urllib.parse
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    readme_path = os.path.join(script_dir, "README.md")
    template_path = os.path.join(script_dir, "README-Codespaces.md")
    
    # Build client URL with server parameter
    client_base = "https://revodavid.github.io/copperhead-client/"
    client_url = f"{client_base}?server={urllib.parse.quote(ws_url, safe='')}"
    
    try:
        # Read the template and substitute placeholders
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
        
        block_content = template.replace("{{CLIENT_URL}}", client_url)
        block_content = block_content.replace("{{SERVER_URL}}", ws_url)
        
        # Wrap in markers for replacement on subsequent runs
        marker_start = "<!-- CODESPACE_CONNECTION_START -->"
        marker_end = "<!-- CODESPACE_CONNECTION_END -->"
        connection_block = f"{marker_start}\n{block_content}\n{marker_end}"
        
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if marker_start in content:
            # Replace existing block
            import re
            pattern = f"{marker_start}.*?{marker_end}"
            content = re.sub(pattern, connection_block, content, flags=re.DOTALL)
        else:
            # Insert after the first heading line
            lines = content.split("\n")
            insert_idx = 1
            for i, line in enumerate(lines):
                if line.startswith("# "):
                    insert_idx = i + 1
                    break
            lines.insert(insert_idx, "\n" + connection_block + "\n")
            content = "\n".join(lines)
        
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        log(f"{GREEN}✓ Updated README.md with your connection URL{RESET}")
        
    except FileNotFoundError:
        log(f"{YELLOW}Note: README-Codespaces.md template not found, skipping README update{RESET}")
    except Exception as e:
        # Don't fail startup if README update fails
        log(f"{YELLOW}Note: Could not update README.md: {e}{RESET}")

def print_connection_instructions(ws_url, is_codespace):
    """Print connection instructions for players."""
    import urllib.parse
    
    client_base = "https://revodavid.github.io/copperhead-client/"
    client_url = f"{client_base}?server={urllib.parse.quote(ws_url, safe='')}"
    
    log(f"{CYAN}📡 HOW TO PLAY:{RESET}")
    log("")
    log(f"   {BOLD}Open this link to play:{RESET}")
    log(f"   {YELLOW}{client_url}{RESET}")
    log("")
    
    if is_codespace:
        log(f"   {YELLOW}⚠️  IMPORTANT - Make your port PUBLIC first:{RESET}")
        log(f"      • Click the {BOLD}Ports{RESET} tab in the bottom panel")
        log(f"      • Right-click on port {BOLD}8765{RESET}")
        log(f"      • Select {BOLD}Port Visibility → Public{RESET}")
        log("")
    
    log(f"{GREEN}{'='*60}{RESET}")
    log("")

def main():
    """Main entry point."""
    print_banner()
    
    ws_url, is_codespace = get_connection_info()
    
    # In Codespaces, update README.md so the URL is visible in the Explorer
    if is_codespace:
        update_readme_with_url(ws_url)
    
    print_connection_instructions(ws_url, is_codespace)
    
    log("Starting server... (Press Ctrl+C to stop)")
    log("")
    
    # Pass through any command-line arguments to main.py
    # Set env var to suppress duplicate connection info from main.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, "main.py")
    
    env = os.environ.copy()
    env["COPPERHEAD_QUIET_STARTUP"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    
    args = [sys.executable, "-u", main_script] + sys.argv[1:]
    
    try:
        subprocess.run(args, env=env)
    except KeyboardInterrupt:
        log("")
        log(f"{YELLOW}Server stopped.{RESET}")

if __name__ == "__main__":
    main()
