#!/usr/bin/env python3
"""
Example client for the Gemini Coding Agent API
Demonstrates how to make requests and handle streaming responses
"""

import asyncio
import aiohttp
import json
import sys
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# API Configuration
API_BASE_URL = "http://localhost:8000"


async def stream_coding_request(repo_url: str, prompt: str, api_url: str = API_BASE_URL):
    """
    Make a coding request and stream the response
    
    Args:
        repo_url: GitHub repository URL
        prompt: Coding instruction
        api_url: API base URL
    """
    request_data = {
        "repoUrl": repo_url,
        "prompt": prompt
    }
    
    console.print(f"\n[bold blue]📤 Sending coding request[/bold blue]")
    console.print(f"Repository: [cyan]{repo_url}[/cyan]")
    console.print(f"Prompt: [yellow]{prompt}[/yellow]\n")
    
    pr_url: Optional[str] = None
    
    try:
        async with aiohttp.ClientSession() as session:
            # Check API health first
            try:
                async with session.get(f"{api_url}/health") as health_check:
                    if health_check.status != 200:
                        console.print("[red]❌ API is not healthy[/red]")
                        return None
            except:
                console.print("[red]❌ Cannot connect to API at {api_url}[/red]")
                console.print("[yellow]Make sure the API is running: ./run_gemini.sh api[/yellow]")
                return None
            
            # Make the coding request
            async with session.post(
                f"{api_url}/code",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=600)  # 10 minute timeout
            ) as response:
                
                if response.status != 200:
                    console.print(f"[red]❌ Request failed with status {response.status}[/red]")
                    return None
                
                # Process streaming response
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    
                    task = progress.add_task("Processing...", total=None)
                    
                    async for line in response.content:
                        if line:
                            line_str = line.decode('utf-8').strip()
                            if line_str.startswith("data: "):
                                try:
                                    data = json.loads(line_str[6:])
                                    
                                    # Update progress based on event type
                                    event_type = data.get("type", "")
                                    message = data.get("message", data.get("content", ""))
                                    
                                    if event_type == "status":
                                        progress.update(task, description=f"[blue]{message}[/blue]")
                                    elif event_type == "Tool: Git":
                                        progress.update(task, description=f"[cyan]Git: {message}[/cyan]")
                                    elif event_type == "AI Message":
                                        progress.update(task, description=f"[dim]AI: {message[:50]}...[/dim]")
                                    elif event_type == "Tool: Read":
                                        progress.update(task, description=f"[green]Reading: {data.get('content', '')}[/green]")
                                    elif event_type == "Tool: Write":
                                        progress.update(task, description=f"[yellow]Writing: {data.get('content', '')}[/yellow]")
                                    elif event_type == "error":
                                        console.print(f"\n[red]❌ Error: {message}[/red]")
                                        return None
                                    elif event_type == "complete":
                                        pr_url = data.get("pr_url")
                                        progress.update(task, description="[green]✅ Complete![/green]")
                                
                                except json.JSONDecodeError:
                                    # Handle non-JSON lines
                                    pass
                
                return pr_url
                
    except asyncio.TimeoutError:
        console.print("\n[red]❌ Request timed out[/red]")
        return None
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        return None


async def main():
    """Main example function"""
    console.print("[bold green]🚀 Gemini Coding Agent - Example Client[/bold green]\n")
    
    # Example 1: Simple README addition
    example_requests = [
        {
            "repo": "https://github.com/mrlancelot/tb-test",
            "prompt": "Add a simple README.md with project title and brief description"
        },
        {
            "repo": "https://github.com/mrlancelot/tb-test",
            "prompt": "Add a .gitignore file for Python projects"
        },
        {
            "repo": "https://github.com/mrlancelot/tb-test",
            "prompt": "Create a basic requirements.txt file with common Python packages"
        }
    ]
    
    # Let user choose an example or enter custom
    console.print("[bold]Choose an example or enter custom request:[/bold]")
    for i, example in enumerate(example_requests, 1):
        console.print(f"{i}. {example['prompt'][:60]}...")
    console.print("4. Enter custom request")
    
    try:
        choice = input("\nYour choice (1-4): ")
        
        if choice in ['1', '2', '3']:
            idx = int(choice) - 1
            repo_url = example_requests[idx]["repo"]
            prompt = example_requests[idx]["prompt"]
        elif choice == '4':
            repo_url = input("Repository URL: ").strip()
            prompt = input("Coding prompt: ").strip()
        else:
            console.print("[red]Invalid choice[/red]")
            return
        
        # Make the request
        pr_url = await stream_coding_request(repo_url, prompt)
        
        if pr_url:
            console.print(f"\n[bold green]✅ Success! Pull Request created:[/bold green]")
            console.print(f"[bold blue]🔗 {pr_url}[/bold blue]")
        else:
            console.print("\n[red]❌ Failed to create pull request[/red]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")


if __name__ == "__main__":
    # Check if API URL is provided as argument
    if len(sys.argv) > 1:
        API_BASE_URL = sys.argv[1]
    
    asyncio.run(main())