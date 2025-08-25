#!/bin/bash

# MCP Development Analysis Runner
# This script provides an easy way to analyze MCP development trends
# with minimal setup requirements.

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_REQUIREMENTS="$SCRIPT_DIR/requirements.txt"
ANALYSIS_SCRIPT="$SCRIPT_DIR/comprehensive_mcp_analysis.py"

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

print_header() {
    echo -e "${PURPLE}================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}================================${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS
detect_os() {
    case "$(uname -s)" in
        Linux*)     echo "linux";;
        Darwin*)    echo "macos";;
        CYGWIN*)    echo "windows";;
        MINGW*)     echo "windows";;
        MSYS*)      echo "windows";;
        *)          echo "unknown";;
    esac
}

# Function to install Python if needed
install_python() {
    local os=$(detect_os)
    
    print_status "Detected OS: $os"
    
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_success "Python 3 found: $PYTHON_VERSION"
        return 0
    elif command_exists python; then
        PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
        if [[ $PYTHON_VERSION == Python\ 3* ]]; then
            print_success "Python 3 found: $PYTHON_VERSION"
            return 0
        fi
    fi
    
    print_warning "Python 3 not found. Attempting to install..."
    
    case $os in
        "linux")
            if command_exists apt-get; then
                print_status "Installing Python 3 via apt-get..."
                sudo apt-get update
                sudo apt-get install -y python3 python3-pip python3-venv
            elif command_exists yum; then
                print_status "Installing Python 3 via yum..."
                sudo yum install -y python3 python3-pip
            elif command_exists dnf; then
                print_status "Installing Python 3 via dnf..."
                sudo dnf install -y python3 python3-pip
            else
                print_error "Could not install Python 3 automatically. Please install Python 3.8+ manually."
                return 1
            fi
            ;;
        "macos")
            if command_exists brew; then
                print_status "Installing Python 3 via Homebrew..."
                brew install python3
            else
                print_error "Homebrew not found. Please install Python 3.8+ manually or install Homebrew first."
                return 1
            fi
            ;;
        "windows")
            print_error "Please install Python 3.8+ from https://python.org"
            return 1
            ;;
        *)
            print_error "Unsupported OS. Please install Python 3.8+ manually."
            return 1
            ;;
    esac
}

# Function to setup virtual environment
setup_venv() {
    if [ -d "$VENV_DIR" ]; then
        print_status "Virtual environment already exists"
    else
        print_status "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
        print_success "Virtual environment created"
    fi
    
    print_status "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    
    print_status "Upgrading pip..."
    pip install --upgrade pip
    
    if [ -f "$PYTHON_REQUIREMENTS" ]; then
        print_status "Installing Python dependencies..."
        pip install -r "$PYTHON_REQUIREMENTS"
        print_success "Dependencies installed"
    else
        print_warning "requirements.txt not found, installing basic dependencies..."
        pip install httpx aiosqlite matplotlib
        print_success "Basic dependencies installed"
    fi
}

# Function to check GitHub token
check_github_token() {
    if [ -z "$GITHUB_TOKEN" ]; then
        print_warning "GITHUB_TOKEN environment variable not set"
        print_status "You can set it in several ways:"
        echo "  1. Export it: export GITHUB_TOKEN=your_token_here"
        echo "  2. Add to ~/.bashrc: echo 'export GITHUB_TOKEN=your_token_here' >> ~/.bashrc"
        echo "  3. Create .env file: echo 'GITHUB_TOKEN=your_token_here' > .env"
        echo ""
        print_status "Getting a GitHub token:"
        echo "  1. Go to https://github.com/settings/tokens"
        echo "  2. Click 'Generate new token'"
        echo "  3. Select 'repo' scope"
        echo "  4. Copy the token and set it as GITHUB_TOKEN"
        echo ""
        
        read -p "Do you want to continue without a token? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "GitHub token required for full analysis"
            exit 1
        fi
        print_warning "Analysis will be limited without GitHub token"
    else
        print_success "GitHub token found"
    fi
}

