# Gemini-Daytona Autonomous Coding Agent

A complete implementation of an autonomous coding agent using Gemini CLI and Daytona sandboxes. This system automatically creates pull requests based on natural language prompts.

## Overview

This implementation provides:
- 🚀 Automated sandbox creation with Gemini CLI pre-installed
- 🤖 Natural language code generation using Gemini
- 🔀 Automatic PR creation on GitHub
- 📡 Real-time streaming of the coding process via Server-Sent Events
- 🔒 Secure, isolated execution environments

## Key Features

- ✅ **Gemini CLI Integration** - Uses Google's Gemini for code generation
- ✅ **Streaming Responses** - Real-time progress via Server-Sent Events
- ✅ **Automatic PR Creation** - Creates GitHub pull requests automatically
- ✅ **Sandbox Isolation** - Secure execution in Daytona environments
- ✅ **Easy CLI Interface** - Simple commands for all operations
- ✅ **Comprehensive Testing** - Full test suite included

## How It Works

1. **Request received** - API accepts repository URL and coding prompt
2. **Sandbox created** - Fresh Daytona environment with Gemini CLI
3. **Repository cloned** - Target repo cloned into sandbox
4. **Gemini executes** - AI analyzes code and makes changes
5. **PR created** - Changes committed and PR opened on GitHub
6. **Response streamed** - Real-time updates via Server-Sent Events

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

### Project Structure

```
tiny-backspace/
├── gemini_daytona_manager.py    # Core Daytona + Gemini manager
├── gemini_streaming.py          # Streaming response handler
├── api/
│   └── gemini_endpoint.py       # FastAPI server
├── test_gemini_implementation.py # Test suite
├── example_api_client.py        # Example API client
├── run_gemini.sh               # Easy launcher script
└── GEMINI_IMPLEMENTATION.md    # This documentation
```

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

1. **Using the run_gemini.sh Script**:
   ```bash
   # Start API server
   ./run_gemini.sh api

   # Run tests
   ./run_gemini.sh test

   # Create a sandbox
   ./run_gemini.sh create my-sandbox

   # List sandboxes
   ./run_gemini.sh list

   # Execute coding task
   ./run_gemini.sh code <sandbox-id> <repo-url> '<prompt>'

   # Run demo
   ./run_gemini.sh demo

   # Delete sandbox
   ./run_gemini.sh delete <sandbox-id>
   ```

2. **Direct CLI Usage**:
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

3. **API Usage**:
   ```bash
   # Start the API server
   ./run_gemini.sh api
   # or
   python api/gemini_endpoint.py

   # In another terminal, make a request
   curl -X POST http://localhost:8000/code \
     -H "Content-Type: application/json" \
     -d '{
       "repoUrl": "https://github.com/mrlancelot/tb-test",
       "prompt": "Add a simple README with project description"
     }'
   
   # Or use the example client
   python example_api_client.py
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

### Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /code` - Create PR from prompt (SSE response)

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

- Each request runs in an isolated Daytona sandbox
- Sandboxes have limited resources (2 CPU, 4GB RAM)
- Automatic cleanup after task completion
- API keys stored securely as environment variables
- Sandboxes are automatically cleaned up 5 minutes after task completion

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

## Notes

- The Gemini CLI npm package name might need adjustment based on the actual package
- Ensure your GitHub token has permissions to create PRs on target repositories
- For the latest updates and full API integration, see the main API at `api/agent_orchestrator.py`

## Demo

Run the included demo to see it in action:
```bash
./run_gemini.sh demo
```

This will create a sandbox and add a README to the test repository!

## License

This implementation is part of the tiny-backspace project.