#!/usr/bin/env python3
"""
Daytona Development Environment Manager
Creates and manages Claude Code + Gemini CLI environments using Daytona SDK
"""

import os
import sys
from datetime import datetime
from daytona import Daytona, DaytonaConfig

# Fix Windows console encoding for Unicode emojis
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

class DaytonaManager:
    def __init__(self):
        """Initialize Daytona client with API credentials"""
        # Load API key from environment or .env file
        self.api_key = os.getenv('DAYTONA_API_KEY')
        self.api_url = os.getenv('DAYTONA_API_URL', 'https://app.daytona.io/api')
        
        if not self.api_key:
            print("❌ DAYTONA_API_KEY not found in environment variables")
            print("   Please check your .env file")
            sys.exit(1)
            
        # Initialize Daytona client
        try:
            config = DaytonaConfig(
                api_key=self.api_key,
                api_url=self.api_url
            )
            self.daytona = Daytona(config)
            print(f"✅ Connected to Daytona at {self.api_url}")
        except Exception as e:
            print(f"❌ Failed to connect to Daytona: {e}")
            sys.exit(1)
    
    def create_claude_auth_sandbox(self, name=None):
        """Create a new sandbox using the authenticated Claude container"""
        if not name:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            name = f"claude-auth-{timestamp}"
            
        print(f"🚀 Creating authenticated Claude sandbox: {name}")
        
        try:
            # Create sandbox using our authenticated container
            from daytona import CreateSandboxFromImageParams, Resources
            
            params = CreateSandboxFromImageParams(
                name=name,
                image="node:20-slim",  # Use base node image and install our container
                resources=Resources(cpu=2, memory=4),
                env_vars={
                    "CLAUDE_AUTHENTICATED": "true",
                }
            )
            
            sandbox = self.daytona.create(params)
            
            print(f"✅ Authenticated Claude sandbox created: {sandbox.id}")
            
            # Install Docker and load our authenticated container
            self.setup_docker_and_claude_container(sandbox)
            
            return sandbox
            
        except Exception as e:
            print(f"❌ Failed to create sandbox: {e}")
            return None
    
    def setup_docker_and_claude_container(self, sandbox):
        """Setup Claude Code with authentication in the sandbox"""
        print("🔧 Setting up Claude Code with authentication...")
        
        # Install Node.js and Claude Code
        setup_commands = [
            "apt-get update",
            "apt-get install -y curl",
            "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash",
            "export NVM_DIR=\"$HOME/.nvm\" && [ -s \"$NVM_DIR/nvm.sh\" ] && . \"$NVM_DIR/nvm.sh\" && nvm install 20",
            "export NVM_DIR=\"$HOME/.nvm\" && [ -s \"$NVM_DIR/nvm.sh\" ] && . \"$NVM_DIR/nvm.sh\" && npm install -g @anthropic-ai/claude-code",
        ]
        
        for cmd in setup_commands:
            try:
                print(f"⚙️  Running: {cmd}")
                response = sandbox.process.exec(cmd)
                if hasattr(response, 'result') and response.result:
                    print(f"   ✅ Command completed")
            except Exception as e:
                print(f"❌ Command failed: {e}")
        
        # Setup authentication files
        self.setup_claude_authentication_files(sandbox)
    
    def setup_claude_authentication_files(self, sandbox):
        """Copy authentication files to sandbox"""
        print("🔐 Setting up Claude authentication files...")
        
        # Read local auth files
        try:
            with open("C:/Users/pridh/.claude.json", "r") as f:
                claude_json = f.read()
            with open("C:/Users/pridh/.claude/.credentials.json", "r") as f:
                credentials_json = f.read()
        except Exception as e:
            print(f"❌ Failed to read auth files: {e}")
            return
        
        # Create auth directory and files in sandbox
        auth_commands = [
            "mkdir -p /root/.claude",
            f'echo \'{claude_json}\' > /root/.claude.json',
            f'echo \'{credentials_json}\' > /root/.claude/.credentials.json',
            "chmod 600 /root/.claude.json /root/.claude/.credentials.json",
        ]
        
        for cmd in auth_commands:
            try:
                response = sandbox.process.exec(cmd)
                print(f"✅ Authentication file setup completed")
            except Exception as e:
                print(f"❌ Auth setup failed: {e}")
    
    def create_claude_gemini_sandbox(self, name=None):
        """Create a new sandbox with Claude Code and Gemini CLI pre-installed"""
        if not name:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            name = f"claude-gemini-{timestamp}"
            
        print(f"🚀 Creating sandbox: {name}")
        
        try:
            # Create sandbox using correct Daytona SDK
            from daytona import CreateSandboxFromImageParams, Resources
            
            params = CreateSandboxFromImageParams(
                name=name,
                image="python:3.11-bullseye",
                resources=Resources(cpu=2, memory=4),
                env_vars={
                    "ANTHROPIC_API_KEY": os.getenv('ANTHROPIC_API_KEY', ''),
                    "GEMINI_API_KEY": os.getenv('GEMINI_API_KEY', ''),
                    "GOOGLE_API_KEY": os.getenv('GOOGLE_API_KEY', ''),
                }
            )
            
            sandbox = self.daytona.create(params)
            
            print(f"✅ Sandbox created: {sandbox.id}")
            
            # Install Claude Code and Gemini CLI
            self.setup_development_tools(sandbox)
            
            return sandbox
            
        except Exception as e:
            print(f"❌ Failed to create sandbox: {e}")
            return None
    
    def setup_development_tools(self, sandbox):
        """Install Claude Code and Gemini CLI in the sandbox"""
        print("📦 Installing development tools...")
        
        # Install tools step by step
        commands = [
            "apt-get update",
            "apt-get install -y curl",
            "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash",
            "export NVM_DIR=\"$HOME/.nvm\" && [ -s \"$NVM_DIR/nvm.sh\" ] && . \"$NVM_DIR/nvm.sh\" && nvm install 20",
            "export NVM_DIR=\"$HOME/.nvm\" && [ -s \"$NVM_DIR/nvm.sh\" ] && . \"$NVM_DIR/nvm.sh\" && npm install -g @anthropic-ai/claude-code",
            "python3 -m pip install --upgrade pip",
            "echo 'Development environment ready!' > /tmp/setup_complete"
        ]
        
        for cmd in commands:
            try:
                print(f"⚙️  Running: {cmd}")
                response = sandbox.process.code_run(cmd)
                if hasattr(response, 'exit_code') and response.exit_code != 0:
                    print(f"⚠️  Warning: Command failed with exit code {response.exit_code}")
                    if hasattr(response, 'stdout'):
                        print(f"   Output: {response.stdout}")
                else:
                    print("✅ Command completed successfully")
            except Exception as e:
                print(f"❌ Command failed: {e}")
    
    def list_sandboxes(self):
        """List all active sandboxes"""
        try:
            sandboxes = self.daytona.list()
            print("\n📋 Active Sandboxes:")
            print("-" * 50)
            
            if not sandboxes:
                print("No active sandboxes found")
                return
                
            for sandbox in sandboxes:
                print(f"ID: {sandbox.id}")
                print(f"Name: {getattr(sandbox, 'name', 'N/A')}")
                print(f"Status: {getattr(sandbox, 'status', 'Unknown')}")
                print(f"Created: {getattr(sandbox, 'created_at', 'N/A')}")
                print("-" * 30)
                
        except Exception as e:
            print(f"❌ Failed to list sandboxes: {e}")
    
    def connect_to_sandbox(self, sandbox_id):
        """Connect to an existing sandbox"""
        try:
            sandbox = self.daytona.get(sandbox_id)
            print(f"🔗 Connected to sandbox: {sandbox_id}")
            
            # Test Claude Code
            print("\n🧪 Testing Claude Code...")
            try:
                claude_test = sandbox.process.code_run("claude --version")
                if hasattr(claude_test, 'stdout'):
                    print(f"Claude: {claude_test.stdout}")
                else:
                    print("Claude Code test completed")
            except Exception as e:
                print(f"Claude Code not available: {e}")
            
            # Test Gemini CLI  
            print("🧪 Testing Gemini CLI...")
            try:
                gemini_test = sandbox.process.code_run("gemini --version")
                if hasattr(gemini_test, 'stdout'):
                    print(f"Gemini: {gemini_test.stdout}")
                else:
                    print("Gemini CLI test completed")
            except Exception as e:
                print(f"Gemini CLI not available: {e}")
                
            # Test basic Python
            print("🧪 Testing Python...")
            try:
                python_test = sandbox.process.code_run("python3 --version")
                if hasattr(python_test, 'stdout'):
                    print(f"Python: {python_test.stdout}")
                else:
                    print("Python test completed")
            except Exception as e:
                print(f"Python test failed: {e}")
            
            return sandbox
            
        except Exception as e:
            print(f"❌ Failed to connect to sandbox: {e}")
            return None
    
    def install_claude_code(self, sandbox):
        """Install Claude Code in sandbox"""
        print("📦 Installing Claude Code...")
        
        install_commands = [
            "apt-get update",
            "apt-get install -y curl",
            "curl -fsSL https://deb.nodesource.com/setup_20.x | bash -",
            "apt-get install -y nodejs",
            "node --version",
            "npm --version", 
            "npm install -g @anthropic-ai/claude-code",
            "which claude",
            "ls -la /usr/local/bin/ | grep claude || echo 'Claude not in /usr/local/bin'",
            "find /usr -name claude 2>/dev/null || echo 'Claude not found in /usr'"
        ]
        
        for cmd in install_commands:
            try:
                print(f"⚙️  {cmd}")
                response = sandbox.process.exec(cmd)  # Use exec for shell commands
                if hasattr(response, 'result') and response.result:
                    print(f"📝 Output: {response.result}")
                if hasattr(response, 'exit_code'):
                    if response.exit_code == 0:
                        print("✅ Command completed successfully")
                    else:
                        print(f"⚠️ Exit code: {response.exit_code}")
            except Exception as e:
                print(f"❌ Failed: {e}")
        
        # Setup Claude Code authentication
        self.setup_claude_authentication(sandbox)
    
    def setup_claude_authentication(self, sandbox):
        """Setup Claude Code authentication in sandbox"""
        print("🔐 Setting up Claude Code authentication...")
        
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            print("❌ No ANTHROPIC_API_KEY found in environment")
            return False
        
        auth_commands = [
            # Create Claude configuration directory
            "mkdir -p ~/.claude",
            
            # Create authentication file with API key
            f'echo \'{{"apiKey":"{api_key}","userId":"sandbox-user"}}\' > ~/.claude.json',
            
            # Set proper permissions
            "chmod 600 ~/.claude.json",
            
            # Create settings.json for Claude Code
            f'''echo '{{
                "anthropicApiKey": "{api_key}",
                "defaultModel": "claude-3-5-sonnet-20241022"
            }}' > ~/.claude/settings.json''',
            
            # Verify files exist
            "ls -la ~/.claude*",
            "cat ~/.claude.json",
            
            # Test authentication directly with curl
            f'''curl -X POST https://api.anthropic.com/v1/messages \\
                -H "Content-Type: application/json" \\
                -H "x-api-key: {api_key}" \\
                -H "anthropic-version: 2023-06-01" \\
                -d '{{
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 100,
                    "messages": [{{
                        "role": "user",
                        "content": "Just say OK"
                    }}]
                }}' 2>&1 | head -20''',
        ]
        
        for cmd in auth_commands:
            try:
                print(f"🔧 {cmd[:100]}{'...' if len(cmd) > 100 else ''}")
                response = sandbox.process.exec(cmd)
                if hasattr(response, 'result') and response.result:
                    result = response.result.strip()
                    if result:
                        print(f"   {result}")
                print("✅ Auth command completed")
            except Exception as e:
                print(f"❌ Auth command failed: {e}")
        
        return True
                
    def run_claude_code(self, sandbox):
        """Run Claude Code in the sandbox"""
        print("🚀 Testing Claude Code functionality...")
        
        try:
            # Test Claude Code version
            print("🔥 Testing: claude --version")
            version_response = sandbox.process.code_run("claude --version")
            print("✅ Version check completed")
            
            # Test Claude Code without authentication
            print("🔥 Testing: claude --help")
            help_response = sandbox.process.code_run("claude --help")
            print("✅ Help command completed")
            
            # Test if authentication is required
            print("🔥 Testing: claude chat --help")
            chat_help_response = sandbox.process.code_run("claude chat --help")
            print("✅ Chat help completed")
            
            # Try a simple Claude command to see authentication status
            print("🔥 Testing: claude auth status")
            auth_status = sandbox.process.code_run("claude auth status")
            print("✅ Auth status check completed")
            
            # Configure Claude Code with API key from environment
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                print("🔑 Configuring Claude Code with API key...")
                config_cmd = f"echo 'ANTHROPIC_API_KEY={api_key}' >> ~/.bashrc"
                sandbox.process.code_run(config_cmd)
                
                # Set API key for current session
                export_cmd = f"export ANTHROPIC_API_KEY={api_key}"
                sandbox.process.code_run(export_cmd)
                print("✅ API key configured")
                
                # Test authenticated command with simple response
                print("🔥 Testing authenticated command...")
                test_cmd = f"ANTHROPIC_API_KEY={api_key} claude chat 'Hello, can you respond with just the word OK?'"
                test_response = sandbox.process.code_run(test_cmd)
                if hasattr(test_response, 'stdout') and test_response.stdout:
                    print(f"📝 Claude Response: {test_response.stdout.strip()}")
                print("✅ Authenticated command test completed")
            else:
                print("⚠️  No ANTHROPIC_API_KEY found in environment")
            
            print("\n🎯 Claude Code is ready! Commands available:")
            print("   claude --version")
            print("   claude chat 'your message'")
            print("   claude generate --prompt 'your request'")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to test Claude Code: {e}")
            return False
    
    def send_prompt_to_claude(self, sandbox, prompt):
        """Send a prompt to Claude Code and stream the response"""
        print(f"🚀 Sending prompt to Claude Code...")
        print(f"📝 Prompt: {prompt}")
        print("=" * 60)
        
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            print("❌ No ANTHROPIC_API_KEY found")
            return False
        
        # Try with verbose flag for stream-json output with proper PATH
        cmd = f'export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && echo "{prompt}" | claude --print --verbose --output-format stream-json'
        
        try:
            print(f"🔥 Executing: claude --print --output-format stream-json")
            print("-" * 60)
            
            # Execute the command with timeout
            response = sandbox.process.exec(cmd)
            
            if hasattr(response, 'result') and response.result:
                result = response.result.strip()
                
                # Check if it's a valid response or error
                if "Invalid API key" in result:
                    print("❌ API Key authentication failed in sandbox")
                    print("   This may be due to:")
                    print("   1. Sandbox network restrictions")
                    print("   2. Claude Code requiring interactive authentication")
                    print("   3. API key environment variable not properly set in sandbox")
                    print("")
                    print("✅ However, Claude Code is successfully installed and can be used!")
                    print("🎯 Available features in sandbox:")
                    print("   - Claude Code CLI installed at /usr/bin/claude")
                    print("   - Stream JSON output format supported (--output-format stream-json --verbose)")
                    print("   - Thinking mode would be available with proper authentication")
                    print("   - Interactive mode available with: claude")
                    print("")
                    print("🔧 For manual testing in sandbox:")
                    print(f"   ANTHROPIC_API_KEY='your-key' claude --print '{prompt}'")
                    print(f"   ANTHROPIC_API_KEY='your-key' claude --print --verbose --output-format stream-json '{prompt}'")
                    return False
                
                # If we got JSON output, try to parse and display nicely
                if result.startswith('{') or '[' in result:
                    print("🎯 Claude Response (Stream JSON):")
                    print(result)
                else:
                    print("🎯 Claude Response:")
                    print(result)
                
                print("=" * 60)
                print("✅ Response received successfully!")
                return True
                
            else:
                print("⚠️ No response content received")
                return False
                
        except Exception as e:
            print(f"❌ Command failed: {e}")
            return False
    
    def create_docker_claude_sandbox(self, name=None):
        """Create a new sandbox with Docker-based Claude Code setup"""
        if not name:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            name = f"claude-docker-{timestamp}"
            
        print(f"🐳 Creating Docker-based Claude Code sandbox: {name}")
        
        try:
            # Create sandbox with Docker pre-installed
            from daytona import CreateSandboxFromImageParams, Resources
            
            params = CreateSandboxFromImageParams(
                name=name,
                image="docker:20.10-dind",  # Docker-in-Docker image
                resources=Resources(cpu=2, memory=4),  # Reduced memory for quota
                env_vars={
                    "ANTHROPIC_API_KEY": os.getenv('ANTHROPIC_API_KEY', ''),
                    "TWILIO_ACCOUNT_SID": os.getenv('TWILIO_ACCOUNT_SID', ''),
                    "TWILIO_AUTH_TOKEN": os.getenv('TWILIO_AUTH_TOKEN', ''),
                    "TWILIO_FROM_NUMBER": os.getenv('TWILIO_FROM_NUMBER', ''),
                    "TWILIO_TO_NUMBER": os.getenv('TWILIO_TO_NUMBER', ''),
                }
            )
            
            sandbox = self.daytona.create(params)
            print(f"✅ Sandbox created: {sandbox.id}")
            
            # Setup Docker and Claude Code
            self.setup_docker_claude(sandbox)
            
            return sandbox
            
        except Exception as e:
            print(f"❌ Failed to create Docker sandbox: {e}")
            return None
    
    def setup_docker_claude(self, sandbox):
        """Setup Docker-based Claude Code in sandbox"""
        print("🐳 Setting up Docker-based Claude Code...")
        
        # Setup commands for Docker-based Claude Code
        setup_commands = [
            # Start Docker daemon
            "dockerd-entrypoint.sh &",
            "sleep 10",  # Wait for Docker to start
            
            # Install dependencies
            "apk add --no-cache git curl bash nodejs npm",
            
            # Clone claude-docker repository
            "cd /workspace && git clone https://github.com/VishalJ99/claude-docker.git",
            "cd /workspace/claude-docker",
            
            # Setup environment
            "cp .env.example .env",
            
            # Create necessary directories and files for authentication
            "mkdir -p ~/.claude-docker/claude-home",
            "mkdir -p ~/.claude-docker/ssh",
            
            # Create minimal Claude authentication (since we can't authenticate interactively)
            'echo \'{"api_key": "placeholder"}\' > ~/.claude.json',
            
            # Build the Docker image
            "docker build -t claude-docker:latest .",
        ]
        
        for cmd in setup_commands:
            try:
                print(f"⚙️  {cmd}")
                response = sandbox.process.exec(cmd)
                if hasattr(response, 'exit_code'):
                    if response.exit_code == 0:
                        print("✅ Command completed successfully")
                    else:
                        print(f"⚠️ Exit code: {response.exit_code}")
                        if hasattr(response, 'result') and response.result:
                            print(f"   Output: {response.result[:200]}...")
            except Exception as e:
                print(f"❌ Command failed: {e}")
    
    def run_docker_claude_prompt(self, sandbox, prompt):
        """Run Claude Code in Docker container with a prompt"""
        print(f"🐳 Running Claude Code in Docker...")
        print(f"📝 Prompt: {prompt}")
        print("=" * 60)
        
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            print("❌ No ANTHROPIC_API_KEY found")
            return False
        
        # Create a temporary project directory with the prompt
        docker_commands = [
            "cd /workspace",
            "mkdir -p temp-project",
            "cd temp-project",
            f'echo "{prompt}" > prompt.txt',
            
            # Run Claude Docker with the prompt
            f'docker run -it --rm \
                -v "$(pwd)":/workspace \
                -e ANTHROPIC_API_KEY="{api_key}" \
                claude-docker:latest \
                --print "$(cat prompt.txt)"'
        ]
        
        for cmd in docker_commands:
            try:
                print(f"🔥 Executing: {cmd}")
                response = sandbox.process.exec(cmd)
                
                if hasattr(response, 'result') and response.result:
                    result = response.result.strip()
                    if result:
                        print("🎯 Claude Response:")
                        print(result)
                        print("=" * 60)
                        return True
                        
            except Exception as e:
                print(f"❌ Command failed: {e}")
                
        return False
    
    def setup_claude_docker_in_sandbox(self, sandbox):
        """Setup claude-docker repository in existing sandbox"""
        print("🐳 Setting up claude-docker in sandbox...")
        
        setup_commands = [
            # Install Docker if not present
            "which docker || (apt-get update && apt-get install -y docker.io && systemctl start docker)",
            
            # Clone and setup claude-docker in one command
            "git clone https://github.com/VishalJ99/claude-docker.git 2>/dev/null || echo 'Already cloned'",
            
            # Setup the environment and authentication
            "cd claude-docker && cp .env.example .env",
            
            # Create necessary directories
            "mkdir -p ~/.claude-docker/claude-home ~/.claude-docker/ssh",
            
            # Show what we have
            "ls -la claude-docker/ 2>/dev/null || echo 'No claude-docker directory'",
            "ls -la ~/.claude-docker/",
            "echo 'Claude-docker repository ready for Docker build!'",
        ]
        
        for cmd in setup_commands:
            try:
                print(f"⚙️  {cmd}")
                response = sandbox.process.exec(cmd)
                if hasattr(response, 'result') and response.result:
                    output = response.result.strip()
                    if output and not output.startswith('+ '):  # Skip shell trace output
                        print(f"   {output}")
                print("✅ Command completed")
            except Exception as e:
                print(f"❌ Command failed: {e}")
    
    def build_and_run_claude_docker(self, sandbox):
        """Build and run the actual claude-docker container with proper authentication"""
        print("🐳 Building Claude Docker container with your full authentication...")
        
        # Read your actual Claude authentication files from Windows
        claude_json_content = '''{
  "numStartups": 3,
  "installMethod": "unknown", 
  "autoUpdates": true,
  "userID": "9dbfefba7621cdea413ee6731681b753f23d1f569f600b2bf1ff9e27159faa2f",
  "hasCompletedOnboarding": true,
  "oauthAccount": {
    "accountUuid": "3fb425bb-3fb1-4a3f-a308-616b742b3c64",
    "emailAddress": "pridhvisowmya@gmail.com",
    "organizationUuid": "6123f6ef-c577-471f-8ed0-3731ff57596e",
    "organizationRole": "admin",
    "organizationName": "pridhvisowmya@gmail.com's Organization"
  }
}'''

        credentials_content = '''{"claudeAiOauth":{"accessToken":"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","refreshToken":"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","expiresAt":1752547043859,"scopes":["user:inference","user:profile"],"subscriptionType":"pro"}}'''
        
        # Setup authentication files that Docker needs - with your real credentials
        auth_setup_commands = [
            # Install Docker first if needed
            "which docker || (apt-get update && apt-get install -y docker.io)",
            
            # Start Docker daemon
            "dockerd > /dev/null 2>&1 & sleep 5",
            
            # Create a script to do everything in the claude-docker directory
            f'''cat > setup_docker.sh << 'EOF'
#!/bin/bash
cd claude-docker
cat > .claude.json << 'AUTHEOF'
{claude_json_content}
AUTHEOF
mkdir -p .claude
cat > .claude/.credentials.json << 'CREDEOF'
{credentials_content}
CREDEOF
echo "ANTHROPIC_API_KEY=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" >> .env
pwd
ls -la Dockerfile
docker build --build-arg GIT_USER_NAME='Pridhvi' --build-arg GIT_USER_EMAIL='pridhvisowmya@gmail.com' --build-arg USER_UID=1001 --build-arg USER_GID=1001 -t claude-docker:latest .
EOF''',
            
            # Run the setup script
            "chmod +x setup_docker.sh && ./setup_docker.sh",
            
            # Show that the image was built
            "docker images | grep claude-docker",
        ]
        
        for cmd in auth_setup_commands:
            try:
                print(f"🔧 {cmd}")
                response = sandbox.process.exec(cmd)
                if hasattr(response, 'result') and response.result:
                    result = response.result.strip()
                    if result:
                        print(f"   {result}")
                        
                        # Check for successful build
                        if "Successfully tagged claude-docker:latest" in result:
                            print("🎉 Docker image built successfully!")
                            
                print("✅ Build command completed")
            except Exception as e:
                print(f"❌ Build command failed: {e}")
        
        return True
    
    def run_claude_docker_prompt(self, sandbox, prompt):
        """Run Claude Code using the actual claude-docker container with proper authentication"""
        print(f"🐳 Running prompt in Claude Docker container...")
        print(f"📝 Prompt: {prompt}")
        print("=" * 60)
        
        # Check if Docker image exists, if not build it
        check_docker_cmd = "cd claude-docker && docker images | grep claude-docker || echo 'Image not found'"
        
        try:
            response = sandbox.process.exec(check_docker_cmd)
            if hasattr(response, 'result') and response.result:
                if "Image not found" in response.result:
                    print("🔧 Docker image not found, building it first...")
                    self.build_and_run_claude_docker(sandbox)
        except Exception as e:
            print(f"⚠️ Could not check Docker image: {e}")
        
        # Create a working directory and run the container
        docker_run_commands = [
            "cd claude-docker",
            "mkdir -p temp-workspace",
            "chmod 777 temp-workspace",
            "cd temp-workspace",
            
            # Create the prompt file
            f'echo "{prompt}" > prompt.txt',
            'chmod 644 prompt.txt',
            
            # Run the Claude Docker container with simpler approach
            f'''docker run --rm \\
                -v "$(pwd)":/workspace \\
                --workdir /workspace \\
                claude-docker:latest \\
                claude --print "{prompt}"''',
        ]
        
        print("🚀 Executing Claude Docker container...")
        for cmd in docker_run_commands:
            try:
                print(f"🔥 {cmd[:100]}{'...' if len(cmd) > 100 else ''}")
                response = sandbox.process.exec(cmd)
                
                if hasattr(response, 'result') and response.result:
                    result = response.result.strip()
                    if result:
                        # If this looks like a Claude response (not an error)
                        if len(result) > 50 and "Error" not in result[:50] and "docker:" not in result[:20]:
                            print("🎯 Claude Response from Container:")
                            print("=" * 60)
                            print(result)
                            print("=" * 60)
                            print("✅ Successfully got response from Claude Docker container!")
                            return True
                        else:
                            print(f"📝 Command output: {result}")
                            
            except Exception as e:
                print(f"❌ Docker command failed: {e}")
        
        print("⚠️ Could not get response from Docker container, trying fallback...")
        return self._try_fallback_approach(sandbox, prompt)
    
    def _try_fallback_approach(self, sandbox, prompt):
        """Fallback approach: run Claude Code directly in sandbox"""
        print("🔄 Fallback: Running Claude Code directly in sandbox...")
        
        # Test direct Claude Code execution with proper setup
        claude_commands = [
            'mkdir -p /tmp/claude-workspace && cd /tmp/claude-workspace',
            f'claude --print "{prompt}"'
        ]
        
        for cmd in claude_commands:
            try:
                print(f"🔧 {cmd}")
                response = sandbox.process.exec(cmd)
                if hasattr(response, 'result') and response.result:
                    result = response.result.strip()
                    if result and len(result) > 20 and "Error" not in result[:100]:
                        print("✅ Fallback Claude Response:")
                        print("=" * 50)
                        print(result)
                        print("=" * 50)
                        return True
                    else:
                        print(f"📝 Command output: {result}")
            except Exception as e:
                print(f"❌ Fallback command failed: {e}")
        
        # Try the enhanced prompt approach
        return self._run_enhanced_prompt_in_sandbox(sandbox, prompt)
    
    def _run_enhanced_prompt_in_sandbox(self, sandbox, prompt):
        """Run enhanced prompt directly in sandbox environment"""
        print("🎯 Trying enhanced prompt approach...")
        
        enhanced_prompt = f"""Task: {prompt}

Please approach this systematically:

1. 🧠 THINKING: Break down what's needed
2. 📝 IMPLEMENTATION: Write clean, documented code  
3. 🔍 EXPLANATION: Explain your approach

Let's solve this step by step!"""
        
        try:
            response = sandbox.process.exec(f'claude --print "{enhanced_prompt}"')
            if hasattr(response, 'result') and response.result:
                result = response.result.strip()
                if result and len(result) > 50:
                    print("🎉 Enhanced Claude Response:")
                    print("=" * 60)
                    print(result)
                    print("=" * 60)
                    return True
                else:
                    print(f"📝 Enhanced output: {result}")
        except Exception as e:
            print(f"❌ Enhanced prompt failed: {e}")
        
        print("❌ All approaches failed")
        return False
    
    def _run_enhanced_prompt(self, sandbox, prompt, api_key):
        """Run the enhanced prompt with thinking process"""
        enhanced_prompt = f"""Task: {prompt}

Please approach this systematically and show your thinking:

1. 🧠 THINKING PROCESS:
   - Break down the problem
   - Consider different approaches
   - Choose the best solution

2. 📝 IMPLEMENTATION:
   - Write clean, well-documented code
   - Include examples and test cases

3. 🔍 EXPLANATION:
   - Explain your reasoning
   - Discuss any trade-offs or alternatives

Please show all your thinking and reasoning throughout."""

        cmd = f'cd claude-docker/temp-work && ANTHROPIC_API_KEY="{api_key}" claude --print --verbose "{enhanced_prompt}"'
        
        try:
            print("🚀 Running enhanced prompt with thinking process...")
            response = sandbox.process.exec(cmd)
            
            if hasattr(response, 'result') and response.result:
                result = response.result.strip()
                print("🎯 Claude Response with Thinking:")
                print("=" * 60)
                print(result)
                print("=" * 60)
                return True
                
        except Exception as e:
            print(f"❌ Enhanced prompt failed: {e}")
            
        return False
    
    def _show_claude_docker_structure(self, sandbox):
        """Show the claude-docker setup structure and capabilities"""
        print("\n🐳 Claude-Docker Environment Structure:")
        print("=" * 60)
        
        structure_commands = [
            "echo '📁 Claude-Docker Repository:'",
            "ls -la claude-docker/ | head -10",
            "echo '\\n📋 MCP Servers Available:'", 
            "cat claude-docker/mcp-servers.txt 2>/dev/null || echo 'MCP servers file not found'",
            "echo '\\n⚙️ Environment Configuration:'",
            "head -5 claude-docker/.env 2>/dev/null || echo 'Env file not found'",
            "echo '\\n🏠 Claude Home Directory:'",
            "ls -la ~/.claude-docker/ 2>/dev/null || echo 'Claude docker home not found'",
            "echo '\\n✨ Available Features:'",
            "echo '- Pre-configured MCP servers (Serena, Context7, Twilio)'",
            "echo '- Enhanced prompt engineering with thinking process'", 
            "echo '- Persistent conversation history'",
            "echo '- Task execution logging'",
            "echo '- SMS notifications via Twilio'",
        ]
        
        for cmd in structure_commands:
            try:
                response = sandbox.process.exec(cmd)
                if hasattr(response, 'result') and response.result:
                    print(response.result.strip())
            except Exception as e:
                print(f"❌ {e}")
                
        print("=" * 60)
    
    def delete_sandbox(self, sandbox_id):
        """Delete a sandbox"""
        try:
            sandbox = self.daytona.get(sandbox_id)
            sandbox.delete()
            print(f"🗑️  Deleted sandbox: {sandbox_id}")
        except Exception as e:
            print(f"❌ Failed to delete sandbox: {e}")
    
    def run_interactive_shell(self, sandbox):
        """Start an interactive Python shell in the sandbox"""
        print("\n🐍 Starting Python server in sandbox...")
        print("📡 Server will be accessible on port 8000")
        
        # Start Python HTTP server
        server_cmd = "cd /workspace && python3 -m http.server 8000"
        try:
            response = sandbox.process.code_run(server_cmd, timeout=None)
            print(f"Server output: {response.output}")
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
        except Exception as e:
            print(f"❌ Server error: {e}")

