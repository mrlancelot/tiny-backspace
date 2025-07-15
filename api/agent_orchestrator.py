"""
Agent Orchestrator - Manages the complete flow from request to PR
Integrates sandbox management, repository operations, and agent execution
"""

import os
import asyncio
import re
from typing import AsyncGenerator, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from config import Settings
from models import StreamEvent, StreamEventType
from sse_adapter import SSEAdapter
import sys
import os
# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from daytona_manager_refactored import DaytonaManagerRefactored
from rich.console import Console


class AgentOrchestrator:
    """Orchestrates the complete agent workflow"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.sse_adapter = SSEAdapter()
        self.console = Console(quiet=True)  # Quiet mode for API usage
        self.manager = DaytonaManagerRefactored(console=self.console)
        
        # Base directory will be set dynamically based on sandbox
        self.base_dir = None
        # Full path to the cloned repository
        self.repo_path = None
        
        # Override permission checks for automated operation
        self.manager.permission_manager.saved_permissions = {
            "CREATE_SANDBOX": {"all": True},
            "EXECUTE_COMMAND": {"all": True},
            "DELETE_SANDBOX": {"all": True}
        }
    
    async def process_request(
        self,
        request_id: str,
        repo_url: str,
        prompt: str
    ) -> AsyncGenerator[StreamEvent, None]:
        """Process a code change request end-to-end"""
        
        sandbox = None
        sandbox_id = None
        
        try:
            # Extract repo info
            repo_parts = self._parse_github_url(repo_url)
            owner = repo_parts['owner']
            repo = repo_parts['repo']
            print(f"\nDEBUG: Starting request {request_id}")
            print(f"DEBUG: Repository: {owner}/{repo}")
            print(f"DEBUG: URL: {repo_url}")
            
            # Validate GitHub token for private repos or PR creation
            if not self.settings.github_token:
                yield StreamEvent(
                    type=StreamEventType.ERROR,
                    data={
                        "error_type": "ConfigurationError",
                        "message": "GitHub token is required for creating pull requests. Please set GITHUB_TOKEN in your environment.",
                        "request_id": request_id
                    }
                )
                return
            
            if not self.settings.github_username:
                yield StreamEvent(
                    type=StreamEventType.ERROR,
                    data={
                        "error_type": "ConfigurationError", 
                        "message": "GitHub username is required. Please set GITHUB_USERNAME in your environment.",
                        "request_id": request_id
                    }
                )
                return
            
            # Stage 1: Create sandbox
            yield await self.sse_adapter.create_progress_event(
                "cloning", 
                f"Creating secure sandbox environment",
                10
            )
            
            print(f"DEBUG: Creating sandbox with name: tb-{request_id[:8]}", flush=True)
            print(f"DEBUG: Sandbox type: {self.settings.agent_type}", flush=True)
            
            try:
                sandbox = await asyncio.to_thread(
                    self.manager.create_sandbox,
                    name=f"tb-{request_id[:8]}",
                    sandbox_type=self.settings.agent_type,  # Use configured agent type
                    resources={"cpu": 1, "memory": 2}  # Reduced memory to avoid quota
                )
            except Exception as create_error:
                print(f"ERROR: Sandbox creation failed with error: {create_error}", flush=True)
                import traceback
                traceback.print_exc()
                raise Exception(f"Failed to create sandbox: {str(create_error)}")
            
            if not sandbox:
                print("DEBUG: Sandbox creation returned None", flush=True)
                raise Exception("Failed to create sandbox")
            
            sandbox_id = sandbox.id
            
            # Initialize logging system
            await self._initialize_sandbox_logging(sandbox)
            
            # Detect the working directory in the sandbox
            self.base_dir = await self._detect_working_directory(sandbox)
            print(f"DEBUG: Detected base directory type: {type(self.base_dir)}")
            print(f"DEBUG: Detected base directory value: {repr(self.base_dir)}")
            print(f"DEBUG: Detected base directory: {self.base_dir}")
            
            # Log the initialization
            await self._log_to_sandbox(sandbox, f"Sandbox initialized: {sandbox_id}")
            await self._log_to_sandbox(sandbox, f"Base directory: {self.base_dir}")
            await self._log_to_sandbox(sandbox, f"Request ID: {request_id}")
            await self._log_to_sandbox(sandbox, f"Repository: {repo_url}")
            
            yield await self.sse_adapter.create_progress_event(
                "cloning",
                f"Sandbox created: {sandbox_id}",
                20
            )
            
            # Install Gemini CLI in the sandbox
            yield await self.sse_adapter.create_progress_event(
                "cloning",
                "Installing Gemini CLI",
                15
            )
            
            await self._install_gemini_cli(sandbox)
            
            # Stage 2: Clone repository
            yield await self.sse_adapter.create_progress_event(
                "cloning",
                f"Cloning repository {owner}/{repo}",
                30
            )
            
            clone_result = await self._clone_repository(sandbox, repo_url)
            print(f"DEBUG: Clone result: {clone_result}")
            
            if not clone_result['success']:
                raise Exception(f"Failed to clone repository: {clone_result.get('error', 'Unknown error')}")
            
            yield await self.sse_adapter.create_tool_event(
                "Bash",
                command=f"git clone {repo_url}",
                output="Repository cloned successfully"
            )
            
            # Debug: Check what was actually cloned
            ls_result = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                f"ls -la {self.base_dir}/",
                show_output=False
            )
            print(f"\nDEBUG: After clone, contents of {self.base_dir}:")
            print(ls_result)
            print(f"\nDEBUG: Current repo_path is: {self.repo_path}")
            
            # Also check if the repo directory exists
            repo_check = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                f"test -d {self.repo_path} && echo 'REPO EXISTS' || echo 'REPO NOT FOUND'",
                show_output=False
            )
            print(f"DEBUG: Repository directory check at {self.repo_path}: {repo_check.strip()}")
            
            # If repo doesn't exist, check what the actual directory name is
            if "NOT FOUND" in repo_check:
                print(f"DEBUG: Repository not found at expected location. Checking actual clone result...")
                # The issue might be that when cloning without specifying target, it uses the repo name from URL
                actual_check = await asyncio.to_thread(
                    self.manager.execute_command,
                    sandbox,
                    f"find {self.base_dir} -maxdepth 1 -name '*test*' -type d",
                    show_output=False
                )
                print(f"DEBUG: Found directories matching *test*: {actual_check}")
            
            # Stage 3: Setup environment
            yield await self.sse_adapter.create_progress_event(
                "analyzing",
                "Setting up development environment",
                40
            )
            
            await self._setup_git_config(sandbox)
            
            # Stage 4: Execute agent
            yield await self.sse_adapter.create_progress_event(
                "coding",
                "Analyzing codebase and planning changes",
                50
            )
            
            # Create branch
            branch_name = f"tb/{request_id[:8]}-{self._slugify(prompt[:30])}"
            print(f"\nDEBUG: Creating branch: {branch_name}")
            print(f"DEBUG: Working in repository at: {self.repo_path}")
            await self._create_branch(sandbox, repo, branch_name)
            
            yield await self.sse_adapter.create_tool_event(
                "Bash",
                command=f"git checkout -b {branch_name}",
                output=f"Switched to new branch '{branch_name}'"
            )
            
            # Execute Claude
            yield StreamEvent(
                type=StreamEventType.AI_MESSAGE,
                data={"message": "Starting code analysis and implementation..."}
            )
            
            # Stream agent execution
            async for event in self._execute_agent(sandbox, repo, prompt):
                yield event
            
            # Stage 5: Commit changes
            yield await self.sse_adapter.create_progress_event(
                "committing",
                "Analyzing and committing changes",
                80
            )
            
            # Emit change analysis events
            yield StreamEvent(
                type="change_analysis",
                data={"message": "Analyzing code changes..."}
            )
            
            commit_result = await self._commit_changes(sandbox, repo, prompt)
            print(f"\nDEBUG: Commit result: {commit_result}")
            print(f"DEBUG: Still working in: {self.repo_path}")
            
            if commit_result['files_changed'] == 0:
                raise Exception("No changes were made by the agent")
            
            # Emit detailed change summary
            changes = commit_result.get('changes', {})
            if changes:
                yield StreamEvent(
                    type="change_summary",
                    data={
                        "files_changed": changes.get('stats', {}).get('total', 0),
                        "additions": changes.get('stats', {}).get('additions', 0),
                        "deletions": changes.get('stats', {}).get('deletions', 0),
                        "categories": changes.get('categories', {}),
                        "commit_type": self._determine_commit_type(prompt, changes)
                    }
                )
            
            yield await self.sse_adapter.create_tool_event(
                "Bash",
                command="git commit",
                output=f"Committed {commit_result['files_changed']} files with {changes.get('stats', {}).get('additions', 0)} additions and {changes.get('stats', {}).get('deletions', 0)} deletions"
            )
            
            # Stage 6: Push and create PR
            yield await self.sse_adapter.create_progress_event(
                "pr_creation",
                "Pushing changes and creating pull request",
                90
            )
            
            # Debug: Check directory exists before PR creation
            print(f"DEBUG: About to create PR. repo_path={self.repo_path}, repo={repo}")
            check_dir = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                f"ls -la {self.repo_path} 2>&1 || echo 'Directory not found'",
                show_output=False
            )
            print(f"DEBUG: Before PR creation, checking {self.repo_path}: {check_dir[:200]}")
            
            # Emit PR preparation event
            yield StreamEvent(
                type="pr_preparation",
                data={
                    "message": "Generating comprehensive PR description...",
                    "files_analyzed": len(self.tool_usage.get('files_read', [])) if hasattr(self, 'tool_usage') else 0,
                    "files_changed": commit_result['files_changed']
                }
            )
            
            pr_result = await self._create_pull_request(
                sandbox, repo, branch_name, prompt, commit_result
            )
            
            if not pr_result['success']:
                raise Exception(f"Failed to create PR: {pr_result.get('error', 'Unknown error')}")
            
            yield await self.sse_adapter.create_tool_event(
                "Bash",
                command="gh pr create",
                output=pr_result['pr_url']
            )
            
            # Enhanced final success event with more details
            yield StreamEvent(
                type="pr_created",
                data={
                    "pr_url": pr_result['pr_url'],
                    "branch_name": branch_name,
                    "files_changed": commit_result['files_changed'],
                    "summary": commit_result['summary'],
                    "stats": changes.get('stats', {}) if changes else {},
                    "categories": changes.get('categories', {}) if changes else {},
                    "pr_title": pr_result.get('pr_title', f"Implement: {prompt[:60]}")
                }
            )
            
        except Exception as e:
            yield StreamEvent(
                type=StreamEventType.ERROR,
                data={
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "request_id": request_id
                }
            )
        
        finally:
            # Read and print final logs before cleanup
            if sandbox:
                try:
                    print("\n=== FINAL SANDBOX LOGS ===")
                    final_logs = await self._read_sandbox_logs(sandbox)
                    print(final_logs)
                    print("=== END LOGS ===\n")
                except Exception as e:
                    print(f"ERROR reading final logs: {e}")
                
                # Clean up temporary files before sandbox deletion
                try:
                    await self._cleanup_sandbox_temp_files(sandbox)
                except Exception as e:
                    print(f"DEBUG: Cleanup of temp files failed: {e}")
            
            # Cleanup sandbox
            if sandbox_id:
                try:
                    await asyncio.to_thread(
                        self.manager.delete_sandbox,
                        sandbox_id
                    )
                except:
                    pass  # Best effort cleanup
    
    def _parse_github_url(self, url: str) -> Dict[str, str]:
        """Parse GitHub URL to extract owner and repo"""
        # Handle both HTTPS and SSH formats
        url = url.strip()
        
        # HTTPS format: https://github.com/owner/repo or https://github.com/owner/repo.git
        https_match = re.match(r'https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', url)
        if https_match:
            return {
                'owner': https_match.group(1),
                'repo': https_match.group(2)
            }
        
        # SSH format: git@github.com:owner/repo.git
        ssh_match = re.match(r'git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$', url)
        if ssh_match:
            return {
                'owner': ssh_match.group(1),
                'repo': ssh_match.group(2)
            }
        
        # If neither format matches, provide helpful error
        raise ValueError(f"Invalid GitHub URL format: '{url}'. Expected formats: https://github.com/owner/repo or git@github.com:owner/repo.git")
    
    def _slugify(self, text: str) -> str:
        """Convert text to valid branch name component"""
        # Replace spaces and special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')
    
    async def _run_git_command(self, sandbox: Any, git_args: str, show_output: bool = False) -> str:
        """Run a git command in the repository directory using -C flag"""
        if not self.repo_path:
            print(f"ERROR: Repository path not set when trying to run: git {git_args}")
            raise ValueError("Repository path not set")
        
        # Use git -C to specify working directory
        command = f"git -C {self.repo_path} {git_args}"
        
        print(f"DEBUG: Running git command: {command}")
        
        try:
            result = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                command,
                show_output=show_output
            )
            print(f"DEBUG: Git command result: {result[:200] if result else 'empty'}")
            return result or ""
        except Exception as e:
            print(f"ERROR: Git command failed: {command}")
            print(f"ERROR: Exception: {e}")
            raise
    
    async def _verify_repository_exists(self, sandbox: Any) -> bool:
        """Verify the repository exists at the expected path"""
        try:
            print(f"\nDEBUG: Verifying repository at: {self.repo_path}")
            check_result = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                f"test -d {self.repo_path}/.git && echo 'EXISTS' || echo 'NOT_FOUND'",
                show_output=False
            )
            exists = "EXISTS" in check_result
            print(f"DEBUG: Repository exists check: {exists}")
            
            if not exists:
                # Additional debug info
                ls_result = await asyncio.to_thread(
                    self.manager.execute_command,
                    sandbox,
                    f"ls -la {self.base_dir}/",
                    show_output=False
                )
                print(f"DEBUG: Contents of {self.base_dir}:\n{ls_result}")
                
            return exists
        except Exception as e:
            print(f"ERROR: Repository verification failed: {e}")
            return False
    
    async def _detect_working_directory(self, sandbox: Any) -> str:
        """Detect the actual working directory in the sandbox"""
        try:
            # Get current working directory
            pwd_result = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                "pwd",
                show_output=False
            )
            
            # Also check HOME and other env vars
            env_result = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                "echo HOME=$HOME USER=$USER PWD=$PWD",
                show_output=False
            )
            
            if pwd_result:
                work_dir = pwd_result.strip()
                print(f"\nDEBUG: Detected sandbox working directory: {repr(pwd_result)}")
                print(f"DEBUG: Environment: {repr(env_result)}")
                print(f"DEBUG: Detected base directory: {work_dir}")
                return work_dir
            else:
                # Fallback to home directory
                print("DEBUG: Could not detect pwd, using /root")
                return "/root"
                
        except Exception as e:
            print(f"DEBUG: Error detecting working directory: {e}")
            # Fallback to home directory
            return "/root"
    
    async def _clone_repository(self, sandbox: Any, repo_url: str) -> Dict[str, Any]:
        """Clone repository in sandbox with authentication for private repos"""
        try:
            print(f"DEBUG: _clone_repository called with repo_url: {repo_url}", flush=True)
            # Parse repo URL to inject authentication
            repo_parts = self._parse_github_url(repo_url)
            owner = repo_parts['owner']
            repo_name = repo_parts['repo']
            
            # Set the repository path
            self.repo_path = f"{self.base_dir}/{repo_name}"
            print(f"\nDEBUG: Clone operation starting")
            print(f"DEBUG: Base directory: {self.base_dir}")
            print(f"DEBUG: Repository name: {repo_name}")
            print(f"DEBUG: Setting repo_path to: {self.repo_path}")
            
            # Log clone operation
            await self._log_to_sandbox(sandbox, f"Starting repository clone: {repo_url}")
            await self._log_to_sandbox(sandbox, f"Target path: {self.repo_path}")
            
            # Check if directory already exists
            dir_check = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                f"test -d {self.repo_path} && echo 'EXISTS' || echo 'NOT_EXISTS'",
                show_output=False
            )
            
            print(f"DEBUG: dir_check result: {dir_check}")
            
            if dir_check and "EXISTS" in dir_check:
                print(f"DEBUG: Directory {self.repo_path} already exists, removing it first")
                # Remove existing directory
                await asyncio.to_thread(
                    self.manager.execute_command,
                    sandbox,
                    f"rm -rf {self.repo_path}",
                    show_output=False
                )
            
            # If we have a GitHub token, use authenticated URL
            if self.settings.github_token and self.settings.github_username:
                # Use token as password with username for authentication
                auth_url = f"https://{self.settings.github_username}:{self.settings.github_token}@github.com/{owner}/{repo_name}.git"
                clone_cmd = f"cd {self.base_dir} && git clone --depth 1 {auth_url} {repo_name}"
                
                # Clone with authentication (hide token in output)
                result = await asyncio.to_thread(
                    self.manager.execute_command,
                    sandbox,
                    clone_cmd,
                    show_output=False
                )
                
                # Check if clone failed
                if result and ("fatal:" in result or "error:" in result.lower()):
                    print(f"DEBUG: Clone failed with output: {result}")
                    return {"success": False, "error": f"Clone failed: {result}"}
                
                # Remove credentials from git remote to avoid exposure
                await asyncio.to_thread(
                    self.manager.execute_command,
                    sandbox,
                    f"cd {self.repo_path} && git remote set-url origin {repo_url}",
                    show_output=False
                )
            else:
                # Try public clone  
                result = await asyncio.to_thread(
                    self.manager.execute_command,
                    sandbox,
                    f"cd {self.base_dir} && git clone --depth 1 {repo_url} {repo_name}",
                    show_output=False
                )
            
            # Verify the clone was successful and update repo_path if needed
            actual_repo_check = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                f"test -d {self.repo_path}/.git && echo 'FOUND' || echo 'NOT_FOUND'",
                show_output=False
            )
            
            if actual_repo_check and "NOT_FOUND" in actual_repo_check:
                print(f"WARNING: Repository not found at {self.repo_path} after clone")
                # Try to find where it was actually cloned
                find_result = await asyncio.to_thread(
                    self.manager.execute_command,
                    sandbox,
                    f"find {self.base_dir} -maxdepth 1 -type d -name '*{repo_name}*' 2>/dev/null",
                    show_output=False
                )
                print(f"DEBUG: Found directories: {find_result}")
                return {"success": False, "error": "Repository clone failed - directory not found after clone"}
            
            # Log successful clone
            await self._log_to_sandbox(sandbox, f"Repository cloned successfully")
            
            return {"success": True, "output": result}
            
        except Exception as e:
            error_msg = str(e)
            print(f"ERROR in _clone_repository: {error_msg}", flush=True)
            import traceback
            traceback.print_exc()
            if "Authentication failed" in error_msg or "could not read Username" in error_msg:
                return {"success": False, "error": "Authentication failed. Please check your GitHub token."}
            return {"success": False, "error": error_msg}
    
    async def _setup_git_config(self, sandbox: Any) -> None:
        """Configure git for commits and authentication"""
        commands = [
            f'git config --global user.name "{self.settings.github_username or "Tiny Backspace"}"',
            f'git config --global user.email "{self.settings.github_email or "bot@tinybackspace.dev"}"',
            'git config --global init.defaultBranch main'
        ]
        
        for cmd in commands:
            await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                cmd,
                show_output=False
            )
        
        # Setup GitHub CLI authentication early if token is available
        if self.settings.github_token:
            print(f"\nDEBUG: Setting up GitHub CLI authentication")
            print(f"DEBUG: Token exists: Yes, length: {len(self.settings.github_token)}")
            
            # Create a temporary file with the token to avoid command line exposure
            token_result = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                f'echo "{self.settings.github_token}" > /tmp/gh_token.txt',
                show_output=False
            )
            print(f"DEBUG: Token file created")
            
            # Authenticate GitHub CLI using the token file
            auth_result = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                'gh auth login --with-token < /tmp/gh_token.txt 2>&1',
                show_output=False
            )
            print(f"DEBUG: gh auth login result: {auth_result[:200] if auth_result else 'empty'}")
            
            # Remove the temporary token file
            await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                'rm -f /tmp/gh_token.txt',
                show_output=False
            )
            
            # Configure git to use GitHub CLI for authentication
            git_setup_result = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                'gh auth setup-git 2>&1',
                show_output=False
            )
            print(f"DEBUG: gh auth setup-git result: {git_setup_result[:200] if git_setup_result else 'empty'}")
            
            # Verify authentication
            status_result = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                'gh auth status 2>&1',
                show_output=False
            )
            print(f"DEBUG: gh auth status: {status_result[:300] if status_result else 'empty'}")
        else:
            print(f"DEBUG: No GitHub token available for authentication")
    
    async def _create_branch(self, sandbox: Any, repo: str, branch_name: str) -> None:
        """Create and checkout new branch"""
        await self._run_git_command(sandbox, f"checkout -b {branch_name}", show_output=False)
    
    async def _initialize_sandbox_logging(self, sandbox: Any) -> None:
        """Initialize logging system in the sandbox"""
        log_file = "/tmp/tiny-backspace.log"
        
        # Create log file and write header
        await asyncio.to_thread(
            self.manager.execute_command,
            sandbox,
            f"""touch {log_file} && echo "[$(date)] Tiny Backspace Execution Log" > {log_file}""",
            show_output=False
        )
        
        print(f"DEBUG: Initialized logging at {log_file}")
    
    async def _log_to_sandbox(self, sandbox: Any, message: str, level: str = "INFO") -> None:
        """Write a log entry to the sandbox log file"""
        log_file = "/tmp/tiny-backspace.log"
        log_entry = f"[$(date)] [{level}] {message}"
        
        await asyncio.to_thread(
            self.manager.execute_command,
            sandbox,
            f"""echo "{log_entry}" >> {log_file}""",
            show_output=False
        )
    
    async def _read_sandbox_logs(self, sandbox: Any, tail_lines: Optional[int] = None) -> str:
        """Read the execution logs from sandbox"""
        log_file = "/tmp/tiny-backspace.log"
        
        if tail_lines:
            cmd = f"tail -n {tail_lines} {log_file} 2>/dev/null || echo 'No logs found'"
        else:
            cmd = f"cat {log_file} 2>/dev/null || echo 'No logs found'"
            
        log_content = await asyncio.to_thread(
            self.manager.execute_command,
            sandbox,
            cmd,
            show_output=False
        )
        return log_content
    
    async def _cleanup_sandbox_temp_files(self, sandbox: Any) -> None:
        """Clean up temporary files created during execution"""
        # List of temporary files to clean up
        temp_files = [
            "/tmp/tiny-backspace.log",
            "/tmp/gemini-output.log",
            "/tmp/gemini-exec.log",
            "/tmp/run-gemini.sh",
            "/tmp/pr-body.md",
            "/tmp/gh_token.txt"
        ]
        
        # Build cleanup command
        cleanup_cmd = "rm -f " + " ".join(temp_files)
        
        # Execute cleanup
        await asyncio.to_thread(
            self.manager.execute_command,
            sandbox,
            cleanup_cmd,
            show_output=False
        )
        
        print("DEBUG: Cleaned up temporary files in sandbox")

    async def _execute_agent(
        self, 
        sandbox: Any, 
        repo: str,
        prompt: str
    ) -> AsyncGenerator[StreamEvent, None]:
        """Execute Claude agent and stream results"""
        
        # Track tool usage for better PR descriptions
        self.tool_usage = {
            "files_read": [],
            "files_edited": [],
            "files_created": [],
            "commands_run": [],
            "analysis_summary": []
        }
        
        # Format prompt for Claude
        agent_prompt = f"""You are working in the repository {self.repo_path}.
        
