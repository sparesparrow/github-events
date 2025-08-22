# MCP Development Analysis Runner (PowerShell)
# This script provides an easy way to analyze MCP development trends
# with minimal setup requirements.

param(
    [switch]$Help,
    [switch]$Setup,
    [switch]$Check,
    [switch]$Token
)

# Script configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ScriptDir ".venv"
$PythonRequirements = Join-Path $ScriptDir "requirements.txt"
$AnalysisScript = Join-Path $ScriptDir "comprehensive_mcp_analysis.py"

# Function to write colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Header {
    param([string]$Message)
    Write-Host "================================" -ForegroundColor Magenta
    Write-Host $Message -ForegroundColor Magenta
    Write-Host "================================" -ForegroundColor Magenta
}

# Function to check if command exists
function Test-Command {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Function to detect OS
function Get-OS {
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        return "windows"
    }
    elseif ($IsLinux) {
        return "linux"
    }
    elseif ($IsMacOS) {
        return "macos"
    }
    else {
        return "unknown"
    }
}

# Function to install Python if needed
function Install-Python {
    $os = Get-OS
    Write-Status "Detected OS: $os"
    
    # Check for Python 3
    if (Test-Command "python3") {
        $version = python3 --version 2>&1
        Write-Success "Python 3 found: $version"
        return $true
    }
    elseif (Test-Command "python") {
        $version = python --version 2>&1
        if ($version -match "Python 3") {
            Write-Success "Python 3 found: $version"
            return $true
        }
    }
    
    Write-Warning "Python 3 not found. Attempting to install..."
    
    switch ($os) {
        "windows" {
            Write-Error "Please install Python 3.8+ from https://python.org"
            Write-Status "Or use winget: winget install Python.Python.3.11"
            return $false
        }
        "linux" {
            if (Test-Command "apt-get") {
                Write-Status "Installing Python 3 via apt-get..."
                sudo apt-get update
                sudo apt-get install -y python3 python3-pip python3-venv
            }
            elseif (Test-Command "yum") {
                Write-Status "Installing Python 3 via yum..."
                sudo yum install -y python3 python3-pip
            }
            elseif (Test-Command "dnf") {
                Write-Status "Installing Python 3 via dnf..."
                sudo dnf install -y python3 python3-pip
            }
            else {
                Write-Error "Could not install Python 3 automatically. Please install Python 3.8+ manually."
                return $false
            }
        }
        "macos" {
            if (Test-Command "brew") {
                Write-Status "Installing Python 3 via Homebrew..."
                brew install python3
            }
            else {
                Write-Error "Homebrew not found. Please install Python 3.8+ manually or install Homebrew first."
                return $false
            }
        }
        default {
            Write-Error "Unsupported OS. Please install Python 3.8+ manually."
            return $false
        }
    }
    
    return $true
}

# Function to setup virtual environment
function Setup-Venv {
    if (Test-Path $VenvDir) {
        Write-Status "Virtual environment already exists"
    }
    else {
        Write-Status "Creating virtual environment..."
        python3 -m venv $VenvDir
        Write-Success "Virtual environment created"
    }
    
    Write-Status "Activating virtual environment..."
    & "$VenvDir\Scripts\Activate.ps1"
    
    Write-Status "Upgrading pip..."
    python -m pip install --upgrade pip
    
    if (Test-Path $PythonRequirements) {
        Write-Status "Installing Python dependencies..."
        pip install -r $PythonRequirements
        Write-Success "Dependencies installed"
    }
    else {
        Write-Warning "requirements.txt not found, installing basic dependencies..."
        pip install httpx aiosqlite matplotlib
        Write-Success "Basic dependencies installed"
    }
}

# Function to check GitHub token
function Test-GitHubToken {
    if (-not $env:GITHUB_TOKEN) {
        Write-Warning "GITHUB_TOKEN environment variable not set"
        Write-Status "You can set it in several ways:"
        Write-Host "  1. Set for current session: `$env:GITHUB_TOKEN = 'your_token_here'"
        Write-Host "  2. Add to PowerShell profile: Add-Content `$PROFILE '`$env:GITHUB_TOKEN = \"your_token_here\"'"
        Write-Host "  3. Create .env file: 'GITHUB_TOKEN=your_token_here' | Out-File .env"
        Write-Host ""
        Write-Status "Getting a GitHub token:"
        Write-Host "  1. Go to https://github.com/settings/tokens"
        Write-Host "  2. Click 'Generate new token (classic)'"
        Write-Host "  3. Select 'repo' scope"
        Write-Host "  4. Copy the token and set it as GITHUB_TOKEN"
        Write-Host ""
        
        $response = Read-Host "Do you want to continue without a token? (y/N)"
        if ($response -notmatch "^[Yy]$") {
            Write-Error "GitHub token required for full analysis"
            exit 1
        }
        Write-Warning "Analysis will be limited without GitHub token"
    }
    else {
        Write-Success "GitHub token found"
    }
}

