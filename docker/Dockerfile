# Dockerfile for Daytona with Claude Code and Gemini CLI
FROM ubuntu:22.04

# Set non-interactive mode for apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    nodejs \
    npm \
    python3 \
    python3-pip \
    ca-certificates \
    gnupg \
    lsb-release \
    sudo \
    vim \
    nano \
    && rm -rf /var/lib/apt/lists/*

# Install latest Node.js (20+)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Create a non-root user
RUN useradd -m -s /bin/bash developer \
    && echo "developer ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to developer user
USER developer
WORKDIR /home/developer

# Create directories for persistent auth storage
RUN mkdir -p /home/developer/.claude \
    && mkdir -p /home/developer/.gemini \
    && mkdir -p /home/developer/.config/gcloud \
    && mkdir -p /home/developer/.npm-global

# Configure npm to use user directory
RUN npm config set prefix '/home/developer/.npm-global'
ENV PATH="/home/developer/.npm-global/bin:$PATH"

# Install Claude Code
RUN npm install -g @anthropic-ai/claude-code

# Install Gemini CLI
RUN npm install -g @google-ai/gemini-cli

# Set environment variables for authentication persistence
ENV CLAUDE_CONFIG_DIR="/home/developer/.claude"
ENV GEMINI_CONFIG_DIR="/home/developer/.gemini"

# Create startup script
RUN echo '#!/bin/bash\n\
# Start Python server if requested\n\
if [ "$START_PYTHON_SERVER" = "true" ]; then\n\
    echo "Starting Python development server..."\n\
    python3 -m http.server 8000 &\n\
fi\n\
\n\
# Check authentication status\n\
echo "=== Authentication Status ==="\n\
if [ -f "$CLAUDE_CONFIG_DIR/.credentials.json" ] || [ -n "$ANTHROPIC_API_KEY" ]; then\n\
    echo "✅ Claude Code authentication found - ready to use!"\n\
else\n\
    echo "❌ Claude Code not authenticated. Run: claude auth login"\n\
fi\n\
\n\
if [ -f "$GEMINI_CONFIG_DIR/config.json" ] || [ -n "$GEMINI_API_KEY" ]; then\n\
    echo "✅ Gemini CLI authentication found - ready to use!"\n\
else\n\
    echo "❌ Gemini CLI not authenticated. Run: gemini auth login"\n\
fi\n\
\n\
echo ""\n\
echo "=== Development Environment Ready! ==="\n\
echo "Available commands:"\n\
echo "  claude    - Start Claude Code"\n\
echo "  gemini    - Start Gemini CLI"\n\
echo "  python3   - Python interpreter"\n\
echo ""\n\
\n\
# Keep container running\n\
exec "$@"\n\
' > /home/developer/startup.sh && chmod +x /home/developer/startup.sh

# Set working directory to project mount point
WORKDIR /workspace

# Default command
CMD ["/home/developer/startup.sh", "bash"]