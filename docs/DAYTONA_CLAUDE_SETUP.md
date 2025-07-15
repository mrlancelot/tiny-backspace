# Daytona + Claude Code Configuration Guide

## Overview

This document provides comprehensive strategies for preconfiguring Daytona sandboxes with Claude Code instances for autonomous coding agent workflows. Multiple approaches are covered to suit different use cases and requirements.

## Table of Contents

1. [Configuration Approaches](#configuration-approaches)
2. [Custom Docker Image (Recommended)](#custom-docker-image-recommended)
3. [Dev Container Configuration](#dev-container-configuration)
4. [Project Configuration Method](#project-configuration-method)
5. [Runtime Installation](#runtime-installation)
6. [Hybrid Approach Strategy](#hybrid-approach-strategy)
7. [Environment Variable Management](#environment-variable-management)
8. [Testing and Validation](#testing-and-validation)
9. [Troubleshooting](#troubleshooting)

## Configuration Approaches

### Comparison Matrix

| Approach | Startup Time | Flexibility | Maintenance | Best For |
|----------|-------------|-------------|-------------|----------|
| Custom Docker Image | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | Production, Speed |
| Dev Container | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Development, Teams |
| Project Config | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Organization-wide |
| Runtime Install | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Dynamic, Testing |

## Custom Docker Image (Recommended)

### Benefits
- **Fastest startup**: Sub-90ms sandbox creation
- **Pre-installed tools**: Claude Code ready immediately
- **Consistent environment**: Same setup across all instances
- **Production ready**: Optimized for automated workflows

### Complete Dockerfile

```dockerfile
# Use Daytona's base workspace image
FROM daytonaio/workspace-project:latest

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV NODE_VERSION=20

# Update system packages
RUN sudo apt-get update && sudo apt-get upgrade -y

# Install Node.js (required for Claude Code)
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | sudo -E bash -
RUN sudo apt-get install -y nodejs

# Install additional system dependencies
RUN sudo apt-get install -y \
    python3-pip \
    python3-venv \
    build-essential \
    curl \
    wget \
    jq \
    tree \
    htop

# Install GitHub CLI for PR operations
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | \
    sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | \
    sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    sudo apt-get update && \
    sudo apt-get install -y gh

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Create Claude configuration directory
RUN mkdir -p ~/.claude

# Set up Claude Code configuration
COPY claude-settings.json ~/.claude/settings.json
COPY api-key-helper.sh ~/.claude/get_api_key.sh
RUN chmod +x ~/.claude/get_api_key.sh

# Configure Git for automated commits
RUN git config --global user.name "Backspace Agent" && \
    git config --global user.email "agent@backspace.run" && \
    git config --global init.defaultBranch main && \
    git config --global pull.rebase false

# Install common development tools
RUN npm install -g \
    typescript \
    @types/node \
    jest \
    prettier \
    eslint

# Install Python packages
RUN pip3 install \
    fastapi \
    uvicorn \
    pytest \
    requests \
    pydantic \
    black \
    flake8

# Set up Claude Code environment variables
ENV CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=true
ENV CLAUDE_CODE_ENABLE_TELEMETRY=0
ENV BASH_DEFAULT_TIMEOUT_MS=300000
ENV MCP_TIMEOUT=60000

# Create workspace directory
WORKDIR /workspace

# Clean up
RUN sudo apt-get autoremove -y && \
    sudo apt-get clean && \
    sudo rm -rf /var/lib/apt/lists/*

# Set proper permissions
RUN sudo chown -R daytona:daytona /home/daytona/.claude

# Verify installations
RUN node --version && \
    npm --version && \
    claude --version && \
    gh --version && \
    python3 --version && \
    git --version
```

### Claude Settings Configuration

```json
// claude-settings.json
{
  "env": {
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "true",
    "CLAUDE_CODE_ENABLE_TELEMETRY": "0",
    "BASH_DEFAULT_TIMEOUT_MS": "300000",
    "MCP_TIMEOUT": "60000"
  },
  "apiKeyHelper": "~/.claude/get_api_key.sh",
  "dangerouslySkipPermissions": true,
  "defaultModel": "claude-3-5-sonnet-20241022"
}
```

### API Key Helper Script

```bash
#!/bin/bash
# api-key-helper.sh
# Securely retrieve API key from environment

if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "$ANTHROPIC_API_KEY"
else
    echo "Error: ANTHROPIC_API_KEY environment variable not set" >&2
    exit 1
fi
```

### Building and Deployment

```bash
# Build the custom image
docker build -t backspace-claude-agent:latest .

# Test the image locally
docker run -it \
  -e ANTHROPIC_API_KEY="your-api-key" \
  -e GITHUB_TOKEN="your-github-token" \
  backspace-claude-agent:latest \
  bash

# Push to Daytona
daytona image push backspace-claude-agent:latest

# Verify the image is available
daytona image list
```

## Dev Container Configuration

### Benefits
- **Version controlled**: Configuration stored in repository
- **Team collaboration**: Shared development environment
- **Flexible**: Easy to modify and update
- **IDE integration**: Works with VS Code and other editors

### Complete devcontainer.json

```json
{
  "name": "Backspace Agent Environment",
  "image": "daytonaio/workspace-project:latest",
  
  "features": {
    "ghcr.io/devcontainers/features/node:1": {
      "version": "20"
    },
    "ghcr.io/devcontainers/features/python:1": {
      "version": "3.11"
    },
    "ghcr.io/devcontainers/features/github-cli:1": {}
  },
  
  "postCreateCommand": ".devcontainer/setup-environment.sh",
  
  "customizations": {
    "codeanywhere": {
      "extensions": [
        "ms-python.python",
        "ms-typescript.typescript"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/bin/python3",
        "typescript.preferences.includePackageJsonAutoImports": "auto"
      }
    }
  },
  
  "containerEnv": {
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "true",
    "CLAUDE_CODE_ENABLE_TELEMETRY": "0",
    "BASH_DEFAULT_TIMEOUT_MS": "300000"
  },
  
  "remoteUser": "daytona",
  
  "forwardPorts": [3000, 8000, 5000],
  
  "portsAttributes": {
    "3000": {
      "label": "Frontend",
      "onAutoForward": "notify"
    },
    "8000": {
      "label": "API Server",
      "onAutoForward": "notify"
    }
  }
}
```

### Environment Setup Script

```bash
#!/bin/bash
# .devcontainer/setup-environment.sh

set -e

echo "🚀 Setting up Backspace Agent environment..."

# Install Claude Code
echo "📦 Installing Claude Code..."
npm install -g @anthropic-ai/claude-code

# Create Claude configuration directory
mkdir -p ~/.claude

# Set up API key helper
cat > ~/.claude/get_api_key.sh << 'EOF'
#!/bin/bash
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "$ANTHROPIC_API_KEY"
else
    echo "Error: ANTHROPIC_API_KEY not set" >&2
    exit 1
fi
EOF
chmod +x ~/.claude/get_api_key.sh

# Configure Claude Code settings
cat > ~/.claude/settings.json << 'EOF'
{
  "env": {
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "true",
    "CLAUDE_CODE_ENABLE_TELEMETRY": "0",
    "BASH_DEFAULT_TIMEOUT_MS": "300000"
  },
  "apiKeyHelper": "~/.claude/get_api_key.sh",
  "dangerouslySkipPermissions": true,
  "defaultModel": "claude-3-5-sonnet-20241022"
}
EOF

# Configure Git
git config --global user.name "Backspace Agent"
git config --global user.email "agent@backspace.run"
git config --global init.defaultBranch main
git config --global pull.rebase false

# Install Python packages
pip3 install fastapi uvicorn pytest requests pydantic black flake8

# Install Node.js packages
npm install -g typescript @types/node jest prettier eslint

# Verify installations
echo "✅ Verifying installations..."
echo "Node.js: $(node --version)"
echo "npm: $(npm --version)"
echo "Claude Code: $(claude --version)"
echo "GitHub CLI: $(gh --version)"
echo "Python: $(python3 --version)"
echo "Git: $(git --version)"

echo "🎉 Environment setup complete!"
```

## Project Configuration Method

### Benefits
- **Centralized management**: Organization-wide standardization
- **Reusable**: Apply same config to multiple repositories
- **Scalable**: Easy to update across teams
- **Governance**: Control over development environments

### TypeScript Implementation

```typescript
// project-config.ts
import { Daytona, ProjectConfig } from '@daytonaio/sdk';

export class BackspaceProjectManager {
  private daytona: Daytona;

  constructor(apiKey: string) {
    this.daytona = new Daytona({ api_key: apiKey });
  }

  async createBackspaceProjectConfig(): Promise<ProjectConfig> {
    const config: ProjectConfig = {
      name: "backspace-agent-config",
      description: "Standardized environment for Backspace autonomous coding agents",
      
      repository: {
        url: "https://github.com/your-org/agent-template.git",
        branch: "main"
      },
      
      builder: {
        type: "custom_image",
        image: "backspace-claude-agent:latest"
      },
      
      environmentVariables: {
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}",
        "GITHUB_TOKEN": "${GITHUB_TOKEN}",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "true",
        "CLAUDE_CODE_ENABLE_TELEMETRY": "0",
        "BASH_DEFAULT_TIMEOUT_MS": "300000"
      },
      
      resources: {
        cpu: "2",
        memory: "4Gi",
        storage: "10Gi"
      },
      
      networks: {
        allowedDomains: [
          "api.anthropic.com",
          "api.github.com",
          "github.com"
        ]
      }
    };

    return await this.daytona.projects.create(config);
  }

  async createWorkspaceFromConfig(
    repoUrl: string, 
    configName: string = "backspace-agent-config"
  ) {
    return await this.daytona.workspaces.create({
      projectConfig: configName,
      repository: { url: repoUrl },
      name: `agent-${Date.now()}`
    });
  }
}
```

## Runtime Installation

### Benefits
- **Dynamic**: Configure per request
- **Flexible**: Adapt to different requirements
- **No pre-built images**: Simpler deployment
- **Development friendly**: Quick iteration

### Implementation

```typescript
// runtime-setup.ts
import { Sandbox } from '@daytonaio/sdk';

export class RuntimeClaudeSetup {
  async setupClaudeCode(
    sandbox: Sandbox, 
    config: {
      anthropicApiKey: string;
      githubToken: string;
      skipTelemetry?: boolean;
    }
  ): Promise<void> {
    
    // Install Node.js if not present
    await sandbox.process.code_run(`
      if ! command -v node &> /dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y nodejs
      fi
    `);

    // Install Claude Code
    await sandbox.process.code_run(`
      npm install -g @anthropic-ai/claude-code
    `);

    // Create configuration directory
    await sandbox.process.code_run(`
      mkdir -p ~/.claude
    `);

    // Set up API key helper
    await sandbox.process.code_run(`
      cat > ~/.claude/get_api_key.sh << 'EOF'
#!/bin/bash
echo "${config.anthropicApiKey}"
EOF
      chmod +x ~/.claude/get_api_key.sh
    `);

    // Configure Claude settings
    const settings = {
      env: {
        CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: config.skipTelemetry ? "true" : "false",
        CLAUDE_CODE_ENABLE_TELEMETRY: config.skipTelemetry ? "0" : "1",
        BASH_DEFAULT_TIMEOUT_MS: "300000"
      },
      apiKeyHelper: "~/.claude/get_api_key.sh",
      dangerouslySkipPermissions: true,
      defaultModel: "claude-3-5-sonnet-20241022"
    };

    await sandbox.process.code_run(`
      cat > ~/.claude/settings.json << 'EOF'
${JSON.stringify(settings, null, 2)}
EOF
    `);

    // Set environment variables
    await sandbox.process.code_run(`
      export ANTHROPIC_API_KEY="${config.anthropicApiKey}"
      export GITHUB_TOKEN="${config.githubToken}"
      export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=true
    `);

    // Configure Git
    await sandbox.process.code_run(`
      git config --global user.name "Backspace Agent"
      git config --global user.email "agent@backspace.run"
    `);

    // Install GitHub CLI if needed
    await sandbox.process.code_run(`
      if ! command -v gh &> /dev/null; then
        curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
        echo "deb [arch=\$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
        sudo apt-get update && sudo apt-get install -y gh
      fi
    `);
  }

  async validateSetup(sandbox: Sandbox): Promise<boolean> {
    try {
      // Test Claude Code installation
      const claudeVersion = await sandbox.process.code_run(`claude --version`);
      if (claudeVersion.exitCode !== 0) return false;

      // Test API configuration
      const apiTest = await sandbox.process.code_run(`
        claude -p "Respond with just 'SETUP_OK' if you can see this"
      `);
      
      return apiTest.output.includes('SETUP_OK');
    } catch (error) {
      console.error('Setup validation failed:', error);
      return false;
    }
  }
}
```

## Hybrid Approach Strategy

### Recommended Implementation

```typescript
// hybrid-manager.ts
import { Daytona, Sandbox } from '@daytonaio/sdk';

export class HybridClaudeManager {
  private daytona: Daytona;
  private baseImageName: string = "backspace-claude-agent:latest";

  constructor(apiKey: string) {
    this.daytona = new Daytona({ api_key: apiKey });
  }

  async createConfiguredSandbox(
    repoUrl: string,
    apiKeys: {
      anthropic: string;
      github: string;
    },
    options?: {
      useCustomImage?: boolean;
      skipValidation?: boolean;
    }
  ): Promise<Sandbox> {
    
    // Phase 1: Create sandbox from base image
    const sandbox = await this.daytona.create({
      image: options?.useCustomImage ? this.baseImageName : "daytonaio/workspace-project:latest"
    });

    try {
      // Phase 2: Clone repository
      await sandbox.process.code_run(`
        git clone ${repoUrl} /workspace/repo
        cd /workspace/repo
      `);

      // Phase 3: Runtime configuration (if needed)
      if (!options?.useCustomImage) {
        await this.setupRuntimeEnvironment(sandbox, apiKeys);
      } else {
        await this.configureExistingEnvironment(sandbox, apiKeys);
      }

      // Phase 4: Validation
      if (!options?.skipValidation) {
        const isValid = await this.validateEnvironment(sandbox);
        if (!isValid) {
          throw new Error('Environment validation failed');
        }
      }

      return sandbox;

    } catch (error) {
      // Cleanup on failure
      await sandbox.delete();
      throw error;
    }
  }

  private async setupRuntimeEnvironment(
    sandbox: Sandbox, 
    apiKeys: { anthropic: string; github: string }
  ): Promise<void> {
    const setup = new RuntimeClaudeSetup();
    await setup.setupClaudeCode(sandbox, {
      anthropicApiKey: apiKeys.anthropic,
      githubToken: apiKeys.github,
      skipTelemetry: true
    });
  }

  private async configureExistingEnvironment(
    sandbox: Sandbox,
    apiKeys: { anthropic: string; github: string }
  ): Promise<void> {
    // Set environment variables for pre-configured image
    await sandbox.process.code_run(`
      export ANTHROPIC_API_KEY="${apiKeys.anthropic}"
      export GITHUB_TOKEN="${apiKeys.github}"
      
      # Update Claude API key helper
      echo '#!/bin/bash' > ~/.claude/get_api_key.sh
      echo 'echo "${apiKeys.anthropic}"' >> ~/.claude/get_api_key.sh
      chmod +x ~/.claude/get_api_key.sh
    `);
  }

  async executeClaude(
    sandbox: Sandbox, 
    prompt: string,
    options?: {
      stream?: boolean;
      timeout?: number;
    }
  ): Promise<any> {
    const command = `claude --dangerously-skip-permissions -p "${prompt}"`;
    
    if (options?.stream) {
      return sandbox.process.start(command, { 
        stream: true,
        timeout: options.timeout || 300000
      });
    } else {
      return sandbox.process.code_run(command);
    }
  }

  private async validateEnvironment(sandbox: Sandbox): Promise<boolean> {
    try {
      // Test Claude Code
      const claudeTest = await sandbox.process.code_run(`claude --version`);
      if (claudeTest.exitCode !== 0) return false;

      // Test Git configuration
      const gitTest = await sandbox.process.code_run(`
        git config --get user.name && git config --get user.email
      `);
      if (gitTest.exitCode !== 0) return false;

      // Test GitHub CLI
      const ghTest = await sandbox.process.code_run(`gh --version`);
      if (ghTest.exitCode !== 0) return false;

      return true;
    } catch (error) {
      console.error('Environment validation error:', error);
      return false;
    }
  }
}
```

## Environment Variable Management

### Security Best Practices

```bash
# Production environment variables
export ANTHROPIC_API_KEY="sk-ant-api03-..."
export GITHUB_TOKEN="ghp_..."
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=true
export CLAUDE_CODE_ENABLE_TELEMETRY=0
export CLAUDE_CODE_API_KEY_HELPER_TTL_MS=3600000

# Development overrides
export CLAUDE_CODE_LOG_LEVEL=debug
export BASH_DEFAULT_TIMEOUT_MS=600000
export MCP_TIMEOUT=120000
```

### Environment Configuration File

```typescript
// environment-config.ts
export interface EnvironmentConfig {
  anthropicApiKey: string;
  githubToken: string;
  debugMode?: boolean;
  telemetryEnabled?: boolean;
  timeouts?: {
    bash?: number;
    mcp?: number;
    apiHelper?: number;
  };
}

export class EnvironmentManager {
  static getConfig(): EnvironmentConfig {
    return {
      anthropicApiKey: process.env.ANTHROPIC_API_KEY || '',
      githubToken: process.env.GITHUB_TOKEN || '',
      debugMode: process.env.NODE_ENV === 'development',
      telemetryEnabled: process.env.CLAUDE_CODE_ENABLE_TELEMETRY === '1',
      timeouts: {
        bash: parseInt(process.env.BASH_DEFAULT_TIMEOUT_MS || '300000'),
        mcp: parseInt(process.env.MCP_TIMEOUT || '60000'),
        apiHelper: parseInt(process.env.CLAUDE_CODE_API_KEY_HELPER_TTL_MS || '3600000')
      }
    };
  }

  static validateConfig(config: EnvironmentConfig): string[] {
    const errors: string[] = [];
    
    if (!config.anthropicApiKey) {
      errors.push('ANTHROPIC_API_KEY is required');
    }
    
    if (!config.githubToken) {
      errors.push('GITHUB_TOKEN is required');
    }
    
    if (config.anthropicApiKey && !config.anthropicApiKey.startsWith('sk-ant-')) {
      errors.push('Invalid Anthropic API key format');
    }
    
    if (config.githubToken && !config.githubToken.startsWith('ghp_')) {
      errors.push('Invalid GitHub token format');
    }
    
    return errors;
  }
}
```

## Testing and Validation

### Comprehensive Test Suite

```typescript
// test-suite.ts
import { HybridClaudeManager } from './hybrid-manager';

export class DaytonaClaudeTestSuite {
  private manager: HybridClaudeManager;

  constructor(daytonaApiKey: string) {
    this.manager = new HybridClaudeManager(daytonaApiKey);
  }

  async runFullTestSuite(): Promise<TestResults> {
    const results: TestResults = {
      tests: [],
      passed: 0,
      failed: 0,
      duration: 0
    };

    const startTime = Date.now();

    // Test 1: Environment setup
    await this.runTest(results, 'Environment Setup', async () => {
      const sandbox = await this.manager.createConfiguredSandbox(
        'https://github.com/octocat/Hello-World.git',
        {
          anthropic: process.env.ANTHROPIC_API_KEY!,
          github: process.env.GITHUB_TOKEN!
        }
      );
      
      await sandbox.delete();
      return true;
    });

    // Test 2: Claude Code execution
    await this.runTest(results, 'Claude Code Execution', async () => {
      const sandbox = await this.manager.createConfiguredSandbox(
        'https://github.com/octocat/Hello-World.git',
        {
          anthropic: process.env.ANTHROPIC_API_KEY!,
          github: process.env.GITHUB_TOKEN!
        }
      );

      const response = await this.manager.executeClaude(
        sandbox,
        'List the files in this repository'
      );

      await sandbox.delete();
      return response.exitCode === 0;
    });

    // Test 3: Git operations
    await this.runTest(results, 'Git Operations', async () => {
      const sandbox = await this.manager.createConfiguredSandbox(
        'https://github.com/octocat/Hello-World.git',
        {
          anthropic: process.env.ANTHROPIC_API_KEY!,
          github: process.env.GITHUB_TOKEN!
        }
      );

      const gitStatus = await sandbox.process.code_run('git status');
      const gitConfig = await sandbox.process.code_run('git config --list');

      await sandbox.delete();
      return gitStatus.exitCode === 0 && gitConfig.exitCode === 0;
    });

    results.duration = Date.now() - startTime;
    return results;
  }

  private async runTest(
    results: TestResults,
    name: string,
    testFn: () => Promise<boolean>
  ): Promise<void> {
    try {
      const passed = await testFn();
      results.tests.push({ name, passed, error: null });
      if (passed) {
        results.passed++;
      } else {
        results.failed++;
      }
    } catch (error) {
      results.tests.push({ 
        name, 
        passed: false, 
        error: error instanceof Error ? error.message : String(error)
      });
      results.failed++;
    }
  }
}

interface TestResults {
  tests: Array<{
    name: string;
    passed: boolean;
    error: string | null;
  }>;
  passed: number;
  failed: number;
  duration: number;
}
```

### Usage Example

```typescript
// usage-example.ts
import { HybridClaudeManager, DaytonaClaudeTestSuite } from './';

async function main() {
  const manager = new HybridClaudeManager(process.env.DAYTONA_API_KEY!);
  
  try {
    // Create configured sandbox
    const sandbox = await manager.createConfiguredSandbox(
      'https://github.com/example/sample-repo.git',
      {
        anthropic: process.env.ANTHROPIC_API_KEY!,
        github: process.env.GITHUB_TOKEN!
      }
    );

    // Execute Claude Code
    const response = await manager.executeClaude(
      sandbox,
      'Add input validation to all API endpoints'
    );

    console.log('Claude response:', response.output);

    // Cleanup
    await sandbox.delete();

  } catch (error) {
    console.error('Error:', error);
  }
}

// Run tests
async function runTests() {
  const testSuite = new DaytonaClaudeTestSuite(process.env.DAYTONA_API_KEY!);
  const results = await testSuite.runFullTestSuite();
  
  console.log(`Tests completed: ${results.passed} passed, ${results.failed} failed`);
  console.log(`Duration: ${results.duration}ms`);
}

if (require.main === module) {
  main().catch(console.error);
}
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Claude Code Installation Fails
```bash
# Symptom: npm install fails
# Solution: Update Node.js and npm
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
npm cache clean --force
npm install -g @anthropic-ai/claude-code
```

#### 2. API Key Not Found
```bash
# Symptom: "Error: ANTHROPIC_API_KEY not set"
# Solution: Verify environment variable
echo $ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY="your-key-here"
```

#### 3. Permission Denied Errors
```bash
# Symptom: Claude Code permission errors
# Solution: Use dangerously-skip-permissions flag
claude --dangerously-skip-permissions -p "your prompt"
```

#### 4. Sandbox Creation Timeout
```typescript
// Symptom: Sandbox creation takes too long
// Solution: Increase timeout and use pre-built images
const sandbox = await daytona.create({
  image: "backspace-claude-agent:latest", // pre-built image
  timeout: 120000 // 2 minutes
});
```

### Debug Commands

```bash
# Check Claude Code status
claude --version
claude config list

# Check environment variables
env | grep CLAUDE
env | grep ANTHROPIC

# Test API connectivity
claude -p "Hello, respond with OK"

# Check Git configuration
git config --list

# Verify GitHub CLI
gh auth status
```

### Monitoring and Logging

```typescript
// Enhanced logging for debugging
export class DebugLogger {
  static log(operation: string, data: any) {
    if (process.env.DEBUG_MODE === 'true') {
      console.log(`[${new Date().toISOString()}] ${operation}:`, data);
    }
  }

  static error(operation: string, error: any) {
    console.error(`[${new Date().toISOString()}] ERROR ${operation}:`, error);
  }

  static timing(operation: string, startTime: number) {
    const duration = Date.now() - startTime;
    console.log(`[${new Date().toISOString()}] ${operation} completed in ${duration}ms`);
  }
}
```

## Performance Optimization

### Best Practices

1. **Use Custom Images**: Pre-built images start 10x faster than runtime installation
2. **Cache Dependencies**: Include common packages in base image
3. **Minimize Image Size**: Use multi-stage builds and clean up after installations
4. **Parallel Operations**: Run independent setup tasks concurrently
5. **Resource Limits**: Set appropriate CPU and memory limits

### Performance Monitoring

```typescript
export class PerformanceMonitor {
  private metrics: Map<string, number> = new Map();

  startTimer(operation: string): () => void {
    const startTime = Date.now();
    return () => {
      const duration = Date.now() - startTime;
      this.metrics.set(operation, duration);
    };
  }

  getMetrics(): Record<string, number> {
    return Object.fromEntries(this.metrics);
  }

  logSummary(): void {
    console.log('Performance Summary:');
    for (const [operation, duration] of this.metrics) {
      console.log(`  ${operation}: ${duration}ms`);
    }
  }
}
```

This comprehensive guide provides everything needed to successfully configure Daytona with Claude Code for autonomous coding agent workflows. Choose the approach that best fits your use case and requirements.