# Function to run analysis
run_analysis() {
    print_header "Starting MCP Development Analysis"
    
    if [ ! -f "$ANALYSIS_SCRIPT" ]; then
        print_error "Analysis script not found: $ANALYSIS_SCRIPT"
        exit 1
    fi
    
    print_status "Running comprehensive MCP analysis..."
    python "$ANALYSIS_SCRIPT"
    
    if [ $? -eq 0 ]; then
        print_success "Analysis completed successfully!"
    else
        print_error "Analysis failed"
        exit 1
    fi
}

# Function to show help
show_help() {
    echo "MCP Development Analysis Runner"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -s, --setup    Only setup environment (don't run analysis)"
    echo "  -c, --check    Check environment and dependencies"
    echo "  -t, --token    Show GitHub token setup instructions"
    echo ""
    echo "This script will:"
    echo "  1. Check/install Python 3"
    echo "  2. Setup virtual environment"
    echo "  3. Install dependencies"
    echo "  4. Check GitHub token"
    echo "  5. Run MCP development analysis"
    echo ""
    echo "Environment variables:"
    echo "  GITHUB_TOKEN   GitHub personal access token (optional but recommended)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run full analysis"
    echo "  $0 --setup            # Only setup environment"
    echo "  export GITHUB_TOKEN=xxx && $0  # Run with token"
}

# Function to check environment
check_environment() {
    print_header "Environment Check"
    
    # Check Python
    if command_exists python3; then
        print_success "Python 3: $(python3 --version)"
    else
        print_error "Python 3: Not found"
    fi
    
    # Check virtual environment
    if [ -d "$VENV_DIR" ]; then
        print_success "Virtual environment: Exists"
    else
        print_warning "Virtual environment: Not found"
    fi
    
    # Check GitHub token
    if [ -n "$GITHUB_TOKEN" ]; then
        print_success "GitHub token: Set"
    else
        print_warning "GitHub token: Not set"
    fi
    
    # Check analysis script
    if [ -f "$ANALYSIS_SCRIPT" ]; then
        print_success "Analysis script: Found"
    else
        print_error "Analysis script: Not found"
    fi
}

# Function to show token setup
show_token_setup() {
    print_header "GitHub Token Setup"
    echo "To get the most out of the MCP analysis, you need a GitHub personal access token."
    echo ""
    echo "Steps to create a token:"
    echo "1. Go to https://github.com/settings/tokens"
    echo "2. Click 'Generate new token (classic)'"
    echo "3. Give it a descriptive name (e.g., 'MCP Analysis')"
    echo "4. Select scopes:"
    echo "   - repo (Full control of private repositories)"
    echo "   - read:org (Read organization data)"
    echo "5. Click 'Generate token'"
    echo "6. Copy the token (you won't see it again!)"
    echo ""
    echo "Ways to set the token:"
    echo "1. Temporary (current session):"
    echo "   export GITHUB_TOKEN=your_token_here"
    echo ""
    echo "2. Permanent (add to ~/.bashrc):"
    echo "   echo 'export GITHUB_TOKEN=your_token_here' >> ~/.bashrc"
    echo "   source ~/.bashrc"
    echo ""
    echo "3. Create .env file in this directory:"
    echo "   echo 'GITHUB_TOKEN=your_token_here' > .env"
    echo ""
    echo "Then run: $0"
}

# Main script logic
main() {
    print_header "MCP Development Analysis Runner"
    
    # Parse command line arguments
    case "${1:-}" in
        -h|--help)
            show_help
            exit 0
            ;;
        -s|--setup)
            print_header "Environment Setup Only"
            install_python
            setup_venv
            check_github_token
            print_success "Environment setup complete!"
            exit 0
            ;;
        -c|--check)
            check_environment
            exit 0
            ;;
        -t|--token)
            show_token_setup
            exit 0
            ;;
        "")
            # No arguments, run full analysis
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
    
    # Run full analysis
    print_status "Checking prerequisites..."
    install_python
    setup_venv
    check_github_token
    
    # Load .env file if it exists
    if [ -f ".env" ]; then
        print_status "Loading .env file..."
        export $(cat .env | grep -v '^#' | xargs)
    fi
    
    run_analysis
}

# Run main function
main "$@"
