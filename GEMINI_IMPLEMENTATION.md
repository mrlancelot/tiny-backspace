# Gemini-Daytona Autonomous Coding Agent

A complete implementation of an autonomous coding agent using Gemini CLI and Daytona sandboxes. This system automatically creates pull requests based on natural language prompts.

## Overview

This implementation provides:
- 🚀 Automated sandbox creation with Gemini CLI pre-installed
- 🤖 Natural language code generation using Gemini
- 🔀 Automatic PR creation on GitHub
- 📡 Real-time streaming of the coding process via Server-Sent Events
- 🔒 Secure, isolated execution environments

## Architecture

### Core Components

1. **`gemini_daytona_manager.py`** - Main manager class
   - Handles Daytona sandbox lifecycle
   - Installs and configures Gemini CLI
   - Executes coding tasks and creates PRs

2. **`gemini_streaming.py`** - Streaming response handler
   - Parses Gemini output for tool usage
   - Formats responses as Server-Sent Events
   - Provides real-time progress updates

3. **`api/gemini_endpoint.py`** - FastAPI endpoint
   - POST `/code` endpoint for coding requests
   - Streams the entire process via SSE
   - Automatic sandbox cleanup

## Setup

### Prerequisites

1. **Environment Variables** (in `.env`):
   ```bash
   DAYTONA_API_KEY=your_daytona_api_key
   GEMINI_API_KEY=your_gemini_api_key
   GITHUB_TOKEN=your_github_pat
   GITHUB_USERNAME=your_github_username
   GITHUB_EMAIL=your_email@example.com
   ```

2. **Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Quick Start

1. **CLI Usage**:
   ```bash
   # Create a Gemini sandbox
   python gemini_daytona_manager.py create my-sandbox

   # List sandboxes
   python gemini_daytona_manager.py list

   # Execute coding task
   python gemini_daytona_manager.py code <sandbox-id> https://github.com/user/repo "Add authentication"

   # Delete sandbox
   python gemini_daytona_manager.py delete <sandbox-id>
   ```

2. **API Usage**:
   ```bash
   # Start the API server
   python api/gemini_endpoint.py

   # In another terminal, make a request
   curl -X POST http://localhost:8000/code \
     -H "Content-Type: application/json" \
     -d '{
       "repoUrl": "https://github.com/mrlancelot/tb-test",
       "prompt": "Add a simple README with project description"
     }'
   ```

## Testing

Run the comprehensive test suite:

```bash
python test_gemini_implementation.py
```

This will:
- ✅ Verify environment setup
- ✅ Test sandbox creation
- ✅ Test Gemini CLI installation
- ✅ Test repository cloning
- ✅ Test API endpoint (optional)

## API Reference

### POST /code

Creates a pull request based on the provided repository and prompt.

**Request Body:**
```json
{
  "repoUrl": "https://github.com/user/repo",
  "prompt": "Your coding instruction here"
}
```

**Response:** Server-Sent Events stream with real-time updates

**Event Types:**
- `status` - General status updates
- `Tool: Git` - Git operations (clone, commit, push)
- `Tool: Read/Write/Edit` - File operations
- `AI Message` - Gemini's analysis and responses
- `complete` - Task completion with PR URL
- `error` - Error messages

## Example Output

```
data: {"type": "status", "message": "Creating Daytona sandbox..."}
data: {"type": "Tool: Git", "message": "Cloning repository: https://github.com/user/repo"}
data: {"type": "AI Message", "message": "Analyzing request: Add authentication"}
data: {"type": "Tool: Read", "content": "src/main.py"}
data: {"type": "Tool: Write", "content": "src/auth.py"}
data: {"type": "Tool: Git", "message": "Creating pull request..."}
data: {"type": "complete", "message": "Task completed successfully", "pr_url": "https://github.com/user/repo/pull/123"}
```

## Security Considerations

- Sandboxes are isolated environments with limited resources
- Each request runs in a fresh sandbox
- Sandboxes are automatically cleaned up after use
- API keys are injected securely as environment variables

## Troubleshooting

### Common Issues

1. **Gemini CLI not found**
   - Ensure `@google/generative-ai-cli` npm package name is correct
   - Check if Node.js 20 is properly installed in sandbox

2. **Authentication failures**
   - Verify GEMINI_API_KEY is set correctly
   - Check GitHub token has necessary permissions for PR creation

3. **Sandbox creation fails**
   - Verify DAYTONA_API_KEY is valid
   - Check Daytona API endpoint is accessible

### Debug Mode

Set `DEBUG=true` in your `.env` file for verbose logging.

## Future Enhancements

- [ ] Add support for private repositories
- [ ] Implement caching for faster sandbox creation
- [ ] Add webhook support for PR status updates
- [ ] Support for multiple coding agents (Claude, Gemini, etc.)
- [ ] Advanced telemetry and observability

## License

This implementation is part of the tiny-backspace project.