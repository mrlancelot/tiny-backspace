#!/bin/bash

# Daytona Development Environment Setup Script
# This script sets up Claude Code and Gemini CLI with persistent authentication

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed and running
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker."
        exit 1
    fi
    
    print_success "Docker is installed and running"
}

# Check if Docker Compose is available
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
    
    print_success "Docker Compose is available"
}

# Setup authentication for the first time
setup_auth() {
    print_status "Setting up authentication for Claude Code and Gemini CLI..."
    
    # Build and start the container
    docker-compose up -d --build
    
    print_warning "First-time setup: You need to authenticate both tools"
    print_status "Starting interactive session for authentication..."
    
    # Enter container for authentication
    docker-compose exec dev-environment bash -c "
        echo 'Welcome to the development environment!'
        echo ''
        echo 'Please authenticate your tools:'
        echo '1. For Claude Code: Run \"claude\" and follow the OAuth flow'
        echo '2. For Gemini CLI: Run \"gemini\" and follow the OAuth flow'
        echo ''
        echo 'After authentication, your credentials will be saved and persist across container restarts.'
        echo 'Type \"exit\" when done.'
        echo ''
        bash
    "
    
    print_success "Authentication setup complete! Credentials are now persistent."
}

# Start the development environment
start_env() {
    print_status "Starting development environment..."
    
    # Check if volumes exist (indicating previous authentication)
    if docker volume ls | grep -q "claude_auth" && docker volume ls | grep -q "gemini_auth"; then
        print_success "Found existing authentication volumes"
    else
        print_warning "No authentication volumes found. You may need to authenticate."
    fi
    
    docker-compose up -d
    
    print_success "Development environment started!"
    print_status "Access it with: docker-compose exec dev-environment bash"
}

# Stop the development environment
stop_env() {
    print_status "Stopping development environment..."
    docker-compose down
    print_success "Environment stopped"
}

# Clean up everything (including authentication)
clean_all() {
    print_warning "This will remove ALL data including saved authentication!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Cleaning up all containers and volumes..."
        docker-compose down -v --remove-orphans
        docker system prune -f
        print_success "Cleanup complete"
    else
        print_status "Cleanup cancelled"
    fi
}

# Show status
show_status() {
    print_status "Development Environment Status:"
    echo ""
    
    # Check if container is running
    if docker-compose ps | grep -q "Up"; then
        print_success "Container is running"
    else
        print_warning "Container is not running"
    fi
    
    # Check volumes
    echo ""
    print_status "Authentication volumes:"
    for vol in claude_auth gemini_auth gcloud_auth npm_cache; do
        if docker volume ls | grep -q "$vol"; then
            print_success "$vol exists"
        else
            print_warning "$vol not found"
        fi
    done
}

# Show usage
usage() {
    echo "Daytona Development Environment Manager"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  setup     - Initial setup with authentication"
    echo "  start     - Start the development environment"
    echo "  stop      - Stop the development environment"
    echo "  restart   - Restart the development environment"
    echo "  shell     - Open a shell in the running container"
    echo "  status    - Show environment status"
    echo "  clean     - Clean up all data (WARNING: removes authentication)"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup     # First time setup"
    echo "  $0 start     # Start environment"
    echo "  $0 shell     # Open shell in container"
}

# Main script logic
main() {
    case "${1:-help}" in
        "setup")
            check_docker
            check_daytona
            setup_auth
            ;;
        "start")
            check_docker
            start_env
            ;;
        "stop")
            stop_env
            ;;
        "restart")
            stop_env
            start_env
            ;;
        "shell")
            docker-compose exec dev-environment bash
            ;;
        "status")
            show_status
            ;;
        "clean")
            clean_all
            ;;
        "help"|*)
            usage
            ;;
    esac
}

# Run the main function
main "$@"