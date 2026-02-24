# Build script for Lambda package with dependencies
param(
    [string]$SourceDir = "..\src",
    [string]$RequirementsFile = "..\requirements-lambda.txt",
    [string]$BuildDir = "..\dist\build",
    [string]$OutputZip = "..\dist\lambda-dev.zip"
)

$ErrorActionPreference = "Stop"

# Resolve paths to absolute
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceDir = Resolve-Path (Join-Path $scriptPath $SourceDir)
$RequirementsFile = Resolve-Path (Join-Path $scriptPath $RequirementsFile)
$BuildDir = Join-Path $scriptPath $BuildDir
$OutputZip = Join-Path $scriptPath $OutputZip

Write-Host "Building Lambda package..."
Write-Host "Source: $SourceDir"
Write-Host "Requirements: $RequirementsFile"
Write-Host "Build: $BuildDir"
Write-Host "Output: $OutputZip"

# Clean build directory
if (Test-Path $BuildDir) {
    Remove-Item -Path $BuildDir -Recurse -Force
}
New-Item -Path $BuildDir -ItemType Directory -Force | Out-Null

# Copy source code
Write-Host "Copying source code..."
Copy-Item -Path "$SourceDir\*" -Destination $BuildDir -Recurse -Force

# Find Python executable (avoid Windows Store stub)
$pythonExe = $null
$possiblePaths = @(
    "$env:LOCALAPPDATA\Python\bin\python.exe",
    "$env:ProgramFiles\Python*\python.exe",
    "C:\Python*\python.exe"
)

foreach ($path in $possiblePaths) {
    $found = Get-ChildItem -Path $path -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) {
        $pythonExe = $found.FullName
        break
    }
}

# Try Get-Command as fallback, but filter out Windows Store stub
if (-not $pythonExe) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd -and $pythonCmd.Source -notlike "*WindowsApps*") {
        $pythonExe = $pythonCmd.Source
    }
}

if (-not $pythonExe) {
    Write-Error "Python not found. Please ensure Python is installed and in PATH."
    exit 1
}
Write-Host "Using Python: $pythonExe"

# Install dependencies
Write-Host "Installing dependencies..."
$ErrorActionPreference = "Continue"
& $pythonExe -m pip install -r $RequirementsFile -t $BuildDir --upgrade
if ($LASTEXITCODE -ne 0) {
    Write-Error "pip install failed with exit code $LASTEXITCODE"
    exit 1
}
$ErrorActionPreference = "Stop"
Write-Host "Dependencies installed successfully"

# Remove unnecessary files
Write-Host "Cleaning up..."
Get-ChildItem -Path $BuildDir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $BuildDir -Recurse -File -Filter "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $BuildDir -Recurse -Directory -Filter "*.dist-info" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $BuildDir -Recurse -Directory -Filter "tests" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Create zip file (Terraform will handle this, but we'll try anyway)
Write-Host "Waiting for file handles to release..."
Start-Sleep -Seconds 2

Write-Host "Creating zip package..."
if (Test-Path $OutputZip) {
    Remove-Item -Path $OutputZip -Force
}

try {
    Compress-Archive -Path "$BuildDir\*" -DestinationPath $OutputZip -Force -ErrorAction Stop
    Write-Host "Build complete: $OutputZip"
} catch {
    Write-Host "Warning: Could not create zip file (Terraform will create it): $_"
    Write-Host "Build directory ready: $BuildDir"
}

