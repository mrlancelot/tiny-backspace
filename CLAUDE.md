# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

tiny-backspace is an autonomous coding agent system that creates sandboxed environments where AI can automatically clone GitHub repositories, make code changes based on prompts, and create pull requests. It integrates Daytona for sandbox management, Claude Code CLI for AI-powered coding, and provides streaming responses with real-time progress updates.

## Common Commands

### Running the Application
```bash
# Interactive mode (recommended)
python enhanced_cli.py

# Command line mode
python daytona_manager_refactored.py create my-sandbox claude
python daytona_manager_refactored.py list
python daytona_manager_refactored.py delete <sandbox-id>
```

### Testing
```bash
# Run all tests
pytest test_daytona_manager.py -v

# Run with coverage
pytest test_daytona_manager.py --cov=. --cov-report=html
```

### Docker Development
```bash
# Quick start
./quick-start.sh

# Manual Docker commands
docker-compose up -d --build
docker-compose exec dev-environment bash
docker-compose down
```

## Architecture Overview

### Core Components

1. **DaytonaManager** (`daytona_manager.py` → `daytona_manager_cleaned.py` → `daytona_manager_refactored.py`)
   - Manages Daytona sandbox lifecycle (create, list, delete)
   - Executes commands within sandboxes
   - Integrates with Claude Code CLI

2. **StreamingResponseHandler** (`streaming_response.py`)
   - Handles real-time streaming of AI responses
   - Parses Claude output for tool usage events
   - Provides async generators for SSE implementation

3. **PermissionManager** (`permission_manager.py`)
   - Enforces security permissions for operations
   - Provides interactive prompts for user consent
   - Tracks operation history and risk levels

4. **EnhancedCLI** (`enhanced_cli.py`)
   - Rich terminal UI with interactive menus
   - Progress bars and real-time status updates
   - User-friendly interface for all operations

### Docker Infrastructure

The project includes Docker configurations for creating custom images with pre-installed tools:
- `Dockerfile`: Main container with Claude Code CLI and Gemini CLI
- `docker-compose.yml`: Orchestrates development environment with persistent volumes for authentication

### Key Design Patterns

1. **Layered Refactoring**: The codebase shows progressive enhancement from `daytona_manager.py` → `daytona_manager_cleaned.py` → `daytona_manager_refactored.py`, each adding features while maintaining backward compatibility.

2. **Async Streaming**: Uses async generators for streaming AI responses, enabling real-time progress updates through Server-Sent Events.

3. **Permission-Based Security**: All potentially dangerous operations require explicit user permission with risk assessment.

4. **Environment Isolation**: Each request operates in a fresh Daytona sandbox for complete isolation and security.

## Environment Configuration

Required environment variables (see `.env.example`):
- `DAYTONA_API_KEY`: Required for Daytona SDK
- `DAYTONA_API_URL`: Daytona API endpoint (default: https://app.daytona.io/api)
- `ANTHROPIC_API_KEY`: Optional, for Claude Code authentication
- `GEMINI_API_KEY`: Optional, for Gemini CLI

## Development Workflow

1. **Adding New Features**: Follow the refactoring pattern - extend `DaytonaManagerRefactored` rather than modifying base classes.

2. **Testing**: Always run the test suite before committing. Tests use mocking for external services.

3. **Error Handling**: The codebase emphasizes graceful error handling with user-friendly messages through Rich console.

4. **Streaming Operations**: When implementing new streaming features, use `StreamingResponseHandler` patterns for consistency.

## Key Dependencies

- `daytona`: SDK for sandbox management
- `rich`: Terminal UI enhancements
- `prompt-toolkit`: Interactive CLI prompts
- `asyncio/aiohttp`: Async operations
- `pytest`: Testing framework with async support

The project aims to provide a secure, observable infrastructure for AI-powered autonomous coding agents.