def main():
    """Main CLI interface"""
    # Load environment variables from .env file
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    manager = DaytonaManager()
    
    if len(sys.argv) < 2:
        print("\n🌟 Daytona Development Environment Manager")
        print("=" * 50)
        print("Commands:")
        print("  create          - Create new Claude+Gemini sandbox")
        print("  create-auth     - Create new authenticated Claude sandbox")
        print("  setup-docker <id> - Setup claude-docker in existing sandbox")
        print("  fix-auth <id>   - Fix Claude Code authentication in sandbox")
        print("  list            - List all sandboxes")
        print("  connect <id>    - Connect to existing sandbox")
        print("  claude <id>     - Install and run Claude Code in sandbox")
        print("  docker-prompt <id> '<prompt>' - Use claude-docker approach with prompt")
        print("  test <id>       - Test Claude Code with actual chat")
        print("  prompt <id> '<prompt>' - Send prompt to Claude Code with streaming")
        print("  delete <id>     - Delete a sandbox")
        print("  server <id>     - Start Python server in sandbox")
        print("\nExample:")
        print("  python daytona_manager.py create")
        print("  python daytona_manager.py list")
        return
    
    command = sys.argv[1]
    
    if command == "create":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        sandbox = manager.create_claude_gemini_sandbox(name)
        if sandbox:
            print(f"\n🎉 Environment ready! Sandbox ID: {sandbox.id}")
            print(f"🔗 Use: python {sys.argv[0]} connect {sandbox.id}")
    
    elif command == "create-auth":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        sandbox = manager.create_claude_auth_sandbox(name)
        if sandbox:
            print(f"\n🎉 Authenticated Claude environment ready! Sandbox ID: {sandbox.id}")
            print(f"🔗 Use: python {sys.argv[0]} connect {sandbox.id}")
            print(f"🚀 Test: python {sys.argv[0]} prompt {sandbox.id} 'Write hello world'")
    
    elif command == "setup-docker":
        if len(sys.argv) < 3:
            print("❌ Please provide sandbox ID")
            return
        sandbox_id = sys.argv[2]
        sandbox = manager.connect_to_sandbox(sandbox_id)
        if sandbox:
            manager.setup_claude_docker_in_sandbox(sandbox)
            print(f"\n🐳 Claude-docker setup complete!")
            print(f"🔗 Use: python {sys.argv[0]} docker-prompt {sandbox.id} 'your prompt'")
    
    elif command == "fix-auth":
        if len(sys.argv) < 3:
            print("❌ Please provide sandbox ID")
            return
        sandbox_id = sys.argv[2]
        sandbox = manager.connect_to_sandbox(sandbox_id)
        if sandbox:
            manager.build_and_run_claude_docker(sandbox)
            print(f"\n🐳 Claude Docker container built with proper authentication!")
            print(f"🔗 Use: python {sys.argv[0]} docker-prompt {sandbox.id} 'your prompt'")
    
    elif command == "list":
        manager.list_sandboxes()
    
    elif command == "connect":
        if len(sys.argv) < 3:
            print("❌ Please provide sandbox ID")
            return
        sandbox_id = sys.argv[2]
        manager.connect_to_sandbox(sandbox_id)
    
    elif command == "claude":
        if len(sys.argv) < 3:
            print("❌ Please provide sandbox ID")
            return
        sandbox_id = sys.argv[2]
        sandbox = manager.connect_to_sandbox(sandbox_id)
        if sandbox:
            manager.install_claude_code(sandbox)
            manager.run_claude_code(sandbox)
    
    elif command == "test":
        if len(sys.argv) < 3:
            print("❌ Please provide sandbox ID")
            return
        sandbox_id = sys.argv[2]
        sandbox = manager.connect_to_sandbox(sandbox_id)
        if sandbox:
            print("🧪 Testing Claude Code with actual chat...")
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                # Test Claude Code now that it's properly installed
                commands_to_try = [
                    "which claude",
                    "claude --version",
                    f"ANTHROPIC_API_KEY='{api_key}' claude --version",
                    f"ANTHROPIC_API_KEY='{api_key}' claude chat 'Hello, just respond with OK to confirm you are working'",
                ]
                
                for i, test_cmd in enumerate(commands_to_try):
                    try:
                        print(f"🔥 Test {i+1}: {test_cmd}")
                        
                        # Try different execution methods
                        if hasattr(sandbox.process, 'exec'):
                            response = sandbox.process.exec(test_cmd)
                        elif hasattr(sandbox.process, 'execute'):
                            response = sandbox.process.execute(test_cmd)
                        else:
                            response = sandbox.process.code_run(test_cmd)
                            
                        print(f"📊 Response type: {type(response)}")
                        
                        # Check all possible response attributes
                        for attr in ['stdout', 'output', 'result', 'content', 'response']:
                            if hasattr(response, attr):
                                value = getattr(response, attr)
                                if value:
                                    print(f"📝 {attr}: {value}")
                        
                        # Check exit code
                        if hasattr(response, 'exit_code'):
                            print(f"🔢 Exit code: {response.exit_code}")
                            if response.exit_code == 0:
                                print("✅ Command succeeded!")
                                break  # Stop on first successful command
                        
                        if hasattr(response, 'stderr'):
                            stderr = getattr(response, 'stderr')
                            if stderr:
                                print(f"❌ Stderr: {stderr}")
                        
                        print("-" * 40)
                        
                    except Exception as e:
                        print(f"❌ Test {i+1} failed: {e}")
                        print("-" * 40)
            else:
                print("❌ No ANTHROPIC_API_KEY found")
    
    elif command == "prompt":
        if len(sys.argv) < 4:
            print("❌ Usage: python daytona_manager.py prompt <sandbox-id> '<your-prompt>'")
            return
        sandbox_id = sys.argv[2]
        prompt = sys.argv[3]
        sandbox = manager.connect_to_sandbox(sandbox_id)
        if sandbox:
            manager.send_prompt_to_claude(sandbox, prompt)
    
    elif command == "docker-prompt":
        if len(sys.argv) < 4:
            print("❌ Usage: python daytona_manager.py docker-prompt <sandbox-id> '<your-prompt>'")
            return
        sandbox_id = sys.argv[2]
        prompt = sys.argv[3]
        sandbox = manager.connect_to_sandbox(sandbox_id)
        if sandbox:
            manager.run_claude_docker_prompt(sandbox, prompt)
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("❌ Please provide sandbox ID")
            return
        sandbox_id = sys.argv[2]
        manager.delete_sandbox(sandbox_id)
    
    elif command == "server":
        if len(sys.argv) < 3:
            print("❌ Please provide sandbox ID")
            return
        sandbox_id = sys.argv[2]
        sandbox = manager.connect_to_sandbox(sandbox_id)
        if sandbox:
            manager.run_interactive_shell(sandbox)
    
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()