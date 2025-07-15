#!/usr/bin/env python3
"""
Test script for Daytona streaming capabilities
Demonstrates real-time command execution with streaming output
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from daytona_streaming_manager import DaytonaStreamingManager
from daytona_manager_refactored import DaytonaManagerRefactored

# Load environment variables
load_dotenv()

console = Console()


async def test_basic_streaming():
    """Test basic streaming command execution"""
    console.print("\n[bold blue]Testing Daytona Streaming Capabilities[/bold blue]\n")
    
    # Initialize managers
    manager = DaytonaManagerRefactored(console=console)
    streaming_manager = DaytonaStreamingManager(
        api_key=os.getenv("DAYTONA_API_KEY")
    )
    
    # Create a test sandbox
    console.print("[yellow]Creating test sandbox...[/yellow]")
    sandbox = manager.create_sandbox(
        name="streaming-test",
        sandbox_type="docker",
        resources={"cpu": 1, "memory": 2}
    )
    
    if not sandbox:
        console.print("[red]Failed to create sandbox[/red]")
        return
    
    sandbox_id = sandbox.id
    console.print(f"[green]✓ Sandbox created: {sandbox_id}[/green]")
    
    try:
        # Test 1: Simple streaming command
        console.print("\n[bold]Test 1: Simple streaming command[/bold]")
        console.print("Executing: for i in {1..5}; do echo \"Line $i\"; sleep 1; done\n")
        
        result = await streaming_manager.execute_streaming_command(
            sandbox_id,
            'for i in {1..5}; do echo "Line $i"; sleep 1; done',
            lambda chunk: console.print(f"[cyan]STREAM:[/cyan] {chunk}", end="")
        )
        
        console.print(f"\n[green]✓ Command completed with exit code: {result['exit_code']}[/green]")
        
        # Test 2: Debug sandbox state
        console.print("\n[bold]Test 2: Debug sandbox state[/bold]")
        await streaming_manager.debug_sandbox_state(sandbox_id)
        
        # Test 3: Git operations with streaming
        console.print("\n[bold]Test 3: Git operations with streaming[/bold]")
        
        # Clone a small test repo
        console.print("\nCloning test repository...")
        result = await streaming_manager.execute_streaming_command(
            sandbox_id,
            "cd /root && git clone --depth 1 https://github.com/octocat/Hello-World.git",
            lambda chunk: console.print(chunk, end="")
        )
        
        if result["exit_code"] == 0:
            console.print("[green]✓ Repository cloned successfully[/green]")
            
            # List repository contents
            console.print("\nListing repository contents:")
            await streaming_manager.execute_streaming_command(
                sandbox_id,
                "cd /root/Hello-World && ls -la",
                lambda chunk: console.print(chunk, end="")
            )
        
        # Test 4: Long-running command with progress
        console.print("\n[bold]Test 4: Long-running command with progress[/bold]")
        console.print("Simulating a build process...\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Building...", total=None)
            
            build_script = """
            echo "Starting build process..."
            for step in "Installing dependencies" "Compiling source" "Running tests" "Creating artifacts" "Finalizing"; do
                echo "[$step]"
                sleep 2
                echo "✓ $step completed"
            done
            echo "Build completed successfully!"
            """
            
            result = await streaming_manager.execute_streaming_command(
                sandbox_id,
                build_script,
                lambda chunk: progress.console.print(f"[dim]{chunk}[/dim]", end="")
            )
            
            progress.update(task, completed=True)
        
        console.print(f"\n[green]✓ Build completed with exit code: {result['exit_code']}[/green]")
        
    except Exception as e:
        console.print(f"\n[red]Error during testing: {e}[/red]")
    
    finally:
        # Cleanup
        console.print("\n[yellow]Cleaning up sandbox...[/yellow]")
        try:
            manager.delete_sandbox(sandbox_id)
            console.print("[green]✓ Sandbox deleted[/green]")
        except:
            console.print("[red]Failed to delete sandbox[/red]")


async def test_error_handling():
    """Test error handling in streaming"""
    console.print("\n[bold blue]Testing Error Handling[/bold blue]\n")
    
    streaming_manager = DaytonaStreamingManager(
        api_key=os.getenv("DAYTONA_API_KEY")
    )
    
    # Test with non-existent sandbox
    console.print("Testing with non-existent sandbox...")
    try:
        result = await streaming_manager.execute_streaming_command(
            "non-existent-sandbox",
            "echo 'This should fail'",
            lambda chunk: console.print(chunk, end="")
        )
        console.print(f"[red]Unexpected success: {result}[/red]")
    except Exception as e:
        console.print(f"[green]✓ Expected error: {e}[/green]")


async def main():
    """Main test function"""
    console.print("[bold]Daytona Streaming Test Suite[/bold]")
    console.print("=" * 50)
    
    # Check for required environment variables
    if not os.getenv("DAYTONA_API_KEY"):
        console.print("[red]Error: DAYTONA_API_KEY not set in environment[/red]")
        console.print("Please set it in your .env file")
        return
    
    # Run tests
    await test_basic_streaming()
    await test_error_handling()
    
    console.print("\n[bold green]All tests completed![/bold green]")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Tests interrupted by user[/yellow]")
        sys.exit(0)