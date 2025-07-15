# Tiny Backspace

An autonomous coding agent that creates pull requests from natural language prompts. Built with FastAPI, Daytona sandboxes, and support for multiple AI agents (Claude Code and Gemini CLI).

## 🚀 Features

- **Streaming API** - Real-time progress updates via Server-Sent Events (SSE)
- **Secure Sandboxing** - Each request runs in isolated Daytona environments
- **Multiple AI Agents** - Support for Claude Code and Gemini CLI
- **Automatic PR Creation** - Creates branches, commits, and pull requests on GitHub
- **Observable** - Comprehensive logging and optional OpenTelemetry support
- **Easy CLI Interface** - Simple commands for all operations

## 📋 Prerequisites

- Python 3.8+
- Daytona API access
- GitHub account with personal access token
- API keys for your chosen AI agent:
  - For Claude: Anthropic API key or Claude Code OAuth token
  - For Gemini: Google Gemini API key

## 🔧 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/tiny-backspace.git
cd tiny-backspace
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
# Required
DAYTONA_API_KEY=your_daytona_api_key
GITHUB_TOKEN=your_github_pat
GITHUB_USERNAME=your_github_username
GITHUB_EMAIL=your_email@example.com

# Choose your AI agent (at least one required)
ANTHROPIC_API_KEY=your_anthropic_api_key  # For Claude
CLAUDE_CODE_OAUTH_TOKEN=your_oauth_token  # Alternative Claude auth
GEMINI_API_KEY=your_gemini_api_key       # For Gemini

# Optional
AGENT_TYPE=claude  # or 'gemini' (default: claude)
```

## 🏃 Quick Start

### Using the API

1. Start the API server:
```bash
./run_api.sh
# or
python api/main.py
```

2. Make a request to create a PR:
```bash
curl -X POST http://localhost:8000/api/code \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/yourusername/test-repo",
    "prompt": "Add a README file with project description"
  }'
```

### Using Docker

```bash
# Quick start with Docker
./quick-start.sh

# Or manually
docker-compose up -d --build
```

## 📡 API Reference

### Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /api/code` - Create PR from prompt (SSE response)

### POST /api/code

**Request:**
```json
{
  "repo_url": "https://github.com/user/repo",
  "prompt": "Your coding instruction here"
}
```

**Response:** Server-Sent Events stream with real-time updates

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   Client    │────▶│  FastAPI    │────▶│   Daytona    │
│   (SSE)     │◀────│   Server    │◀────│   Sandbox    │
└─────────────┘     └─────────────┘     └──────────────┘
                           │                     │
                           │                     ▼
                    ┌──────▼──────┐      ┌──────────────┐
                    │   GitHub    │◀─────│  AI Agent    │
                    │     API     │      │(Claude/Gemini)│
                    └─────────────┘      └──────────────┘
```

## 📂 Project Structure

```
tiny-backspace/
├── api/
│   ├── main.py                # FastAPI application
│   ├── agent_orchestrator.py  # Core orchestration logic
│   ├── models.py              # Data models
│   ├── config.py              # Configuration
│   └── sse_adapter.py         # SSE formatting
├── daytona_manager_refactored.py  # Daytona integration
├── docs/                      # Documentation
├── docker/                    # Docker configurations
└── CLAUDE.md                  # Instructions for Claude Code
```

## 🤖 AI Agent Support

### Claude Code (Default)
- Uses Anthropic's Claude for intelligent code generation
- Supports OAuth token or API key authentication
- See [CLAUDE.md](CLAUDE.md) for Claude-specific instructions

### Gemini CLI
- Uses Google's Gemini for code generation
- Requires Node.js 18+ in sandboxes
- See [GEMINI_IMPLEMENTATION.md](GEMINI_IMPLEMENTATION.md) for details

## 🔒 Security

- Each request runs in an isolated Daytona sandbox
- Sandboxes have limited resources (CPU, memory)
- Automatic cleanup after task completion
- API keys stored securely as environment variables
- Optional API authentication for production use

## 🧪 Testing

Run the test suite:
```bash
# API tests
python api/test_api.py

# Test with example client
python example_api_client.py
```

## 📚 Documentation

- [Project Specification](docs/tinyb.md) - Original project requirements
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) - Production deployment
- [Private Repo Setup](docs/PRIVATE_REPO_SETUP.md) - Working with private repositories
- [Windows Docker Guide](WINDOWS_DOCKER_GUIDE.md) - Windows-specific setup
- [API Documentation](docs/README_TINYB.md) - Detailed API documentation

## 🛠️ Development

### Adding New Features

1. Extend `StreamEventType` in `models.py` for new event types
2. Update `SSEAdapter` to handle new event conversions
3. Modify `AgentOrchestrator` to emit new events
4. Update client examples to handle new events

### Debug Mode

Enable debug logging:
```bash
DEBUG=true python api/main.py
```

## 🚨 Troubleshooting

### Common Issues

1. **Sandbox creation fails**
   - Check Daytona API key and connectivity
   - Verify resource quotas aren't exceeded

2. **PR creation fails**
   - Ensure GitHub token has appropriate permissions
   - Verify repository exists and is accessible

3. **AI agent errors**
   - Check API keys are correctly set
   - Verify agent-specific requirements (e.g., Node.js for Gemini)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details