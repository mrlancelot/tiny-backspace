# Tiny Backspace - Autonomous Coding Agent Implementation Plan

## Project Overview

Building a sandboxed coding agent that automatically creates pull requests based on GitHub repository URLs and coding prompts. This explores the core technology behind autonomous coding agents using modern tooling for safety and observability.

### Take-Home Test Requirements

**Input:**
- `repoUrl`: Public GitHub repository URL (e.g., https://github.com/daytonaio/daytona)
- `prompt`: Textual command describing code changes (e.g., "Add input validation to POST endpoints")

**Output:**
- Streaming API via Server-Sent Events
- Real-time updates of the coding process
- Automated pull request creation
- Summary of changes made

**Example Workflow:**
```
POST /api/code
{
  "repoUrl": "https://github.com/example/simple-api",
  "prompt": "Add input validation to all POST endpoints and return proper error messages"
}
```

**Expected Stream Output:**
```
data: {"type": "Tool: Read", "filepath": "app.py"}
data: {"type": "AI Message", "message": "Found 3 POST endpoints: /users, /posts, /comments. Need to add Pydantic for validation."}
data: {"type": "Tool: Edit", "filepath": "models.py", "changes": "Added Pydantic models"}
data: {"type": "Tool: Bash", "command": "git checkout -b feature/add-input-validation"}
data: {"type": "Tool: Bash", "command": "gh pr create --title 'Add input validation'", "output": "https://github.com/example/simple-api/pull/123"}
```

## Research Summary

### Sandbox Providers Analysis

#### 1. Daytona (Recommended Choice)
**Strengths:**
- Sub-90ms sandbox creation time
- Custom Docker image support with pre-installed tools
- Native Git operations and file system APIs
- Python & TypeScript SDKs for programmatic control
- Unlimited persistence during workflow
- OCI/Docker compatibility
- Built-in security isolation

**API Example:**
```python
from daytona import Daytona, DaytonaConfig, CreateSandboxParams

daytona = Daytona(DaytonaConfig(api_key="YOUR_API_KEY"))
sandbox = daytona.create(CreateSandboxParams(
    image="custom-claude-code:latest"
))
response = sandbox.process.code_run('git clone repo && claude-code --prompt "..."')
```

**Custom Image Capabilities:**
- Pre-install Claude Code CLI
- Configure Git and GitHub CLI
- Add common development tools
- Set up environment variables

#### 2. E2B
**Strengths:**
- 150ms startup time
- Desktop sandbox environments
- Good documentation
- Python/JavaScript SDKs

**Limitations:**
- Less mature than Daytona
- Limited custom image examples

#### 3. Modal
**Strengths:**
- Excellent for Python workloads
- Good documentation
- Fast execution

**Limitations:**
- Primarily Python-focused
- Less flexibility for custom environments

### Streaming API Options

#### Next.js with Server-Sent Events (Recommended)
**Advantages:**
- Modern framework with TypeScript support
- Built-in API routes
- Good SSE support with proper configuration
- Easy deployment to Vercel/similar platforms

**Implementation Considerations:**
- Requires proper headers to avoid buffering
- Need to handle client disconnection
- Cache-Control: "no-cache, no-transform" required

#### FastAPI with SSE
**Advantages:**
- Excellent Python ecosystem integration
- Built-in SSE support with EventSourceResponse
- Strong typing with Pydantic

**Considerations:**
- Python deployment complexity
- Less integrated frontend development

### AI Agent Integration

#### Claude Code CLI (Recommended)
**Strengths:**
- Purpose-built for autonomous coding
- Excellent tool usage (Read, Edit, Bash, Git)
- Streaming output capabilities
- High-quality code generation

**Integration Strategy:**
- Pre-install in custom Docker image
- Execute via subprocess in sandbox
- Parse output for tool usage events
- Stream agent thinking process

## Proposed Architecture

### High-Level System Design

```
User Request → Next.js API → Daytona Sandbox → Claude Code → Git Operations → PR Creation
     ↓              ↓              ↓              ↓              ↓              ↓
   Input         Stream         Custom        AI Agent       GitHub         Output
Validation      Events         Image         Execution        API          Stream
```

### Core Components

#### 1. Streaming API Endpoint (`/api/code`)
- **Framework:** Next.js 14+ with App Router
- **Method:** POST with SSE response
- **Validation:** Repository URL and prompt sanitization
- **Error Handling:** Graceful degradation and cleanup

#### 2. Custom Daytona Image
**Base Configuration:**
```dockerfile
FROM ubuntu:22.04

# System dependencies
RUN apt-get update && apt-get install -y \
    curl wget git nodejs npm python3 pip \
    build-essential

# Claude Code CLI
RUN curl -fsSL https://claude.ai/install.sh | sh

# GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
RUN echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null
RUN apt-get update && apt-get install -y gh

# Git configuration
RUN git config --global user.name "Backspace Agent"
RUN git config --global user.email "agent@backspace.run"

# Development tools
RUN npm install -g typescript @types/node
RUN pip3 install fastapi uvicorn pytest

WORKDIR /workspace
```

#### 3. Sandbox Manager
**Responsibilities:**
- Create fresh Daytona sandbox per request
- Clone repository into sandbox environment
- Execute Claude Code with streaming output
- Handle sandbox lifecycle and cleanup

#### 4. Event Stream Manager
**Event Types:**
```typescript
interface StreamEvent {
  type: 'sandbox_creating' | 'repo_cloning' | 'agent_thinking' | 
        'tool_read' | 'tool_edit' | 'tool_bash' | 'git_operation' | 
        'pr_created' | 'complete' | 'error'
  timestamp: string
  data: {
    message?: string
    file?: string
    command?: string
    output?: string
    prUrl?: string
    error?: string
  }
}
```

#### 5. Git Operations Handler
- Create feature branches
- Stage and commit changes
- Push to remote repository
- Create pull requests via GitHub CLI

## Implementation Roadmap

### Phase 1: Foundation (Days 1-2)

#### Day 1: Project Setup & Custom Image
1. **Initialize Next.js Project**
   ```bash
   npx create-next-app@latest tiny-backspace --typescript --app
   cd tiny-backspace
   npm install @daytonaio/sdk
   ```

2. **Create Custom Docker Image**
   - Build Dockerfile with Claude Code and tools
   - Test image locally with basic operations
   - Push to Daytona using `daytona image push`

3. **Basic API Endpoint Structure**
   - Set up `/api/code` route with SSE headers
   - Implement request validation
   - Add basic event streaming

#### Day 2: Daytona Integration
1. **Sandbox Management**
   - Implement Daytona SDK wrapper
   - Create sandbox with custom image
   - Test repository cloning

2. **Event Streaming Infrastructure**
   - Design event format and types
   - Implement streaming utilities
   - Add client disconnection handling

### Phase 2: AI Agent Integration (Days 2-3)

#### Day 2-3: Claude Code Execution
1. **Claude Code Wrapper**
   - Execute Claude Code within sandbox
   - Parse tool usage from output
   - Stream agent thinking process

2. **Tool Usage Parsing**
   - Read operations → file content events
   - Edit operations → file change events
   - Bash operations → command execution events

3. **Error Handling & Recovery**
   - Handle Claude Code failures
   - Implement retry mechanisms
   - Graceful error reporting

### Phase 3: Git Operations & PR Creation (Day 3-4)

#### Day 3: Git Integration
1. **Branch Management**
   - Create feature branches with timestamps
   - Handle branch conflicts
   - Commit changes with descriptive messages

2. **GitHub API Integration**
   - Authenticate with GitHub tokens
   - Create pull requests programmatically
   - Handle rate limiting

#### Day 4: Security & Observability
1. **Security Measures**
   - Input sanitization and validation
   - Sandbox resource limits
   - Secure token management

2. **OpenTelemetry Integration**
   - Add distributed tracing
   - Instrument key operations
   - Set up logging pipeline

### Phase 4: Testing & Polish (Day 4-5)

#### Day 4-5: Testing & Documentation
1. **Testing Strategy**
   - Unit tests for core functions
   - Integration tests with mock repositories
   - End-to-end workflow tests

2. **Demo Interface**
   - Simple React dashboard
   - Real-time event display
   - Progress indicators

3. **Documentation**
   - Comprehensive README
   - API documentation
   - Deployment instructions

### Phase 5: Deployment (Day 5)

1. **Production Deployment**
   - Deploy to Vercel/Railway
   - Configure environment variables
   - Set up monitoring

2. **Performance Optimization**
   - Optimize sandbox creation time
   - Implement connection pooling
   - Add caching where appropriate

## Security Considerations

### Sandbox Security
- **Complete Isolation:** Each request gets fresh Daytona sandbox
- **Resource Limits:** CPU, memory, and execution time constraints
- **Network Restrictions:** Limited external access except GitHub API
- **Automatic Cleanup:** Sandbox destruction after completion

### Input Validation
- **Repository URL Validation:** Whitelist GitHub domains
- **Prompt Sanitization:** Remove potentially harmful commands
- **Rate Limiting:** Prevent abuse with per-IP limits
- **Authentication:** Secure GitHub token handling

### Code Execution Safety
- **Sandboxed Environment:** All code runs in isolated containers
- **No Host Access:** Sandbox cannot affect host system
- **Audit Logging:** Complete trail of all operations
- **Token Security:** Environment variables, no exposure in logs

## Observability Strategy

### Real-Time Monitoring
- **OpenTelemetry Tracing:** End-to-end request tracing
- **Structured Logging:** JSON logs with correlation IDs
- **Performance Metrics:** Sandbox creation time, execution duration
- **Error Tracking:** Comprehensive error reporting

### Event Streaming
- **Progress Updates:** Real-time workflow status
- **Agent Thinking:** Stream Claude's reasoning process
- **Tool Usage:** Detailed logging of file operations
- **Git Operations:** Track all repository changes

## Alternative Approaches Considered

### 1. FastAPI + E2B
**Pros:** Python ecosystem, faster E2B startup
**Cons:** Deployment complexity, less integrated frontend

### 2. Next.js + Modal
**Pros:** Excellent Python support, good documentation
**Cons:** Limited custom environment flexibility

### 3. Container Orchestration (Docker + Kubernetes)
**Pros:** Full control over environment
**Cons:** Complex setup, slower startup times

### 4. Firecracker VMs
**Pros:** Ultra-fast startup, complete isolation
**Cons:** Complex implementation, limited tooling

## Risk Assessment & Mitigation

### Technical Risks

#### Daytona API Limits
**Risk:** Quota exhaustion or rate limiting
**Mitigation:** 
- Implement queuing system
- Monitor usage metrics
- Graceful degradation

#### Claude Code Integration
**Risk:** Parsing failures or unexpected output
**Mitigation:**
- Robust output parsing
- Fallback mechanisms
- Comprehensive testing

#### GitHub API Limits
**Risk:** Rate limiting on PR creation
**Mitigation:**
- Respect rate limits
- Use proper authentication
- Implement exponential backoff

### Security Risks

#### Code Injection
**Risk:** Malicious code execution
**Mitigation:**
- Sandbox isolation
- Input validation
- Resource limits

#### Token Exposure
**Risk:** GitHub tokens in logs/responses
**Mitigation:**
- Environment variables
- Secure logging practices
- Token rotation

## Success Metrics

### Functional Requirements
- ✅ Successfully clone any public GitHub repository
- ✅ Generate appropriate code changes based on prompts
- ✅ Create pull requests automatically
- ✅ Stream real-time progress updates
- ✅ Handle errors gracefully with cleanup

### Performance Requirements
- **Sandbox Creation:** < 5 seconds including image pull
- **Total Execution:** < 60 seconds for typical changes
- **Streaming Latency:** < 1 second for event updates
- **Concurrent Requests:** Handle 10+ simultaneous workflows

### Quality Requirements
- **Error Rate:** < 5% for valid inputs
- **Security:** Complete sandbox isolation
- **Observability:** Full tracing and logging
- **Maintainability:** Clean, documented codebase

## Next Research Areas

### 1. Claude Code API Integration
- Investigate Claude Code streaming capabilities
- Test output parsing with various prompts
- Explore error handling mechanisms

### 2. Daytona Advanced Features
- Custom image optimization strategies
- Workspace persistence options
- Performance tuning parameters

### 3. GitHub Integration
- PR template customization
- Advanced Git operations
- Repository permission handling

### 4. Scaling Considerations
- Multi-instance deployment
- Load balancing strategies
- Cost optimization approaches

## Development Environment Setup

### Prerequisites
```bash
# Required accounts and tokens
- Daytona account + API key
- Anthropic API key for Claude
- GitHub personal access token
- Node.js 18+ and Docker installed
```

### Local Development
```bash
# Initial setup
git clone <repo>
cd tiny-backspace
npm install

# Environment variables
cp .env.example .env.local
# Add API keys to .env.local

# Development server
npm run dev
```

### Testing Strategy
```bash
# Unit tests
npm run test

# Integration tests with test repositories
npm run test:integration

# E2E tests with Playwright
npm run test:e2e
```

This comprehensive plan provides the foundation for building a production-quality autonomous coding agent that leverages modern infrastructure for safety, performance, and observability.