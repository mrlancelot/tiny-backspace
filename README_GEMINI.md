# Tiny Backspace - Gemini Implementation

An autonomous coding agent that creates pull requests automatically using **Gemini CLI** and **Daytona sandboxes**.

## 🚀 Quick Start

### 1. Setup Environment

Create a `.env` file with your API keys:
```bash
DAYTONA_API_KEY=your_daytona_api_key
GEMINI_API_KEY=your_gemini_api_key
GITHUB_TOKEN=your_github_pat
GITHUB_USERNAME=your_github_username
GITHUB_EMAIL=your_email@example.com
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the API Server

```bash
./run_gemini.sh api
# or
python api/gemini_endpoint.py
```

### 4. Make a Coding Request

Using curl:
```bash
curl -X POST http://localhost:8000/code \
  -H "Content-Type: application/json" \
  -d '{
    "repoUrl": "https://github.com/mrlancelot/tb-test",
    "prompt": "Add a README.md file with project description"
  }'
```

Using the example client:
```bash
python example_api_client.py
```

## 📁 Project Structure

```
tiny-backspace/
├── gemini_daytona_manager.py    # Core Daytona + Gemini manager
├── gemini_streaming.py          # Streaming response handler
├── api/
│   └── gemini_endpoint.py       # FastAPI server
├── test_gemini_implementation.py # Test suite
├── example_api_client.py        # Example API client
├── run_gemini.sh               # Easy launcher script
└── GEMINI_IMPLEMENTATION.md    # Detailed documentation
```

## 🛠️ CLI Commands

The `run_gemini.sh` script provides easy access to all features:

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

## 🔄 How It Works

1. **Request received** - API accepts repository URL and coding prompt
2. **Sandbox created** - Fresh Daytona environment with Gemini CLI
3. **Repository cloned** - Target repo cloned into sandbox
4. **Gemini executes** - AI analyzes code and makes changes
5. **PR created** - Changes committed and PR opened on GitHub
6. **Response streamed** - Real-time updates via Server-Sent Events

## 📡 API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /code` - Create PR from prompt (SSE response)

## 🧪 Testing

Run the comprehensive test suite:
```bash
python test_gemini_implementation.py
```

## 📊 Example Response Stream

```
data: {"type": "status", "message": "Creating Daytona sandbox..."}
data: {"type": "Tool: Git", "message": "Cloning repository..."}
data: {"type": "AI Message", "message": "Analyzing codebase..."}
data: {"type": "Tool: Write", "content": "README.md"}
data: {"type": "Tool: Git", "message": "Creating pull request..."}
data: {"type": "complete", "pr_url": "https://github.com/user/repo/pull/123"}
```

## 🔒 Security

- Each request runs in an isolated Daytona sandbox
- Sandboxes have limited resources (2 CPU, 4GB RAM)
- Automatic cleanup after task completion
- API keys stored securely as environment variables

## 🎯 Key Features

- ✅ **Gemini CLI Integration** - Uses Google's Gemini for code generation
- ✅ **Streaming Responses** - Real-time progress via Server-Sent Events
- ✅ **Automatic PR Creation** - Creates GitHub pull requests automatically
- ✅ **Sandbox Isolation** - Secure execution in Daytona environments
- ✅ **Easy CLI Interface** - Simple commands for all operations
- ✅ **Comprehensive Testing** - Full test suite included

## 📝 Notes

- The Gemini CLI npm package name might need adjustment based on the actual package
- Ensure your GitHub token has permissions to create PRs on target repositories
- Sandboxes are automatically cleaned up 5 minutes after task completion

## 🚀 Demo

Run the included demo to see it in action:
```bash
./run_gemini.sh demo
```

This will create a sandbox and add a README to the test repository!