Task: {prompt}

Instructions:
1. First explore the repository structure to understand the codebase
2. Identify the files that need to be modified
3. Make the necessary changes to implement the requested feature
4. Ensure your changes follow the existing code style and conventions
5. Do not modify configuration files unless necessary
6. Focus only on the specific task requested

Start by exploring the repository structure."""
        
        # Initialize logging for this execution
        await self._log_to_sandbox(sandbox, f"Starting Gemini execution for task: {prompt}")
        await self._log_to_sandbox(sandbox, f"Repository path: {self.repo_path}")
        
        # Execute Gemini CLI with logging
        log_file = "/tmp/tiny-backspace.log"
        gemini_log = "/tmp/gemini-output.log"
        
        # Create a script to run Gemini with proper logging
        gemini_api_key = self.settings.gemini_api_key if hasattr(self.settings, 'gemini_api_key') else ""
        gemini_script = f"""#!/bin/bash
cd {self.repo_path}

echo "[$(date)] [INFO] Working directory: $(pwd)" >> {log_file}
echo "[$(date)] [INFO] Files in directory:" >> {log_file}
ls -la >> {log_file}

echo "[$(date)] [INFO] Starting Gemini CLI execution" >> {log_file}

# Export API key if available
export GEMINI_API_KEY="{gemini_api_key}"

