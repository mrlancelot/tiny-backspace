#!/usr/bin/env python3
"""Fix Claude authentication by copying entire .claude directory"""

import os
import shutil
import tarfile
import base64
import json
from dotenv import load_dotenv
from daytona_manager_cleaned import DaytonaManager
from rich.console import Console

load_dotenv()

console = Console()
manager = DaytonaManager()

try:
    # Create sandbox
    console.print("[yellow]Creating test sandbox...[/yellow]")
    sandbox = manager.create_sandbox(
        name="auth-complete",
        sandbox_type="claude",
        resources={"cpu": 1, "memory": 2}
    )
    
    if not sandbox:
        console.print("[red]Failed to create sandbox[/red]")
        exit(1)
    
    console.print(f"[green]✓ Sandbox created: {sandbox.id}[/green]")
    
    # Create tar of local .claude directory
    console.print("\n[yellow]Preparing Claude configuration...[/yellow]")
    
    # Create a temporary tar file
    tar_path = "/tmp/claude_config.tar"
    with tarfile.open(tar_path, "w") as tar:
        # Add the entire .claude directory
        claude_dir = os.path.expanduser("~/.claude")
        if os.path.exists(claude_dir):
            tar.add(claude_dir, arcname=".claude")
            console.print("[green]✓ Added .claude directory[/green]")
        
        # Also add .claude.json if it exists
        claude_json = os.path.expanduser("~/.claude.json")
        if os.path.exists(claude_json):
            # Read and filter sensitive data
            with open(claude_json, 'r') as f:
                data = json.load(f)
                # Only keep non-sensitive configuration
                safe_data = {
                    "autoUpdates": data.get("autoUpdates", True),
                    "installMethod": "npm"
                }
            
            # Write filtered data to temp file
            temp_json = "/tmp/claude_filtered.json"
            with open(temp_json, 'w') as f:
                json.dump(safe_data, f)
            
            tar.add(temp_json, arcname=".claude.json")
            console.print("[green]✓ Added .claude.json (filtered)[/green]")
    
    # Base64 encode the tar file
    with open(tar_path, 'rb') as f:
        tar_b64 = base64.b64encode(f.read()).decode()
    
    # Transfer to sandbox
    console.print("\n[yellow]Transferring configuration to sandbox...[/yellow]")
    
    # Create script to extract
    extract_script = f'''
# Decode and extract tar
echo "{tar_b64}" | base64 -d > /tmp/claude_config.tar
cd /root
tar -xf /tmp/claude_config.tar
ls -la ~/.claude/
    '''
    
    # Execute transfer
    manager.execute_command(
        sandbox,
        extract_script,
        show_output=True
    )
    
    # Set up OAuth token separately
    console.print("\n[yellow]Setting up OAuth authentication...[/yellow]")
    oauth_token = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
    
    if oauth_token:
        # Try multiple auth locations
        auth_commands = [
            # Method 1: statsig directory (most likely)
            f'''mkdir -p ~/.claude/statsig && echo '{{"oauth_token": "{oauth_token}"}}' > ~/.claude/statsig/auth.json''',
            
            # Method 2: Standard OAuth location
            f'''mkdir -p ~/.config/claude-code && echo '{{"access_token": "{oauth_token}", "token_type": "Bearer"}}' > ~/.config/claude-code/auth.json''',
            
            # Method 3: Environment variable
            f'''echo 'export CLAUDE_CODE_OAUTH_TOKEN="{oauth_token}"' >> ~/.bashrc && source ~/.bashrc'''
        ]
        
        for cmd in auth_commands:
            manager.execute_command(sandbox, cmd, show_output=False)
    
    # Test Claude
    console.print("\n[yellow]Testing Claude...[/yellow]")
    
    # First check version
    result = manager.execute_command(
        sandbox,
        "claude --version 2>&1",
        show_output=True
    )
    
    # Try running Claude with a simple command
    console.print("\n[yellow]Testing Claude functionality...[/yellow]")
    
    # Set environment variable and run
    test_result = manager.execute_command(
        sandbox,
        f'''CLAUDE_CODE_OAUTH_TOKEN="{oauth_token}" claude --print "Say hello" 2>&1''',
        show_output=True
    )
    
    # Check if we need to use a different auth method
    if "Invalid API key" in test_result or "login" in test_result.lower():
        console.print("\n[yellow]Trying alternative authentication method...[/yellow]")
        
        # Try using the API key directly
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            result = manager.execute_command(
                sandbox,
                f'ANTHROPIC_API_KEY="{api_key}" claude --print "Say hello" 2>&1',
                show_output=True
            )
    
finally:
    # Cleanup
    if 'sandbox' in locals() and sandbox:
        console.print("\n[yellow]Cleaning up...[/yellow]")
        try:
            manager.delete_sandbox(sandbox.id)
            console.print("[green]✓ Sandbox deleted[/green]")
        except:
            console.print("[red]Failed to delete sandbox[/red]")
    
    # Clean up temp files
    if os.path.exists("/tmp/claude_config.tar"):
        os.remove("/tmp/claude_config.tar")
    if os.path.exists("/tmp/claude_filtered.json"):
        os.remove("/tmp/claude_filtered.json")