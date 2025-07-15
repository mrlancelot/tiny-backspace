# Private Repository Setup Guide

This guide explains how to set up and test Tiny Backspace with private GitHub repositories.

## Prerequisites

1. **Environment Variables** - Make sure your `.env` file contains:
   ```env
   # Required for Daytona sandboxes
   DAYTONA_API_KEY=your_daytona_key
   
   # Required for Claude Code
   CLAUDE_CODE_OAUTH_TOKEN=your_claude_oauth_token
   
   # Required for GitHub operations
   GITHUB_TOKEN=your_github_pat_token
   GITHUB_USERNAME=your_github_username
   GITHUB_EMAIL=your_email@example.com
   ```

2. **GitHub Personal Access Token** - Your token needs these permissions:
   - `repo` (full control of private repositories)
   - `workflow` (optional, for GitHub Actions)

## Quick Start

### 1. Start the API Server

In one terminal window:
```bash
./run_api.sh
```

Or manually:
```bash
cd api
python main.py
```

The API will start at `http://localhost:8000`

### 2. Test with Private Repository

In another terminal:
```bash
python test_private_repo.py
```

This will:
1. Check API health
2. Send a request to create a README.md file
3. Stream the entire process
4. Create a pull request in your private repository

### 3. Monitor Progress

The test script will show:
- 🏁 Request start
- 📊 Progress updates (cloning, analyzing, coding, etc.)
- 📖 File reads
- ✏️ File edits  
- 💻 Shell commands
- 🤔 Claude's thinking process
- ✅ Pull request creation

## Manual Testing

You can also test manually using curl:

```bash
curl -X POST http://localhost:8000/api/code \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/yourusername/your-private-repo",
    "prompt": "Add a simple hello world Python script"
  }'
```

Or use the web interface by opening `api/client_example.html` in your browser.

## What Happens Behind the Scenes

1. **Authentication Setup**
   - GitHub token is validated
   - Daytona sandbox is created
   - Claude Code OAuth token is configured

2. **Repository Cloning**
   - Private repo is cloned using authenticated URL
   - Credentials are immediately removed from remote URL

3. **Code Generation**
   - Claude analyzes the repository
   - Makes the requested changes
   - Commits with descriptive message

4. **Pull Request Creation**
   - Changes are pushed to a new branch
   - PR is created via GitHub CLI
   - Link is returned in the response

## Troubleshooting

### "Authentication failed" Error
- Check your GitHub token has `repo` scope
- Verify GITHUB_USERNAME matches your actual username
- Ensure token hasn't expired

### "No changes made" Error
- The prompt may be unclear
- Claude might not understand the repository structure
- Try a more specific prompt

### "Permission denied" Error  
- Your GitHub token may lack required permissions
- The repository might have branch protection rules

### Claude Authentication Issues
- Verify CLAUDE_CODE_OAUTH_TOKEN is set correctly
- Token should start with `sk-ant-oat01-`
- Try regenerating the token if expired

## Security Notes

1. **Tokens are never logged** - All authentication tokens are hidden from output
2. **Credentials are scrubbed** - Git remotes are reset after operations
3. **Sandboxed execution** - All code runs in isolated Daytona containers
4. **Temporary storage** - Tokens are stored in memory only during execution

## Example Prompts

Simple tasks work best:
- "Create a README.md with project description"
- "Add a .gitignore file for Python projects"
- "Create a simple Flask hello world application"
- "Add type hints to all Python functions"
- "Create unit tests for the main module"

## Next Steps

1. Try different prompts with your repository
2. Monitor the created pull requests
3. Check the sandbox logs for debugging
4. Customize the agent behavior in `agent_orchestrator.py`