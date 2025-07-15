#!/usr/bin/env python3
"""Test different Claude authentication methods"""

import os
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
        name="auth-test",
        sandbox_type="claude",
        resources={"cpu": 1, "memory": 2}
    )
    
    if not sandbox:
        console.print("[red]Failed to create sandbox[/red]")
        exit(1)
    
    console.print(f"[green]✓ Sandbox created: {sandbox.id}[/green]")
    
    # Check current auth setup
    console.print("\n[yellow]Checking authentication setup...[/yellow]")
    
    # Check what files exist
    console.print("\n1. Authentication files:")
    manager.execute_command(sandbox, "ls -la ~/.claude* ~/.config/claude* 2>/dev/null || true", show_output=True)
    
    # Check OAuth token file content (safely)
    console.print("\n2. Check OAuth config:")
    manager.execute_command(sandbox, "test -f ~/.config/claude-code/auth.json && echo 'OAuth file exists' || echo 'OAuth file missing'", show_output=True)
    
    # Try different authentication methods
    console.print("\n[yellow]Testing authentication methods...[/yellow]")
    
    # Method 1: Set ANTHROPIC_API_KEY environment variable
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        console.print("\n3. Testing with ANTHROPIC_API_KEY env var:")
        result = manager.execute_command(
            sandbox,
            f'ANTHROPIC_API_KEY="{api_key}" claude --print "Say hello" 2>&1',
            show_output=True
        )
    
    # Method 2: Create proper Claude config
    console.print("\n4. Creating Claude CLI config:")
    oauth_token = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
    
    # Create the auth.json file that Claude CLI expects
    auth_config = {
        "session_key": oauth_token,
        "expires_at": "2025-12-31T23:59:59.999Z"  # Far future date
    }
    
    # Write the config
    manager.execute_command(
        sandbox,
        f"mkdir -p ~/.config/claude && echo '{json.dumps(auth_config)}' > ~/.config/claude/auth.json",
        show_output=False
    )
    
    # Test with new config
    console.print("\n5. Testing with session key config:")
    result = manager.execute_command(
        sandbox,
        'claude --print "Say hello" 2>&1',
        show_output=True
    )
    
    # Method 3: Try the login command approach
    console.print("\n6. Check Claude's expected auth format:")
    manager.execute_command(
        sandbox,
        "claude --help 2>&1 | grep -A5 -B5 login || true",
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