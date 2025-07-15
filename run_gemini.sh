#!/bin/bash

# Gemini-Daytona Runner Script
# Easy launcher for the Gemini autonomous coding agent

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    echo -e "${BLUE}Gemini-Daytona Autonomous Coding Agent${NC}"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  api              Start the API server"
    echo "  test             Run the test suite"
    echo "  create [name]    Create a new Gemini sandbox"
    echo "  list             List all sandboxes"
    echo "  delete <id>      Delete a sandbox"
    echo "  code <id> <repo> '<prompt>'  Execute coding task"
    echo "  demo             Run a demo with the test repository"
    echo ""
    echo "Examples:"
    echo "  $0 api"
    echo "  $0 create my-sandbox"
    echo "  $0 code abc123 https://github.com/user/repo 'Add authentication'"
    echo "  $0 demo"
}

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create a .env file with your API keys"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check required environment variables
check_env() {
    local missing=0
    
    if [ -z "$DAYTONA_API_KEY" ]; then
        echo -e "${RED}Missing DAYTONA_API_KEY in .env${NC}"
        missing=1
    fi
    
    if [ -z "$GEMINI_API_KEY" ]; then
        echo -e "${YELLOW}Warning: GEMINI_API_KEY not set - Gemini will need manual auth${NC}"
    fi
    
    if [ -z "$GITHUB_TOKEN" ]; then
        echo -e "${YELLOW}Warning: GITHUB_TOKEN not set - PR creation will fail${NC}"
    fi
    
    if [ $missing -eq 1 ]; then
        exit 1
    fi
}

# Main command handler
case "$1" in
    api)
        check_env
        echo -e "${GREEN}Starting Gemini API server...${NC}"
        python api/gemini_endpoint.py
        ;;
    
    test)
        check_env
        echo -e "${GREEN}Running test suite...${NC}"
        python test_gemini_implementation.py
        ;;
    
    create)
        check_env
        echo -e "${GREEN}Creating Gemini sandbox...${NC}"
        python gemini_daytona_manager.py create $2
        ;;
    
    list)
        check_env
        echo -e "${GREEN}Listing sandboxes...${NC}"
        python gemini_daytona_manager.py list
        ;;
    
    delete)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Please provide sandbox ID${NC}"
            echo "Usage: $0 delete <sandbox-id>"
            exit 1
        fi
        check_env
        echo -e "${GREEN}Deleting sandbox $2...${NC}"
        python gemini_daytona_manager.py delete $2
        ;;
    
    code)
        if [ -z "$2" ] || [ -z "$3" ] || [ -z "$4" ]; then
            echo -e "${RED}Error: Missing arguments${NC}"
            echo "Usage: $0 code <sandbox-id> <repo-url> '<prompt>'"
            exit 1
        fi
        check_env
        echo -e "${GREEN}Executing coding task...${NC}"
        python gemini_daytona_manager.py code "$2" "$3" "$4"
        ;;
    
    demo)
        check_env
        echo -e "${BLUE}Running Gemini Demo${NC}"
        echo -e "${YELLOW}This will create a sandbox and add a README to the test repo${NC}"
        echo ""
        
        # Create sandbox
        echo -e "${GREEN}Step 1: Creating sandbox...${NC}"
        output=$(python gemini_daytona_manager.py create demo-sandbox 2>&1)
        echo "$output"
        
        # Extract sandbox ID
        sandbox_id=$(echo "$output" | grep -oE 'Sandbox ID: [a-zA-Z0-9-]+' | cut -d' ' -f3)
        
        if [ -z "$sandbox_id" ]; then
            echo -e "${RED}Failed to create sandbox${NC}"
            exit 1
        fi
        
        echo ""
        echo -e "${GREEN}Step 2: Running coding task...${NC}"
        python gemini_daytona_manager.py code "$sandbox_id" \
            "https://github.com/mrlancelot/tb-test" \
            "Add a comprehensive README.md file with project overview, installation instructions, and usage examples"
        
        echo ""
        echo -e "${GREEN}Demo complete!${NC}"
        echo -e "${YELLOW}Note: Sandbox $sandbox_id will remain active. Delete it with:${NC}"
        echo "  $0 delete $sandbox_id"
        ;;
    
    *)
        usage
        exit 1
        ;;
esac