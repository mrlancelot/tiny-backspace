#!/usr/bin/env python3
"""
Test script for Gemini-Daytona implementation
Tests sandbox creation, Gemini execution, and PR creation
"""

import os
import sys
import asyncio
import aiohttp
import json
from rich.console import Console
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

console = Console()

# Test configuration
TEST_REPO_URL = "https://github.com/mrlancelot/tb-test"
TEST_PROMPT = "Add a simple README.md file with project description"
API_URL = "http://localhost:8000"


async def test_cli_directly():
    """Test the Gemini Daytona Manager directly via CLI"""
    console.print("\n[bold blue]🧪 Testing Gemini-Daytona Manager CLI[/bold blue]\n")
    
    # Import the manager
    from gemini_daytona_manager import GeminiDaytonaManager
    
    manager = GeminiDaytonaManager(console)
    
    # Test 1: Create sandbox
    console.print("[yellow]Test 1: Creating Gemini sandbox...[/yellow]")
    sandbox = manager.create_gemini_sandbox("test-gemini-sandbox")
    
    if not sandbox:
        console.print("[red]❌ Failed to create sandbox[/red]")
        return False
    
    console.print(f"[green]✅ Sandbox created: {sandbox.id}[/green]")
    sandbox_id = sandbox.id
    
    try:
        # Test 2: List sandboxes
        console.print("\n[yellow]Test 2: Listing sandboxes...[/yellow]")
        sandboxes = manager.list_sandboxes()
        console.print(f"[green]✅ Found {len(sandboxes)} sandbox(es)[/green]")
        
        # Test 3: Clone repository
        console.print(f"\n[yellow]Test 3: Cloning repository {TEST_REPO_URL}...[/yellow]")
        clone_success = manager.clone_repository(sandbox, TEST_REPO_URL)
        
        if not clone_success:
            console.print("[red]❌ Failed to clone repository[/red]")
            return False
        
        console.print("[green]✅ Repository cloned successfully[/green]")
        
        # Test 4: Execute Gemini prompt
        console.print(f"\n[yellow]Test 4: Executing Gemini prompt...[/yellow]")
        console.print(f"[dim]Prompt: {TEST_PROMPT}[/dim]")
        
        repo_name = TEST_REPO_URL.rstrip('/').split('/')[-1].replace('.git', '')
        result = manager.execute_gemini_prompt(sandbox, TEST_PROMPT, repo_name)
        
        if result["success"]:
            console.print("[green]✅ Gemini execution successful[/green]")
        else:
            console.print("[red]❌ Gemini execution failed[/red]")
            console.print(f"[dim]{result.get('output', 'No output')}[/dim]")
        
        # Test 5: Check if Gemini is properly installed
        console.print("\n[yellow]Test 5: Verifying Gemini CLI installation...[/yellow]")
        gemini_check = manager.execute_command(sandbox, "which gemini && gemini --version")
        console.print(f"[dim]{gemini_check}[/dim]")
        
        return True
        
    finally:
        # Cleanup
        console.print(f"\n[yellow]Cleaning up sandbox {sandbox_id}...[/yellow]")
        manager.delete_sandbox(sandbox_id)


async def test_api_endpoint():
    """Test the FastAPI endpoint with streaming"""
    console.print("\n[bold blue]🧪 Testing API Endpoint[/bold blue]\n")
    
    # Check if API is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/health") as response:
                if response.status != 200:
                    console.print("[red]❌ API is not running. Start it with: python api/gemini_endpoint.py[/red]")
                    return False
                
                health = await response.json()
                console.print(f"[green]✅ API is healthy: {health}[/green]")
    except:
        console.print("[red]❌ Cannot connect to API. Start it with: python api/gemini_endpoint.py[/red]")
        return False
    
    # Test streaming endpoint
    console.print(f"\n[yellow]Testing POST /code endpoint...[/yellow]")
    console.print(f"Repository: {TEST_REPO_URL}")
    console.print(f"Prompt: {TEST_PROMPT}")
    
    request_data = {
        "repoUrl": TEST_REPO_URL,
        "prompt": TEST_PROMPT
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_URL}/code",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=600)
            ) as response:
                
                console.print("\n[bold]📡 Streaming response:[/bold]\n")
                
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith("data: "):
                            try:
                                data = json.loads(line_str[6:])
                                
                                # Display based on type
                                if data.get("type") == "status":
                                    console.print(f"[blue]ℹ️  {data.get('message')}[/blue]")
                                elif data.get("type") == "Tool: Git":
                                    console.print(f"[cyan]🔀 {data.get('message', data.get('content', ''))}[/cyan]")
                                elif data.get("type") == "AI Message":
                                    console.print(f"[dim]🤖 {data.get('message')}[/dim]")
                                elif data.get("type") == "error":
                                    console.print(f"[red]❌ {data.get('message')}[/red]")
                                elif data.get("type") == "complete":
                                    console.print(f"\n[bold green]✅ {data.get('message')}[/bold green]")
                                    if data.get("pr_url"):
                                        console.print(f"[bold blue]🔗 PR URL: {data.get('pr_url')}[/bold blue]")
                                
                            except json.JSONDecodeError:
                                console.print(f"[dim]{line_str}[/dim]")
                
                return True
                
    except asyncio.TimeoutError:
        console.print("[red]❌ Request timed out[/red]")
        return False
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        return False


async def main():
    """Run all tests"""
    console.print("[bold green]🚀 Gemini-Daytona Implementation Test Suite[/bold green]")
    
    # Check environment
    console.print("\n[yellow]Checking environment variables...[/yellow]")
    required_vars = ["DAYTONA_API_KEY", "GEMINI_API_KEY", "GITHUB_TOKEN"]
    missing_vars = []
    
    for var in required_vars:
        if os.getenv(var):
            console.print(f"[green]✅ {var} is set[/green]")
        else:
            console.print(f"[red]❌ {var} is missing[/red]")
            missing_vars.append(var)
    
    if missing_vars:
        console.print("\n[red]Please set the missing environment variables in your .env file[/red]")
        return
    
    # Run tests
    tests_passed = True
    
    # Test 1: Direct CLI test
    if await test_cli_directly():
        console.print("\n[green]✅ CLI tests passed[/green]")
    else:
        console.print("\n[red]❌ CLI tests failed[/red]")
        tests_passed = False
    
    # Test 2: API endpoint test (optional)
    console.print("\n[dim]To test the API endpoint, run: python api/gemini_endpoint.py[/dim]")
    console.print("[dim]Then run this test again in another terminal[/dim]")
    
    # Ask if user wants to test API
    try:
        test_api = input("\nTest API endpoint? (y/n): ").lower() == 'y'
        if test_api:
            if await test_api_endpoint():
                console.print("\n[green]✅ API tests passed[/green]")
            else:
                console.print("\n[red]❌ API tests failed[/red]")
                tests_passed = False
    except KeyboardInterrupt:
        console.print("\n[yellow]Skipping API test[/yellow]")
    
    # Summary
    console.print("\n" + "="*50)
    if tests_passed:
        console.print("[bold green]✅ All tests passed![/bold green]")
    else:
        console.print("[bold red]❌ Some tests failed[/bold red]")
    console.print("="*50)


if __name__ == "__main__":
    asyncio.run(main())