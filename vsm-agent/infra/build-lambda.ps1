<# 
Build script para empaquetar la Lambda de `vsm-agent` en un zip listo para deploy.

Uso típico (desde la raíz del repo):

    cd vsm-agent\infra
    .\build-lambda.ps1

Genera:  ..\dist\lambda-dev.zip
#>

param(
    [string]$SourceDir = "..",
    [string]$BuildDir = "..\dist\build-agent",
    [string]$OutputZip = "..\dist\lambda-dev.zip"
)

$ErrorActionPreference = "Stop"

# Resolver rutas absolutas
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceDir  = Resolve-Path (Join-Path $scriptPath $SourceDir)
$BuildDir   = Join-Path $scriptPath $BuildDir
$OutputZip  = Join-Path $scriptPath $OutputZip

Write-Host "Building VSM Agent Lambda package..."
Write-Host "Source:  $SourceDir"
Write-Host "Build:   $BuildDir"
Write-Host "Output:  $OutputZip"

# Limpiar y recrear build dir
if (Test-Path $BuildDir) {
    Remove-Item -Path $BuildDir -Recurse -Force
}
New-Item -Path $BuildDir -ItemType Directory -Force | Out-Null

# Copiar archivos necesarios
Write-Host "Copying source code..."

Copy-Item -Path (Join-Path $SourceDir "handler.py") -Destination $BuildDir -Force
Copy-Item -Path (Join-Path $SourceDir "router.py")  -Destination $BuildDir -Force

Copy-Item -Path (Join-Path $SourceDir "models")     -Destination $BuildDir -Recurse -Force
Copy-Item -Path (Join-Path $SourceDir "services")   -Destination $BuildDir -Recurse -Force
Copy-Item -Path (Join-Path $SourceDir "agent_core") -Destination $BuildDir -Recurse -Force

# Limpiar artefactos innecesarios
Write-Host "Cleaning build directory..."
Get-ChildItem -Path $BuildDir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $BuildDir -Recurse -File -Filter "*.pyc"            | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $BuildDir -Recurse -Directory -Filter "*.dist-info" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $BuildDir -Recurse -Directory -Filter "tests"       | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 1

# Crear zip usando tar.exe (evita muchos problemas de locking de Compress-Archive)
Write-Host "Creating zip package with tar..."
if (Test-Path $OutputZip) {
    Remove-Item -Path $OutputZip -Force
}

Push-Location $BuildDir
try {
    tar -a -c -f $OutputZip *  # Crea un .zip con el contenido del build dir en la raíz del paquete
    Write-Host "Build complete: $OutputZip"
} catch {
    Write-Error "Error creating zip package: $_"
    Write-Host "Build directory is ready at: $BuildDir"
    exit 1
} finally {
    Pop-Location
}

