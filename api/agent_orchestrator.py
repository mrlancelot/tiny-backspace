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
sys.path.append('..')
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
            
            sandbox = await asyncio.to_thread(
                self.manager.create_sandbox,
                name=f"tb-{request_id[:8]}",
                sandbox_type="claude",
                resources={"cpu": 2, "memory": 4}
            )
            
            if not sandbox:
                raise Exception("Failed to create sandbox")
            
            sandbox_id = sandbox.id
            
            # Detect the working directory in the sandbox
            self.base_dir = await self._detect_working_directory(sandbox)
            print(f"DEBUG: Detected base directory: {self.base_dir}")
            
            yield await self.sse_adapter.create_progress_event(
                "cloning",
                f"Sandbox created: {sandbox_id}",
                20
            )
            
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
                "Committing changes",
                80
            )
            
            commit_result = await self._commit_changes(sandbox, repo, prompt)
            print(f"\nDEBUG: Commit result: {commit_result}")
            print(f"DEBUG: Still working in: {self.repo_path}")
            
            if commit_result['files_changed'] == 0:
                raise Exception("No changes were made by the agent")
            
            yield await self.sse_adapter.create_tool_event(
                "Bash",
                command="git commit",
                output=f"Committed {commit_result['files_changed']} files"
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
            
            # Final success event
            yield StreamEvent(
                type="pr_created",
                data={
                    "pr_url": pr_result['pr_url'],
                    "branch_name": branch_name,
                    "files_changed": commit_result['files_changed'],
                    "summary": commit_result['summary']
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
                print(f"\nDEBUG: Detected sandbox working directory: {work_dir}")
                print(f"DEBUG: Environment: {env_result.strip()}")
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
            
            # Check if directory already exists
            dir_check = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                f"test -d {self.repo_path} && echo 'EXISTS' || echo 'NOT_EXISTS'",
                show_output=False
            )
            
            if "EXISTS" in dir_check:
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
                if "fatal:" in result or "error:" in result.lower():
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
            
            if "NOT_FOUND" in actual_repo_check:
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
            
            return {"success": True, "output": result}
            
        except Exception as e:
            error_msg = str(e)
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
            # Create a temporary file with the token to avoid command line exposure
            await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                f'echo "{self.settings.github_token}" > /tmp/gh_token.txt',
                show_output=False
            )
            
            # Authenticate GitHub CLI using the token file
            await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                'gh auth login --with-token < /tmp/gh_token.txt',
                show_output=False
            )
            
            # Remove the temporary token file
            await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                'rm -f /tmp/gh_token.txt',
                show_output=False
            )
            
            # Configure git to use GitHub CLI for authentication
            await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                'gh auth setup-git',
                show_output=False
            )
    
    async def _create_branch(self, sandbox: Any, repo: str, branch_name: str) -> None:
        """Create and checkout new branch"""
        await self._run_git_command(sandbox, f"checkout -b {branch_name}", show_output=False)
    
    async def _execute_agent(
        self, 
        sandbox: Any, 
        repo: str,
        prompt: str
    ) -> AsyncGenerator[StreamEvent, None]:
        """Execute Claude agent and stream results"""
        
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
        
        # Stream Claude execution
        command = f'cd {self.repo_path} && claude --print "{agent_prompt}"'
        
        print(f"\nDEBUG: Executing Claude command in {self.repo_path}")
        print(f"DEBUG: Command: {command[:100]}...")
        
        async def async_execute(cmd):
            return await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                cmd,
                show_output=False
            )
        
        # Execute Claude command directly
        yield await self.sse_adapter.create_tool_event(
            "AI Message",
            message="Starting code analysis and implementation...",
            thinking=True
        )
        
        try:
            # Execute the command
            result = await async_execute(command)
            
            print(f"DEBUG: Claude execution result length: {len(result) if result else 0}")
            print(f"DEBUG: Claude output preview: {result[:200] if result else 'No output'}")
            
            # Parse the output and yield events
            if result:
                lines = result.strip().split('\n')
                for line in lines:
                    if line.strip():
                        # Try to detect different types of output
                        if line.startswith("Reading ") or line.startswith("Editing "):
                            # Tool usage
                            yield await self.sse_adapter.create_tool_event(
                                "File Operation",
                                message=line
                            )
                        elif line.startswith("$ "):
                            # Bash command
                            yield await self.sse_adapter.create_tool_event(
                                "Bash",
                                command=line[2:],
                                output=""
                            )
                        else:
                            # Regular output
                            yield await self.sse_adapter.create_tool_event(
                                "AI Message",
                                message=line
                            )
        except Exception as e:
            yield await self.sse_adapter.create_tool_event(
                "Error",
                message=f"Agent execution failed: {str(e)}"
            )
    
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
            
            # Check for changes
            status_output = await self._run_git_command(sandbox, "status --porcelain", show_output=False)
            
            if not status_output or not status_output.strip():
                return {
                    "files_changed": 0,
                    "summary": "No changes made"
                }
            
            # Count changed files
            changed_files = len([line for line in status_output.strip().split('\n') if line])
            
            # Stage all changes
            await self._run_git_command(sandbox, "add -A", show_output=False)
            
            # Generate commit message
            commit_message = f"Implement: {prompt[:60]}...\n\nGenerated by Tiny Backspace"
            
            # Commit
            await self._run_git_command(sandbox, f'commit -m "{commit_message}"', show_output=False)
            
            # Get diff summary
            diff_summary = await self._run_git_command(sandbox, "diff HEAD^ --stat", show_output=False)
            
            return {
                "files_changed": changed_files,
                "summary": diff_summary or f"Modified {changed_files} files"
            }
            
        except Exception as e:
            return {
                "files_changed": 0,
                "summary": f"Commit failed: {str(e)}"
            }
    
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
            
            # Create PR
            pr_title = f"Implement: {prompt[:60]}"
            pr_body = f"""## Summary
{prompt}

## Changes
{commit_result['summary']}

---
*Generated by [Tiny Backspace](https://github.com/tiny-backspace)*"""
            
            # GitHub CLI needs to be run from the repo directory
            print(f"\nDEBUG: Creating PR with gh CLI")
            print(f"DEBUG: Working directory: {self.repo_path}")
            print(f"DEBUG: PR title: {pr_title}")
            
            pr_output = await asyncio.to_thread(
                self.manager.execute_command,
                sandbox,
                f'''cd {self.repo_path} && gh pr create \\
                    --title "{pr_title}" \\
                    --body "{pr_body}" \\
                    --base main \\
                    --head {branch_name}''',
                show_output=False
            )
            
            print(f"DEBUG: PR creation output: {pr_output}")
            
            # Extract PR URL from output
            pr_url_match = re.search(r'https://github\.com/[^\s]+/pull/\d+', pr_output or '')
            
            if pr_url_match:
                pr_url = pr_url_match.group(0)
                print(f"\nDEBUG: PR created successfully: {pr_url}")
                return {
                    "success": True,
                    "pr_url": pr_url
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