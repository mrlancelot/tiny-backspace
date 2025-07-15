#!/usr/bin/env python3
"""
Enhanced CLI for Daytona Manager
Provides rich interactive interface with streaming and progress visualization
"""

import asyncio
import sys
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.progress import track
from rich.text import Text
from rich.tree import Tree
from rich import box
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory

from daytona_manager_cleaned import DaytonaManager
from streaming_response import StreamingResponseHandler, StreamChunk, ResponseType
from permission_manager import PermissionManager, OperationType


class EnhancedCLI:
    def __init__(self):
        """Initialize enhanced CLI"""
        self.console = Console()
        self.manager = None
        self.permission_manager = PermissionManager(console=self.console)
        self.stream_handler = StreamingResponseHandler(console=self.console)
        
        # Command history
        history_file = Path.home() / '.daytona' / 'history.txt'
        history_file.parent.mkdir(exist_ok=True)
        self.history = FileHistory(str(history_file))
        
        # Initialize prompt session with completions
        self.commands = [
            'create', 'list', 'connect', 'exec', 'delete', 
            'test', 'stream', 'permissions', 'help', 'exit'
        ]
        self.session = PromptSession(
            history=self.history,
            completer=WordCompleter(self.commands)
        )
        
        # Current context
        self.current_sandbox = None
        self.sandbox_cache = {}
    
    def initialize_manager(self):
        """Initialize Daytona manager with error handling"""
        try:
            self.manager = DaytonaManager()
            self.console.print("[green]✅ Connected to Daytona successfully!")
            return True
        except SystemExit:
            self.console.print("[red]❌ Failed to initialize Daytona Manager")
            self.console.print("[yellow]Please ensure DAYTONA_API_KEY is set in your environment or .env file")
            return False
    
    def show_banner(self):
        """Display welcome banner"""
        banner = Panel(
            "[bold blue]Daytona Development Environment Manager[/bold blue]\n"
            "[dim]Enhanced CLI with streaming responses and rich UI[/dim]\n\n"
            "Type [bold]help[/bold] for available commands or [bold]exit[/bold] to quit",
            title="🌟 Welcome",
            border_style="blue"
        )
        self.console.print(banner)
    
    def show_help(self):
        """Display help information"""
        help_tree = Tree("📚 Available Commands", style="bold blue")
        
        commands = {
            "create": "Create a new sandbox environment",
            "list": "List all active sandboxes",
            "connect": "Connect to an existing sandbox",
            "exec": "Execute a command in a sandbox",
            "delete": "Delete a sandbox",
            "test": "Test sandbox tools and connectivity",
            "stream": "Send a prompt with streaming response",
            "permissions": "Manage permission settings",
            "help": "Show this help message",
            "exit": "Exit the CLI"
        }
        
        for cmd, desc in commands.items():
            help_tree.add(f"[cyan]{cmd}[/cyan] - {desc}")
        
        self.console.print(help_tree)
        
        # Show usage examples
        examples = Panel(
            "[bold]Examples:[/bold]\n\n"
            "[cyan]create[/cyan] → Interactive sandbox creation\n"
            "[cyan]connect abc123[/cyan] → Connect to sandbox 'abc123'\n"
            "[cyan]exec 'python --version'[/cyan] → Run command in current sandbox\n"
            "[cyan]stream 'Write a hello world function'[/cyan] → Stream Claude response",
            title="💡 Usage",
            border_style="yellow"
        )
        self.console.print(examples)
    
    async def cmd_create(self):
        """Handle create command with interactive prompts"""
        # Request permission
        if not self.permission_manager.request_permission(
            OperationType.CREATE_SANDBOX,
            "New Sandbox",
            {"timestamp": datetime.now().isoformat()},
            risk_level="low"
        ):
            self.console.print("[red]❌ Permission denied for sandbox creation")
            return
        
        # Interactive sandbox configuration
        name = Prompt.ask(
            "Sandbox name",
            default=f"sandbox-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        
        # Choose sandbox type
        sandbox_types = ["claude", "python", "docker"]
        type_table = Table(title="Available Sandbox Types", box=box.ROUNDED)
        type_table.add_column("Type", style="cyan")
        type_table.add_column("Description")
        type_table.add_column("Base Image")
        
        type_table.add_row("claude", "Claude Code environment", "node:20-slim")
        type_table.add_row("python", "Python development", "python:3.11-bullseye")
        type_table.add_row("docker", "Docker-in-Docker", "docker:20.10-dind")
        
        self.console.print(type_table)
        
        sandbox_type = Prompt.ask(
            "Select sandbox type",
            choices=sandbox_types,
            default="claude"
        )
        
        # Resource configuration
        if Confirm.ask("Customize resources?", default=False):
            cpu = IntPrompt.ask("CPU cores", default=2, minimum=1, maximum=8)
            memory = IntPrompt.ask("Memory (GB)", default=4, minimum=1, maximum=16)
            resources = {"cpu": cpu, "memory": memory}
        else:
            resources = None
        
        # Create sandbox with progress
        with self.console.status(f"[bold green]Creating {sandbox_type} sandbox '{name}'...") as status:
            sandbox = self.manager.create_sandbox(name, sandbox_type, resources)
            
        if sandbox:
            self.current_sandbox = sandbox
            self.sandbox_cache[sandbox.id] = {
                'name': name,
                'type': sandbox_type,
                'created': datetime.now()
            }
            
            success_panel = Panel(
                f"✅ Sandbox created successfully!\n\n"
                f"[bold]ID:[/bold] {sandbox.id}\n"
                f"[bold]Name:[/bold] {name}\n"
                f"[bold]Type:[/bold] {sandbox_type}\n\n"
                f"[dim]You are now connected to this sandbox[/dim]",
                title="🎉 Success",
                border_style="green"
            )
            self.console.print(success_panel)
        else:
            self.console.print("[red]❌ Failed to create sandbox")
    
    def cmd_list(self):
        """List sandboxes with rich formatting"""
        self.console.print("\n[bold]📋 Fetching sandbox list...[/bold]")
        
        # Mock implementation since we need actual Daytona response
        # In real usage, this would call self.manager.list_sandboxes()
        
        table = Table(title="Active Sandboxes", box=box.ROUNDED)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="white")
        table.add_column("Type", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Created", style="dim")
        
        # Add cached sandboxes
        for sandbox_id, info in self.sandbox_cache.items():
            status = "🟢 Active" if sandbox_id == getattr(self.current_sandbox, 'id', None) else "⚪ Idle"
            table.add_row(
                sandbox_id[:8] + "...",
                info['name'],
                info['type'],
                status,
                info['created'].strftime("%H:%M:%S")
            )
        
        if not self.sandbox_cache:
            table.add_row("", "[dim]No sandboxes found[/dim]", "", "", "")
        
        self.console.print(table)
    
    async def cmd_stream(self, prompt: Optional[str] = None):
        """Handle streaming command with Claude"""
        if not self.current_sandbox:
            self.console.print("[yellow]⚠️  No sandbox connected. Use 'connect' first.")
            return
        
        if not prompt:
            prompt = Prompt.ask("Enter your prompt for Claude")
        
        # Request permission
        if not self.permission_manager.request_permission(
            OperationType.EXECUTE_COMMAND,
            self.current_sandbox.id,
            {"command": "claude", "prompt": prompt[:50] + "..."},
            risk_level="medium"
        ):
            self.console.print("[red]❌ Permission denied")
            return
        
        # Create streaming command
        command = f"claude --print '{prompt}'"
        
        # Show streaming response
        self.console.print(f"\n[bold]🚀 Streaming response for:[/bold] {prompt}\n")
        
        # Create response generator
        response_gen = self.stream_handler.stream_claude_response(
            command,
            lambda cmd: self.manager.execute_command(self.current_sandbox, cmd, show_output=False)
        )
        
        # Display streaming response
        await self.stream_handler.display_streaming_response(response_gen)
    
    def cmd_permissions(self):
        """Manage permissions interactively"""
        while True:
            perm_menu = Table(title="Permission Management", box=box.ROUNDED)
            perm_menu.add_column("Option", style="cyan")
            perm_menu.add_column("Description")
            
            perm_menu.add_row("1", "View current permissions")
            perm_menu.add_row("2", "View audit log")
            perm_menu.add_row("3", "Reset session permissions")
            perm_menu.add_row("4", "Reset all permissions")
            perm_menu.add_row("5", "Back to main menu")
            
            self.console.print(perm_menu)
            
            choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5"])
            
            if choice == "1":
                self.permission_manager.show_permission_summary()
            elif choice == "2":
                limit = IntPrompt.ask("Number of entries to show", default=10)
                self.permission_manager.show_audit_log(limit)
            elif choice == "3":
                if Confirm.ask("Reset session permissions?"):
                    self.permission_manager.reset_permissions("session")
            elif choice == "4":
                if Confirm.ask("[red]Reset ALL permissions?[/red]"):
                    self.permission_manager.reset_permissions("all")
            elif choice == "5":
                break
            
            self.console.print()  # Add spacing
    
    def show_status_bar(self):
        """Display current status bar"""
        status_parts = []
        
        if self.current_sandbox:
            sandbox_info = self.sandbox_cache.get(
                self.current_sandbox.id,
                {'name': 'Unknown', 'type': 'unknown'}
            )
            status_parts.append(
                f"[green]📦 {sandbox_info['name']}[/green] "
                f"([yellow]{sandbox_info['type']}[/yellow])"
            )
        else:
            status_parts.append("[dim]No sandbox connected[/dim]")
        
        status_parts.append(f"[dim]{datetime.now().strftime('%H:%M:%S')}[/dim]")
        
        status_text = " | ".join(status_parts)
        self.console.print(f"\n[{status_text}]")
    
    async def run_interactive(self):
        """Run interactive CLI session"""
        self.show_banner()
        
        if not self.initialize_manager():
            return
        
        self.console.print("\n[green]Ready![/green] Type [bold]help[/bold] to see available commands.\n")
        
        while True:
            try:
                # Show status
                self.show_status_bar()
                
                # Get command with auto-completion
                command = await self.session.prompt_async("daytona> ")
                
                if not command.strip():
                    continue
                
                # Parse command and arguments
                parts = command.strip().split(maxsplit=1)
                cmd = parts[0].lower()
                args = parts[1] if len(parts) > 1 else None
                
                # Handle commands
                if cmd == "exit":
                    if Confirm.ask("Exit Daytona CLI?"):
                        self.console.print("[yellow]Goodbye! 👋[/yellow]")
                        break
                
                elif cmd == "help":
                    self.show_help()
                
                elif cmd == "create":
                    await self.cmd_create()
                
                elif cmd == "list":
                    self.cmd_list()
                
                elif cmd == "connect":
                    if args:
                        sandbox = self.manager.connect_to_sandbox(args)
                        if sandbox:
                            self.current_sandbox = sandbox
                            self.console.print(f"[green]✅ Connected to sandbox: {args}")
                    else:
                        self.console.print("[yellow]Usage: connect <sandbox-id>")
                
                elif cmd == "exec":
                    if self.current_sandbox and args:
                        if self.permission_manager.request_permission(
                            OperationType.EXECUTE_COMMAND,
                            self.current_sandbox.id,
                            {"command": args}
                        ):
                            with self.console.status(f"Executing: {args}"):
                                self.manager.execute_command(self.current_sandbox, args)
                    else:
                        self.console.print("[yellow]Usage: exec <command> (requires connected sandbox)")
                
                elif cmd == "delete":
                    if args:
                        if self.permission_manager.request_permission(
                            OperationType.DELETE_SANDBOX,
                            args,
                            risk_level="high"
                        ):
                            self.manager.delete_sandbox(args)
                            if self.current_sandbox and self.current_sandbox.id == args:
                                self.current_sandbox = None
                    else:
                        self.console.print("[yellow]Usage: delete <sandbox-id>")
                
                elif cmd == "stream":
                    await self.cmd_stream(args)
                
                elif cmd == "permissions":
                    self.cmd_permissions()
                
                elif cmd == "test":
                    if self.current_sandbox:
                        self.manager.test_sandbox_tools(self.current_sandbox)
                    else:
                        self.console.print("[yellow]No sandbox connected")
                
                else:
                    self.console.print(f"[red]Unknown command: {cmd}[/red]")
                    self.console.print("[dim]Type 'help' for available commands[/dim]")
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")


def main():
    """Main entry point"""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check if running in interactive mode
    if len(sys.argv) > 1:
        # Fallback to simple CLI for command-line arguments
        from daytona_manager_cleaned import main as simple_main
        simple_main()
    else:
        # Run enhanced interactive CLI
        cli = EnhancedCLI()
        asyncio.run(cli.run_interactive())


if __name__ == "__main__":
    main()