# Function to run analysis
function Start-Analysis {
    Write-Header "Starting MCP Development Analysis"
    
    if (-not (Test-Path $AnalysisScript)) {
        Write-Error "Analysis script not found: $AnalysisScript"
        exit 1
    }
    
    Write-Status "Running comprehensive MCP analysis..."
    python $AnalysisScript
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Analysis completed successfully!"
    }
    else {
        Write-Error "Analysis failed"
        exit 1
    }
}

# Function to show help
function Show-Help {
    Write-Host "MCP Development Analysis Runner" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\run_mcp_analysis.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Help     Show this help message"
    Write-Host "  -Setup    Only setup environment (don't run analysis)"
    Write-Host "  -Check    Check environment and dependencies"
    Write-Host "  -Token    Show GitHub token setup instructions"
    Write-Host ""
    Write-Host "This script will:"
    Write-Host "  1. Check/install Python 3"
    Write-Host "  2. Setup virtual environment"
    Write-Host "  3. Install dependencies"
    Write-Host "  4. Check GitHub token"
    Write-Host "  5. Run MCP development analysis"
    Write-Host ""
    Write-Host "Environment variables:"
    Write-Host "  GITHUB_TOKEN   GitHub personal access token (optional but recommended)"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\run_mcp_analysis.ps1                    # Run full analysis"
    Write-Host "  .\run_mcp_analysis.ps1 -Setup             # Only setup environment"
    Write-Host "  `$env:GITHUB_TOKEN='xxx'; .\run_mcp_analysis.ps1  # Run with token"
}

# Function to check environment
function Test-Environment {
    Write-Header "Environment Check"
    
    # Check Python
    if (Test-Command "python3") {
        $version = python3 --version 2>&1
        Write-Success "Python 3: $version"
    }
    else {
        Write-Error "Python 3: Not found"
    }
    
    # Check virtual environment
    if (Test-Path $VenvDir) {
        Write-Success "Virtual environment: Exists"
    }
    else {
        Write-Warning "Virtual environment: Not found"
    }
    
    # Check GitHub token
    if ($env:GITHUB_TOKEN) {
        Write-Success "GitHub token: Set"
    }
    else {
        Write-Warning "GitHub token: Not set"
    }
    
    # Check analysis script
    if (Test-Path $AnalysisScript) {
        Write-Success "Analysis script: Found"
    }
    else {
        Write-Error "Analysis script: Not found"
    }
}

# Function to show token setup
function Show-TokenSetup {
    Write-Header "GitHub Token Setup"
    Write-Host "To get the most out of the MCP analysis, you need a GitHub personal access token."
    Write-Host ""
    Write-Host "Steps to create a token:"
    Write-Host "1. Go to https://github.com/settings/tokens"
    Write-Host "2. Click 'Generate new token (classic)'"
    Write-Host "3. Give it a descriptive name (e.g., 'MCP Analysis')"
    Write-Host "4. Select scopes:"
    Write-Host "   - repo (Full control of private repositories)"
    Write-Host "   - read:org (Read organization data)"
    Write-Host "5. Click 'Generate token'"
    Write-Host "6. Copy the token (you won't see it again!)"
    Write-Host ""
    Write-Host "Ways to set the token:"
    Write-Host "1. Temporary (current session):"
    Write-Host "   `$env:GITHUB_TOKEN = 'your_token_here'"
    Write-Host ""
    Write-Host "2. Permanent (add to PowerShell profile):"
    Write-Host "   Add-Content `$PROFILE '`$env:GITHUB_TOKEN = \"your_token_here\"'"
    Write-Host "   . `$PROFILE"
    Write-Host ""
    Write-Host "3. Create .env file in this directory:"
    Write-Host "   'GITHUB_TOKEN=your_token_here' | Out-File .env"
    Write-Host ""
    Write-Host "Then run: .\run_mcp_analysis.ps1"
}

# Function to load .env file
function Load-EnvFile {
    $envFile = Join-Path $ScriptDir ".env"
    if (Test-Path $envFile) {
        Write-Status "Loading .env file..."
        Get-Content $envFile | ForEach-Object {
            if ($_ -match "^([^#][^=]+)=(.*)$") {
                $name = $matches[1].Trim()
                $value = $matches[2].Trim()
                Set-Item -Path "env:$name" -Value $value
            }
        }
    }
}

# Main script logic
function Main {
    Write-Header "MCP Development Analysis Runner"
    
    # Parse command line arguments
    if ($Help) {
        Show-Help
        return
    }
    elseif ($Setup) {
        Write-Header "Environment Setup Only"
        Install-Python
        Setup-Venv
        Test-GitHubToken
        Write-Success "Environment setup complete!"
        return
    }
    elseif ($Check) {
        Test-Environment
        return
    }
    elseif ($Token) {
        Show-TokenSetup
        return
    }
    
    # Run full analysis
    Write-Status "Checking prerequisites..."
    Install-Python
    Setup-Venv
    Test-GitHubToken
    
    # Load .env file if it exists
    Load-EnvFile
    
    Start-Analysis
}

# Run main function
Main
