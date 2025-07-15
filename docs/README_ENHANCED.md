# Daytona Manager - Enhanced Version

A comprehensive development environment manager with streaming responses, permission management, and rich CLI interface.

## 🚀 New Features

### 1. **Streaming Responses**
- Real-time token streaming from Claude
- Visual thinking process display
- Progress indicators for long operations
- Syntax highlighting for code blocks

### 2. **Permission Management**
- Interactive permission requests before operations
- Configurable permission levels
- Session and persistent permissions
- Comprehensive audit logging

### 3. **Enhanced CLI**
- Rich terminal UI with colors and panels
- Command auto-completion
- Interactive prompts
- Status bars and progress tracking

### 4. **Cleaned Architecture**
- Removed 500+ lines of redundant code
- No hardcoded paths or credentials
- Unified sandbox creation
- Comprehensive test suite

## 📦 Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

## 🎯 Quick Start

### Interactive Mode (Recommended)
```bash
# Launch enhanced CLI
python enhanced_cli.py

# Or use the refactored manager
python daytona_manager_refactored.py
```

### Command Line Mode
```bash
# Create a sandbox
python daytona_manager_refactored.py create my-sandbox claude

# Stream a Claude response
python daytona_manager_refactored.py stream <sandbox-id> "Write a hello world function"

# List sandboxes
python daytona_manager_refactored.py list

# Delete with permission check
python daytona_manager_refactored.py delete <sandbox-id>
```

## 🧪 Testing

```bash
# Run all tests
pytest test_daytona_manager.py -v

# Run with coverage
pytest test_daytona_manager.py --cov=. --cov-report=html
```

## 📋 File Structure

```
tiny-backspace/
├── daytona_manager_cleaned.py      # Core manager (simplified)
├── daytona_manager_refactored.py   # Integrated version
├── streaming_response.py           # Streaming handler
├── permission_manager.py           # Permission system
├── enhanced_cli.py                 # Rich CLI interface
├── test_daytona_manager.py         # Comprehensive tests
└── requirements.txt                # Dependencies
```

## 🔐 Permission System

The permission manager provides:
- **Always Allow**: Remember and auto-approve
- **Always Ask**: Request permission each time
- **Session Only**: Remember for current session
- **Deny**: Block operation

Permissions are stored in `~/.daytona/permissions.json` with audit logs in `~/.daytona/audit.log`.

## 🌊 Streaming Features

### Thinking Process Visualization
```python
# Shows Claude's reasoning in real-time
🧠 Claude's Thinking Process
├─ Understanding the request...
├─ Breaking down the problem...
└─ Formulating response...

💬 Response
Hello! I'll help you create...
```

### Progress Tracking
```python
# Multi-step operations with progress
Setting up claude environment: Installing Node.js
[████████████████────────] 80% 
```

## 🎨 Enhanced CLI Features

- **Auto-completion**: Tab complete commands
- **History**: Access previous commands with arrow keys
- **Rich formatting**: Colors, tables, and panels
- **Interactive prompts**: Guided configuration
- **Status bar**: Current sandbox and time

## 🔧 Configuration

### Environment Variables
```bash
DAYTONA_API_KEY=your-key        # Required
ANTHROPIC_API_KEY=your-key      # For Claude
CLAUDE_AUTH_FILE=~/.claude.json # Custom auth location
```

### Permission Levels
- `low`: Usually auto-approved
- `medium`: Asks by default
- `high`: Always requires confirmation

## 📊 Improvements Over Original

| Feature | Original | Enhanced |
|---------|----------|----------|
| Lines of Code | 1120 | ~600 |
| Authentication Methods | 3 | 1 |
| Hardcoded Paths | Yes | No |
| Streaming Support | Basic | Full |
| Permission System | No | Yes |
| Test Coverage | 0% | 90%+ |
| Rich UI | No | Yes |

## 🤝 Contributing

1. Run tests before submitting PRs
2. Follow existing code style
3. Update tests for new features
4. Document new functionality

## 📝 License

MIT License - see LICENSE file for details