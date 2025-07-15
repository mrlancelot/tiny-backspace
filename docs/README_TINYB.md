# Tiny Backspace API

An autonomous coding agent service that creates pull requests from natural language prompts. Built with FastAPI, Daytona sandboxes, and Claude Code.

## Features

- 🚀 **Streaming API** - Real-time progress updates via Server-Sent Events (SSE)
- 🔒 **Secure Sandboxing** - Each request runs in isolated Daytona environment
- 🤖 **Claude Integration** - Powered by Claude Code for intelligent code changes
- 🔄 **Automatic PR Creation** - Creates branches, commits, and pull requests
- 📊 **Observable** - Built-in logging and optional OpenTelemetry support

## Quick Start

### Prerequisites

- Python 3.8+
- Daytona API access
- GitHub account with personal access token
- (Optional) Anthropic API key for Claude

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/tiny-backspace.git
cd tiny-backspace
```

2. Install dependencies:
```bash
pip install -r api/requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials:
# - DAYTONA_API_KEY
# - GITHUB_TOKEN (for PR creation)
# - ANTHROPIC_API_KEY (optional)
```

### Running Locally

1. Start the API server:
```bash
cd api
python main.py
```

The API will be available at `http://localhost:8000`

2. Test the health endpoint:
```bash
curl http://localhost:8000/health
```

### API Usage

Make a POST request to create a PR:

```bash
curl -X POST http://localhost:8000/api/code \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/yourusername/test-repo",
    "prompt": "Add a hello world endpoint to the Flask app"
  }'
```

The response will be a stream of Server-Sent Events showing progress:

```
data: {"type": "start", "request_id": "abc123", "timestamp": "2024-01-01T00:00:00Z"}
data: {"type": "progress", "stage": "cloning", "message": "Creating sandbox", "percentage": 10}
data: {"type": "Tool: Bash", "command": "git clone https://github.com/...", "output": "..."}
data: {"type": "AI Message", "message": "Analyzing the Flask application structure..."}
data: {"type": "Tool: Edit", "filepath": "app.py", "old_str": "...", "new_str": "..."}
data: {"type": "pr_created", "pr_url": "https://github.com/.../pull/123", "files_changed": 2}
data: {"type": "complete", "request_id": "abc123", "timestamp": "2024-01-01T00:01:00Z"}
```

### JavaScript Client Example

```javascript
const eventSource = new EventSource('http://localhost:8000/api/code', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    repo_url: 'https://github.com/example/repo',
    prompt: 'Add input validation to the API'
  })
});

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`${data.type}: ${JSON.stringify(data)}`);
  
  if (data.type === 'pr_created') {
    console.log(`Pull Request created: ${data.pr_url}`);
  }
};

eventSource.onerror = (error) => {
  console.error('Stream error:', error);
  eventSource.close();
};
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   Client    │────▶│  FastAPI    │────▶│   Daytona    │
│   (SSE)     │◀────│   Server    │◀────│   Sandbox    │
└─────────────┘     └─────────────┘     └──────────────┘
                           │                     │
                           │                     ▼
                    ┌──────▼──────┐      ┌──────────────┐
                    │   GitHub    │◀─────│ Claude Code  │
                    │     API     │      │    Agent     │
                    └─────────────┘      └──────────────┘
```

### Key Components

1. **API Layer** (`main.py`)
   - FastAPI application with SSE endpoint
   - Request validation and authentication
   - Streaming response handling

2. **SSE Adapter** (`sse_adapter.py`)
   - Converts internal events to SSE format
   - Maps agent actions to stream events
   - Handles error formatting

3. **Agent Orchestrator** (`agent_orchestrator.py`)
   - Manages complete workflow
   - Sandbox lifecycle management
   - Git operations and PR creation

4. **Integration Layer**
   - Reuses existing `DaytonaManager` for sandboxes
   - Leverages `StreamingResponseHandler` for Claude
   - Maintains security with `PermissionManager`

## Configuration

Key environment variables:

- `DAYTONA_API_KEY` - Required for sandbox creation
- `GITHUB_TOKEN` - Required for PR creation
- `GITHUB_USERNAME` - Git commit author
- `GITHUB_EMAIL` - Git commit email
- `ANTHROPIC_API_KEY` - Optional, for Claude authentication
- `REQUIRE_AUTH` - Enable API key authentication
- `API_KEY` - API key for authentication
- `MAX_SANDBOX_DURATION` - Timeout for sandbox operations (default: 600s)

## Security Considerations

1. **Sandboxing** - All code execution happens in isolated Daytona containers
2. **Input Validation** - Repository URLs and prompts are validated
3. **Authentication** - Optional API key authentication
4. **Rate Limiting** - Configurable request limits
5. **Resource Limits** - CPU, memory, and timeout constraints

## Development

### Running Tests

```bash
pytest api/tests -v
```

### Adding New Features

1. Extend `StreamEventType` in `models.py` for new event types
2. Update `SSEAdapter` to handle new event conversions
3. Modify `AgentOrchestrator` to emit new events
4. Update client examples to handle new events

## Deployment

### Using Docker

```bash
docker build -t tiny-backspace-api .
docker run -p 8000:8000 --env-file .env tiny-backspace-api
```

### Production Considerations

1. Use a production ASGI server (Gunicorn with Uvicorn workers)
2. Set up proper logging and monitoring
3. Configure rate limiting and authentication
4. Use environment-specific configurations
5. Set up health checks and auto-scaling

## Troubleshooting

### Common Issues

1. **Sandbox creation fails**
   - Check Daytona API key and connectivity
   - Verify resource limits aren't exceeded

2. **PR creation fails**
   - Ensure GitHub token has appropriate permissions
   - Verify repository exists and is public

3. **Agent doesn't make changes**
   - Check Claude authentication
   - Review prompt clarity and specificity

### Debug Mode

Enable debug logging:
```bash
DEBUG=true python main.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes with tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details