# Run Gemini and capture output
gemini --prompt "{agent_prompt}" --yolo --all_files 2>&1 | tee {gemini_log}
GEMINI_EXIT_CODE=$?

echo "[$(date)] [INFO] Gemini execution completed with exit code: $GEMINI_EXIT_CODE" >> {log_file}

# Append Gemini output to main log
echo "[$(date)] [INFO] === Gemini Output Start ===" >> {log_file}
cat {gemini_log} >> {log_file}
echo "[$(date)] [INFO] === Gemini Output End ===" >> {log_file}

# Check for created/modified files
echo "[$(date)] [INFO] Git status after execution:" >> {log_file}
git status --porcelain >> {log_file}

exit $GEMINI_EXIT_CODE
"""
        
        # Write the script to the sandbox
        script_path = "/tmp/run-gemini.sh"
        await asyncio.to_thread(
            self.manager.execute_command,
            sandbox,
            f'cat > {script_path} << \'EOF\'\n{gemini_script}\nEOF',
            show_output=False
        )
        
        # Make script executable
        await asyncio.to_thread(
            self.manager.execute_command,
            sandbox,
            f'chmod +x {script_path}',
            show_output=False
        )
        
        print(f"\nDEBUG: Executing Gemini with logging in {self.repo_path}")
        
        # Execute the script asynchronously
        yield await self.sse_adapter.create_tool_event(
            "AI Message",
            message="Starting code analysis and implementation...",
            thinking=True
        )
        
        try:
            # Start Gemini execution in background
            await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                f'nohup {script_path} > /tmp/gemini-exec.log 2>&1 &',
                show_output=False
            )
            
            # Monitor execution through logs
            await self._log_to_sandbox(sandbox, "Gemini execution started in background")
            
            # Monitor logs and yield progress events
            async for event in self._monitor_gemini_execution(sandbox):
                yield event
                
        except Exception as e:
            await self._log_to_sandbox(sandbox, f"Error during Gemini execution: {str(e)}", "ERROR")
            yield await self.sse_adapter.create_tool_event(
                "Error",
                message=f"Agent execution failed: {str(e)}"
            )
    
    async def _monitor_gemini_execution(self, sandbox: Any, max_duration: int = 300) -> AsyncGenerator[StreamEvent, None]:
        """Monitor Gemini execution through logs"""
        log_file = "/tmp/tiny-backspace.log"
        start_time = datetime.now()
        last_log_size = 0
        execution_complete = False
        
        while not execution_complete:
            # Check if we've exceeded max duration
            if (datetime.now() - start_time).seconds > max_duration:
                await self._log_to_sandbox(sandbox, "Execution timeout reached", "WARNING")
                yield await self.sse_adapter.create_tool_event(
                    "Timeout",
                    message=f"Execution exceeded {max_duration} seconds"
                )
                break
            
            # Read the latest logs
            log_content = await self._read_sandbox_logs(sandbox)
            
            # Check for new content
            if len(log_content) > last_log_size:
                new_content = log_content[last_log_size:]
                last_log_size = len(log_content)
                
                # Parse new log entries for progress
                for line in new_content.split('\n'):
                    if not line.strip():
                        continue
                    
                    # Check for completion
                    if "Gemini execution completed with exit code:" in line:
                        execution_complete = True
                        if "exit code: 0" in line:
                            yield await self.sse_adapter.create_tool_event(
                                "AI Message",
                                message="Code implementation completed successfully"
                            )
                        else:
                            yield await self.sse_adapter.create_tool_event(
                                "Error",
                                message="Gemini execution failed"
                            )
                    
                    # Check for file operations
                    elif "Creating file:" in line or "Writing to:" in line:
                        yield await self.sse_adapter.create_tool_event(
                            "File Write",
                            message=line.split("] ")[-1]
                        )
                    elif "Editing file:" in line or "Modifying:" in line:
                        yield await self.sse_adapter.create_tool_event(
                            "File Edit",
                            message=line.split("] ")[-1]
                        )
                    elif "Reading file:" in line:
                        yield await self.sse_adapter.create_tool_event(
                            "File Read",
                            message=line.split("] ")[-1]
                        )
                    elif "Executing:" in line or "Running command:" in line:
                        yield await self.sse_adapter.create_tool_event(
                            "Bash",
                            message=line.split("] ")[-1]
                        )
            
            # Check if process is still running
            check_process = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                "pgrep -f 'gemini.*--prompt' > /dev/null && echo 'RUNNING' || echo 'STOPPED'",
                show_output=False
            )
            
            if "STOPPED" in check_process and not execution_complete:
                # Process ended but we didn't see completion - check exit status
                await asyncio.sleep(2)  # Give logs time to flush
                final_logs = await self._read_sandbox_logs(sandbox, tail_lines=50)
                
                if "Gemini execution completed" not in final_logs:
                    execution_complete = True
                    yield await self.sse_adapter.create_tool_event(
                        "AI Message",
                        message="Gemini process completed"
                    )
            
            # Wait before next check
            await asyncio.sleep(2)
        
        # Parse final results
        final_logs = await self._read_sandbox_logs(sandbox)
        
        # Extract tool usage from logs
        await self._extract_tool_usage_from_logs(final_logs)
        
        # Check git status for changes
        git_status = await asyncio.to_thread(
            self.manager.execute_command,
            sandbox,
            f"cd {self.repo_path} && git status --porcelain",
            show_output=False
        )
        
        if git_status.strip():
            files_changed = len(git_status.strip().split('\n'))
            yield await self.sse_adapter.create_tool_event(
                "AI Message",
                message=f"Modified {files_changed} file(s)"
            )
    
    async def _extract_tool_usage_from_logs(self, log_content: str) -> None:
        """Extract tool usage information from logs for PR description"""
        for line in log_content.split('\n'):
            if "Creating file:" in line or "Writing to:" in line:
                filename = line.split(":")[-1].strip()
                if filename and filename not in self.tool_usage["files_created"]:
                    self.tool_usage["files_created"].append(filename)
            elif "Editing file:" in line or "Modifying:" in line:
                filename = line.split(":")[-1].strip()
                if filename and filename not in self.tool_usage["files_edited"]:
                    self.tool_usage["files_edited"].append(filename)
            elif "Reading file:" in line:
                filename = line.split(":")[-1].strip()
                if filename and filename not in self.tool_usage["files_read"]:
                    self.tool_usage["files_read"].append(filename)
            elif "Git status after execution:" in line:
                # Mark that we found the git status section
                pass
    
    async def _parse_gemini_output(self, output: str, sandbox: Any) -> AsyncGenerator[StreamEvent, None]:
        """Parse Gemini's output and track tool usage"""
        lines = output.strip().split('\n')
        
        # Gemini output patterns
        tool_patterns = {
            'read': re.compile(r'Reading file:\s*(.+)'),
            'write': re.compile(r'Writing to file:\s*(.+)'),
            'edit': re.compile(r'Editing file:\s*(.+)'),
            'bash': re.compile(r'Executing command:\s*(.+)'),
            'analyze': re.compile(r'Analyzing:\s*(.+)'),
            'git': re.compile(r'Git operation:\s*(.+)')
        }
        
        for line in lines:
            if not line.strip():
                continue
            
            # Check for tool usage patterns
            matched = False
            for tool_type, pattern in tool_patterns.items():
                match = pattern.search(line)
                if match:
                    matched = True
                    content = match.group(1).strip()
                    
                    if tool_type == 'read':
                        self.tool_usage["files_read"].append(content)
                        yield await self.sse_adapter.create_tool_event(
                            "Read",
                            filepath=content
                        )
                    elif tool_type == 'write':
                        self.tool_usage["files_created"].append(content)
                        yield await self.sse_adapter.create_tool_event(
                            "Edit",
                            filepath=content,
                            new_str="[File created/updated]"
                        )
                    elif tool_type == 'edit':
                        self.tool_usage["files_edited"].append(content)
                        yield await self.sse_adapter.create_tool_event(
                            "Edit",
                            filepath=content
                        )
                    elif tool_type == 'bash':
                        self.tool_usage["commands_run"].append(content)
                        yield await self.sse_adapter.create_tool_event(
                            "Bash",
                            command=content
                        )
                    elif tool_type == 'analyze':
                        self.tool_usage["analysis_summary"].append(content)
                        yield await self.sse_adapter.create_tool_event(
                            "AI Message",
                            message=f"Analyzing: {content}"
                        )
                    break
            
            # Check for Git operations
            if not matched and any(keyword in line.lower() for keyword in ['git', 'commit', 'push', 'branch']):
                self.tool_usage["commands_run"].append(line.strip())
                yield await self.sse_adapter.create_tool_event(
                    "Bash",
                    command=line.strip()
                )
            
            # Default to AI message
            elif not matched:
                yield await self.sse_adapter.create_tool_event(
                    "AI Message",
                    message=line.strip()
                )
    
    async def _analyze_changes(self, sandbox: Any) -> Dict[str, Any]:
        """Analyze the changes made using git diff"""
        try:
            # Get list of changed files with status
            status_output = await self._run_git_command(sandbox, "status --porcelain", show_output=False)
            
            if not status_output or not status_output.strip():
                return {
                    "files": [],
                    "stats": {"total": 0, "additions": 0, "deletions": 0},
                    "summary": "No changes detected"
                }
            
            # Parse status output
            files_info = []
            for line in status_output.strip().split('\n'):
                if line:
                    # Git status format: XY filename
                    status = line[:2].strip()
                    filename = line[3:].strip()
                    
                    action = "modified"
                    if status == "A" or status == "??":
                        action = "added"
                    elif status == "D":
                        action = "deleted"
                    elif status == "M":
                        action = "modified"
                    
                    files_info.append({
                        "path": filename,
                        "action": action,
                        "status": status
                    })
            
            # Get detailed diff statistics
            diff_stat = await self._run_git_command(sandbox, "diff --cached --stat", show_output=False)
            
            # Get detailed diff for each file
            for file_info in files_info:
                if file_info["action"] != "deleted":
                    # Get number of lines changed for this file
                    file_diff = await self._run_git_command(
                        sandbox, 
                        f"diff --cached --numstat -- {file_info['path']}", 
                        show_output=False
                    )
                    if file_diff:
                        parts = file_diff.strip().split('\t')
                        if len(parts) >= 3:
                            file_info["additions"] = int(parts[0]) if parts[0] != '-' else 0
                            file_info["deletions"] = int(parts[1]) if parts[1] != '-' else 0
            
            # Calculate total stats
            total_additions = sum(f.get("additions", 0) for f in files_info)
            total_deletions = sum(f.get("deletions", 0) for f in files_info)
            
            # Categorize changes by file type
            categories = {}
            for file_info in files_info:
                ext = Path(file_info["path"]).suffix.lower()
                category = self._categorize_file(ext)
                if category not in categories:
                    categories[category] = []
                categories[category].append(file_info["path"])
            
            return {
                "files": files_info,
                "stats": {
                    "total": len(files_info),
                    "additions": total_additions,
                    "deletions": total_deletions
                },
                "categories": categories,
                "summary": diff_stat or f"Modified {len(files_info)} files"
            }
            
        except Exception as e:
            print(f"ERROR: Failed to analyze changes: {e}")
            return {
                "files": [],
                "stats": {"total": 0, "additions": 0, "deletions": 0},
                "summary": f"Analysis failed: {str(e)}"
            }
    
    def _categorize_file(self, extension: str) -> str:
        """Categorize file by extension"""
        categories = {
            "code": [".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cpp", ".c", ".h", ".go", ".rs", ".rb", ".php"],
            "config": [".json", ".yaml", ".yml", ".toml", ".ini", ".env", ".gitignore"],
            "docs": [".md", ".rst", ".txt", ".pdf", ".docx"],
            "styles": [".css", ".scss", ".sass", ".less"],
            "tests": ["_test.py", ".test.js", ".spec.js", "_spec.rb"],
            "data": [".csv", ".xml", ".sql"]
        }
        
        for category, extensions in categories.items():
            if extension in extensions:
                return category
        return "other"

    async def _commit_changes(
        self, 
        sandbox: Any, 
        repo: str,
        prompt: str
    ) -> Dict[str, Any]:
        """Commit changes made by agent"""
        try:
            print(f"\nDEBUG: Starting commit process")
            print(f"DEBUG: Working in: {self.repo_path}")
            
            # Log commit process
            await self._log_to_sandbox(sandbox, "Starting commit process")
            await self._log_to_sandbox(sandbox, f"Working directory: {self.repo_path}")
            
            # Check for changes
            status_output = await self._run_git_command(sandbox, "status --porcelain", show_output=False)
            
            await self._log_to_sandbox(sandbox, f"Git status output: {status_output.strip() if status_output else 'No changes'}")
            
            if not status_output or not status_output.strip():
                await self._log_to_sandbox(sandbox, "No changes detected - nothing to commit")
                return {
                    "files_changed": 0,
                    "summary": "No changes made",
                    "changes": {}
                }
            
            # Analyze changes before staging
            change_analysis = await self._analyze_changes(sandbox)
            
            # Stage all changes
            await self._run_git_command(sandbox, "add -A", show_output=False)
            
            # Re-analyze after staging to get cached diff
            staged_analysis = await self._analyze_changes(sandbox)
            
            # Generate enhanced commit message
            commit_type = self._determine_commit_type(prompt, staged_analysis)
            commit_message = self._generate_commit_message(commit_type, prompt, staged_analysis)
            
            # Commit with enhanced message
            await self._run_git_command(sandbox, f'commit -m "{commit_message}"', show_output=False)
            
            # Get diff summary
            diff_summary = await self._run_git_command(sandbox, "diff HEAD^ --stat", show_output=False)
            
            return {
                "files_changed": staged_analysis["stats"]["total"],
                "summary": diff_summary or f"Modified {staged_analysis['stats']['total']} files",
                "changes": staged_analysis
            }
            
        except Exception as e:
            return {
                "files_changed": 0,
                "summary": f"Commit failed: {str(e)}",
                "changes": {}
            }
    
    def _determine_commit_type(self, prompt: str, analysis: Dict[str, Any]) -> str:
        """Determine commit type based on prompt and changes"""
        prompt_lower = prompt.lower()
        
        # Check prompt for keywords in priority order
        if any(word in prompt_lower for word in ["fix", "bug", "error", "issue"]):
            return "fix"
        elif any(word in prompt_lower for word in ["test", "spec"]):
            return "test"
        elif any(word in prompt_lower for word in ["refactor", "restructure", "reorganize"]):
            return "refactor"
        elif any(word in prompt_lower for word in ["document", "docs", "readme"]):
            return "docs"
        elif any(word in prompt_lower for word in ["style", "format", "lint"]):
            return "style"
        elif any(word in prompt_lower for word in ["add", "new", "create", "implement"]):
            return "feat"
        
        # Check file types if prompt doesn't give clear indication
        categories = analysis.get("categories", {})
        if "tests" in categories:
            return "test"
        elif "docs" in categories and len(categories) == 1:
            return "docs"
        elif "styles" in categories and len(categories) == 1:
            return "style"
        
        return "feat"  # Default to feature
    
    def _generate_commit_message(self, commit_type: str, prompt: str, analysis: Dict[str, Any]) -> str:
        """Generate a detailed commit message"""
        # Title line (50 chars max)
        title = f"{commit_type}: {prompt[:50]}"
        if len(prompt) > 50:
            title = title.rstrip() + "..."
        
        # Body with details
        body_lines = [
            "",
            f"Task: {prompt}",
            "",
            "Changes made:",
        ]
        
        # Group files by category
        categories = analysis.get("categories", {})
        for category, files in categories.items():
            if files:
                body_lines.append(f"- {category.capitalize()}:")
                for file in files[:5]:  # Limit to 5 files per category
                    body_lines.append(f"  - {file}")
                if len(files) > 5:
                    body_lines.append(f"  - ... and {len(files) - 5} more")
        
        # Add statistics
        stats = analysis.get("stats", {})
        if stats.get("total", 0) > 0:
            body_lines.extend([
                "",
                f"Impact: {stats['total']} files changed, +{stats['additions']}/-{stats['deletions']} lines",
            ])
        
        body_lines.extend([
            "",
            "Generated by Tiny Backspace with Claude Code"
        ])
        
        return title + "\n" + "\n".join(body_lines)
    
    async def _create_pull_request(
        self,
        sandbox: Any,
        repo: str,
        branch_name: str,
        prompt: str,
        commit_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Push changes and create pull request"""
        try:
            print(f"\nDEBUG: Starting PR creation")
            print(f"DEBUG: Repository name parameter: {repo}")
            print(f"DEBUG: Current repo_path: {self.repo_path}")
            print(f"DEBUG: Branch name: {branch_name}")
            
            # Verify repository exists before proceeding
            if not await self._verify_repository_exists(sandbox):
                print(f"ERROR: Repository not found at {self.repo_path}")
                # Try to find where it actually is
                ls_result = await asyncio.to_thread(
                    self.manager.execute_command,
                    sandbox,
                    f"find {self.base_dir} -name '.git' -type d 2>/dev/null | head -5",
                    show_output=False
                )
                print(f"DEBUG: Found .git directories at: {ls_result}")
                raise ValueError(f"Repository not found at expected path: {self.repo_path}")
            
            # GitHub CLI should already be authenticated from _setup_git_config
            
            # For private repos, we need to set up push authentication
            if self.settings.github_token and self.settings.github_username:
                # Get the current remote URL
                try:
                    remote_url_result = await self._run_git_command(sandbox, "remote get-url origin", show_output=False)
                    
                    # Clean up the remote URL (remove any trailing newlines or spaces)
                    remote_url = remote_url_result.strip() if remote_url_result else ""
                    
                    # Debug logging
                    print(f"DEBUG: Remote URL from git: '{remote_url}'")
                    print(f"DEBUG: Using repo path: '{self.repo_path}'")
                    
                    # Parse and create authenticated push URL
                    repo_parts = self._parse_github_url(remote_url)
                    owner = repo_parts['owner']
                    repo_name = repo_parts['repo']
                    print(f"DEBUG: Parsed from remote URL - owner: {owner}, repo: {repo_name}")
                except Exception as e:
                    print(f"ERROR: Failed to get/parse remote URL: {e}")
                    print(f"ERROR: Remote URL was: '{remote_url}'")
                    raise
                auth_push_url = f"https://{self.settings.github_username}:{self.settings.github_token}@github.com/{owner}/{repo_name}.git"
                
                # Temporarily set authenticated URL for push
                await self._run_git_command(sandbox, f"remote set-url origin {auth_push_url}", show_output=False)
            
            # Push branch
            print(f"\nDEBUG: Pushing branch {branch_name} to origin")
            push_result = await self._run_git_command(sandbox, f"push -u origin {branch_name}", show_output=False)
            print(f"DEBUG: Push completed successfully")
            
            # Reset remote URL to remove credentials
            if self.settings.github_token and self.settings.github_username:
                await self._run_git_command(
                    sandbox, 
                    f"remote set-url origin https://github.com/{owner}/{repo_name}.git",
                    show_output=False
                )
            
            # Generate enhanced PR description
            pr_title = self._generate_pr_title(prompt, commit_result)
            pr_body = await self._generate_pr_body(sandbox, prompt, commit_result, owner, repo_name, branch_name)
            
            # GitHub CLI needs to be run from the repo directory
            print(f"\nDEBUG: Creating PR with gh CLI")
            print(f"DEBUG: Working directory: {self.repo_path}")
            print(f"DEBUG: PR title: {pr_title}")
            
            # First verify we're in the right directory and branch
            verify_cmd = f"cd {self.repo_path} && pwd && git branch --show-current"
            verify_result = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                verify_cmd,
                show_output=False
            )
            print(f"DEBUG: Pre-PR verification - pwd and branch: {verify_result}")
            
            # Create the PR with detailed error capture
            # Write PR body to a temporary file to avoid shell escaping issues
            pr_body_file = "/tmp/pr-body.md"
            write_body_cmd = f'''cat > {pr_body_file} << 'PREOF'
{pr_body}
PREOF'''
            await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                write_body_cmd,
                show_output=False
            )
            
            pr_cmd = f'''cd {self.repo_path} && gh pr create \\
                    --title "{pr_title}" \\
                    --body-file {pr_body_file} \\
                    --base main \\
                    --head {branch_name} 2>&1'''
            
            print(f"DEBUG: PR command: {pr_cmd[:200]}...")
            
            pr_output = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                pr_cmd,
                show_output=False
            )
            
            print(f"DEBUG: PR creation output: {pr_output}")
            
            # If PR creation failed, try to get more info
            if not pr_output or "error" in pr_output.lower() or "fatal" in pr_output.lower():
                print(f"DEBUG: PR creation may have failed. Getting more info...")
                
                # Check git remote
                remote_check = await asyncio.to_thread(
                    self.manager.execute_command,
                    sandbox,
                    f"cd {self.repo_path} && git remote -v",
                    show_output=False
                )
                print(f"DEBUG: Git remotes: {remote_check}")
                
                # Check if branch was pushed
                branch_check = await asyncio.to_thread(
                    self.manager.execute_command,
                    sandbox,
                    f"cd {self.repo_path} && git branch -r | grep {branch_name}",
                    show_output=False
                )
                print(f"DEBUG: Remote branch exists: {branch_check}")
            
            # Extract PR URL from output
            pr_url_match = re.search(r'https://github\.com/[^\s]+/pull/\d+', pr_output or '')
            
            if pr_url_match:
                pr_url = pr_url_match.group(0)
                print(f"\nDEBUG: PR created successfully: {pr_url}")
                return {
                    "success": True,
                    "pr_url": pr_url,
                    "pr_title": pr_title
                }
            else:
                print(f"ERROR: Could not extract PR URL from output: {pr_output}")
                return {
                    "success": False,
                    "error": "Could not extract PR URL from output"
                }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_pr_title(self, prompt: str, commit_result: Dict[str, Any]) -> str:
        """Generate a descriptive PR title"""
        # Get commit type from changes
        changes = commit_result.get("changes", {})
        commit_type = self._determine_commit_type(prompt, changes)
        
        # Clean up prompt for title
        clean_prompt = prompt.strip()
        if len(clean_prompt) > 50:
            clean_prompt = clean_prompt[:50].rstrip() + "..."
        
        # Format based on commit type with conventional commit format
        if commit_type == "fix":
            return f"fix: {clean_prompt}"
        elif commit_type == "feat":
            return f"feat: {clean_prompt}"
        elif commit_type == "refactor":
            return f"refactor: {clean_prompt}"
        elif commit_type == "docs":
            return f"docs: {clean_prompt}"
        elif commit_type == "test":
            return f"test: {clean_prompt}"
        elif commit_type == "style":
            return f"style: {clean_prompt}"
        else:
            return clean_prompt
    
    async def _generate_pr_body(
        self, 
        sandbox: Any,
        prompt: str, 
        commit_result: Dict[str, Any],
        owner: str,
        repo_name: str,
        branch_name: str
    ) -> str:
        """Generate a comprehensive PR body with all changes"""
        changes = commit_result.get("changes", {})
        
        # Get the actual diff for code snippets
        diff_output = await self._run_git_command(sandbox, "diff main...HEAD", show_output=False)
        
        body_sections = []
        
        # Summary section
        body_sections.append(f"""## Summary

**Task:** {prompt}

**Impact:** {changes.get('stats', {}).get('total', 0)} files changed | +{changes.get('stats', {}).get('additions', 0)} lines | -{changes.get('stats', {}).get('deletions', 0)} lines""")
        
        # Implementation approach (from Claude's analysis)
        if hasattr(self, 'tool_usage') and self.tool_usage.get('analysis_summary'):
            body_sections.append("""## Implementation Approach

""" + "\n".join(f"- {summary}" for summary in self.tool_usage['analysis_summary'][:5]))
        
        # Files changed section
        if changes.get('files'):
            body_sections.append(self._generate_files_section(changes))
        
        # Technical details from Claude's tool usage
        if hasattr(self, 'tool_usage'):
            body_sections.append(self._generate_technical_details())
        
        # Code highlights (show key changes)
        if diff_output:
            body_sections.append(self._generate_code_highlights(diff_output, changes))
        
        # Testing checklist
        body_sections.append(self._generate_testing_checklist(changes))
        
        # Footer
        body_sections.append(f"""---

### Generated by [Tiny Backspace](https://github.com/pridhvi007/tiny-backspace) with Claude Code

This PR was automatically generated based on the prompt above. The implementation was done by Claude Code in a sandboxed environment.

**Branch:** `{branch_name}`
**Request ID:** `{self.base_dir.split('-')[-1] if self.base_dir else 'unknown'}`""")
        
        return "\n\n".join(body_sections)
    
    def _generate_files_section(self, changes: Dict[str, Any]) -> str:
        """Generate the files changed section"""
        section = "## Files Changed\n"
        
        categories = changes.get('categories', {})
        if not categories:
            return section + "\nNo categorized changes found."
        
        for category, files in categories.items():
            if files:
                section += f"\n### {category.capitalize()}\n"
                for file in files:
                    # Find the file info
                    file_info = next((f for f in changes.get('files', []) if f['path'] == file), None)
                    if file_info:
                        action_prefix = {"added": "[Added]", "modified": "[Modified]", "deleted": "[Deleted]"}.get(file_info['action'], "[Changed]")
                        stats = ""
                        if 'additions' in file_info or 'deletions' in file_info:
                            stats = f" (+{file_info.get('additions', 0)}/-{file_info.get('deletions', 0)})"
                        section += f"- {action_prefix} `{file}`{stats}\n"
                    else:
                        section += f"- [Changed] `{file}`\n"
        
        return section
    
    def _generate_technical_details(self) -> str:
        """Generate technical details from tool usage"""
        if not hasattr(self, 'tool_usage'):
            return ""
        
        section = "## Technical Details\n"
        
        # Files analyzed
        if self.tool_usage.get('files_read'):
            section += f"\n**Files Analyzed:** {len(self.tool_usage['files_read'])}\n"
            for file in self.tool_usage['files_read'][:5]:
                section += f"- `{file}`\n"
            if len(self.tool_usage['files_read']) > 5:
                section += f"- ... and {len(self.tool_usage['files_read']) - 5} more\n"
        
        # Commands executed
        if self.tool_usage.get('commands_run'):
            section += f"\n**Commands Executed:**\n"
            for cmd in self.tool_usage['commands_run'][:3]:
                section += f"```bash\n{cmd}\n```\n"
        
        return section
    
    def _generate_code_highlights(self, diff_output: str, changes: Dict[str, Any]) -> str:
        """Generate code highlights section showing key changes"""
        section = "## Key Changes\n"
        
        # Parse diff to find interesting changes
        current_file = None
        interesting_chunks = []
        chunk_lines = []
        
        for line in diff_output.split('\n'):
            if line.startswith('diff --git'):
                # Save previous chunk if interesting
                if current_file and chunk_lines and len(chunk_lines) < 20:
                    interesting_chunks.append((current_file, '\n'.join(chunk_lines)))
                # Start new file
                match = re.search(r'b/(.+)$', line)
                current_file = match.group(1) if match else None
                chunk_lines = []
            elif line.startswith('@@'):
                # New chunk - save previous if small
                if chunk_lines and len(chunk_lines) < 20:
                    interesting_chunks.append((current_file, '\n'.join(chunk_lines)))
                chunk_lines = [line]
            elif current_file and (line.startswith('+') or line.startswith('-')):
                chunk_lines.append(line)
        
        # Add last chunk
        if current_file and chunk_lines and len(chunk_lines) < 20:
            interesting_chunks.append((current_file, '\n'.join(chunk_lines)))
        
        # Show up to 3 interesting changes
        shown = 0
        for file, chunk in interesting_chunks[:3]:
            if shown >= 3:
                break
            # Skip test files for highlights
            if 'test' in file.lower() or 'spec' in file.lower():
                continue
            
            lang = self._detect_language(file)
            section += f"\n### `{file}`\n```{lang}\n{chunk}\n```\n"
            shown += 1
        
        if not shown:
            section += "\nSee the full diff for detailed changes.\n"
        
        return section
    
    def _detect_language(self, filepath: str) -> str:
        """Detect language from file extension"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'jsx',
            '.tsx': 'tsx',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.css': 'css',
            '.html': 'html',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.sh': 'bash',
            '.sql': 'sql'
        }
        
        ext = Path(filepath).suffix.lower()
        return ext_map.get(ext, 'diff')
    
    def _generate_testing_checklist(self, changes: Dict[str, Any]) -> str:
        """Generate testing checklist based on changes"""
        section = "## Testing Checklist\n\n"
        
        categories = changes.get('categories', {})
        
        # Basic checks
        section += "- [ ] Code compiles without errors\n"
        section += "- [ ] No linting errors introduced\n"
        
        # Category-specific checks
        if 'code' in categories:
            section += "- [ ] Unit tests pass\n"
            section += "- [ ] Integration tests pass (if applicable)\n"
            section += "- [ ] Manual testing completed\n"
        
        if 'config' in categories:
            section += "- [ ] Configuration changes validated\n"
            section += "- [ ] Environment variables documented (if added)\n"
        
        if 'styles' in categories:
            section += "- [ ] Visual changes reviewed\n"
            section += "- [ ] Cross-browser compatibility checked\n"
        
        if 'docs' in categories:
            section += "- [ ] Documentation builds correctly\n"
            section += "- [ ] Links and references are valid\n"
        
        # Performance check for significant changes
        if changes.get('stats', {}).get('additions', 0) > 100:
            section += "- [ ] Performance impact assessed\n"
        
        return section
    
    async def _install_gemini_cli(self, sandbox: Any) -> None:
        """Install Gemini CLI in the sandbox"""
        # First, remove any existing Node.js to ensure clean installation
        await asyncio.to_thread(
            self.manager.execute_command,
            sandbox,
            "apt-get remove -y nodejs npm 2>/dev/null || true",
            show_output=False
        )
        
        # Install Node.js 18+ first (required for optional chaining support)
        nodejs_commands = [
            # Update package list
            "apt-get update -qq",
            # Install curl and ca-certificates
            "apt-get install -y curl ca-certificates gnupg",
            # Add NodeSource repository
            "mkdir -p /etc/apt/keyrings",
            "curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg",
            "echo 'deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_18.x nodistro main' > /etc/apt/sources.list.d/nodesource.list",
            # Update and install Node.js
            "apt-get update -qq",
            "apt-get install -y nodejs",
            # Verify Node.js version
            "node --version && npm --version"
        ]
        
        print("DEBUG: Installing Node.js 18+...")
        for cmd in nodejs_commands:
            try:
                result = await asyncio.to_thread(
                    self.manager.execute_command,
                    sandbox,
                    cmd,
                    show_output=False
                )
                if cmd.endswith("--version"):
                    print(f"DEBUG: Node.js installation result: {result}")
            except Exception as e:
                print(f"ERROR: Failed to run Node.js setup '{cmd[:50]}...': {e}")
        
        # Now install other dependencies and Gemini CLI
        install_commands = [
            # Install required dependencies
            "apt-get install -y git python3 python3-pip",
            # Install GitHub CLI
            "curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg",
            'echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null',
            "apt-get update -qq && apt-get install -y gh",
            # Install Gemini CLI globally with the new Node.js
            "npm install -g @google/gemini-cli",
            # Verify installation
            "gemini --version || echo 'Gemini installation verification failed'",
            # Set up Gemini configuration if API key is available
            f"mkdir -p ~/.gemini && echo '{{\"apiKey\": \"{self.settings.gemini_api_key}\"}}' > ~/.gemini/settings.json" if hasattr(self.settings, 'gemini_api_key') and self.settings.gemini_api_key else "echo 'No Gemini API key configured'"
        ]
        
        for cmd in install_commands:
            try:
                result = await asyncio.to_thread(
                    self.manager.execute_command,
                    sandbox,
                    cmd,
                    show_output=False
                )
                if "error" in str(result).lower() and "No Claude API key" not in str(result):
                    print(f"WARNING: Command '{cmd[:50]}...' had warnings: {result[:100]}")
                elif "gemini --version" in cmd:
                    print(f"DEBUG: Gemini CLI version: {result}")
            except Exception as e:
                print(f"ERROR: Failed to run '{cmd[:50]}...': {e}")
                # Continue with other commands