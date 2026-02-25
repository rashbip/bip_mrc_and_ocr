# install_globally.ps1 - Compile and install bipmrcocr globally on Windows

$ErrorActionPreference = "Stop"

$ProjectDir = Get-Location
$WrapperFile = "bipmrcocr_wrapper.py"
$InstallDir = Join-Path $HOME ".bipmrcocr"
$ExeName = "bipmrcocr.exe"

Write-Host "--- Starting Global Installation of bipmrcocr ---" -ForegroundColor Cyan

# 1. Check for PyInstaller
if (!(Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "PyInstaller not found in PATH. Attempting to run via python -m PyInstaller..." -ForegroundColor Yellow
    $PyInstallerCmd = "python -m PyInstaller"
} else {
    $PyInstallerCmd = "pyinstaller"
}

# 2. Compile Wrapper to EXE
Write-Host "Compiling $WrapperFile to EXE..." -ForegroundColor Blue
Invoke-Expression "$PyInstallerCmd --onefile --name bipmrcocr --distpath . $WrapperFile"

if (!(Test-Path $ExeName)) {
    Write-Host "Error: Compilation failed. $ExeName not found." -ForegroundColor Red
    exit 1
}

# 3. Setup Install Directory
if (!(Test-Path $InstallDir)) {
    Write-Host "Creating installation directory at $InstallDir..." -ForegroundColor Blue
    New-Item -ItemType Directory -Path $InstallDir | Out-Null
}

# 4. Move EXE to Install Directory
Write-Host "Installing EXE to $InstallDir..." -ForegroundColor Blue
Move-Item -Path $ExeName -Destination (Join-Path $InstallDir $ExeName) -Force

# 5. Add to User PATH
Write-Host "Adding $InstallDir to User PATH..." -ForegroundColor Blue
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$InstallDir*") {
    $NewPath = "$UserPath;$InstallDir"
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    Write-Host "PATH updated successfully. You will need to RESTART your terminal to see the changes." -ForegroundColor Green
} else {
    Write-Host "$InstallDir is already in PATH." -ForegroundColor Green
}

Write-Host "`n--- Installation Complete! ---" -ForegroundColor Green
Write-Host "You can now run 'bipmrcocr <pdf_path>' from any new terminal." -ForegroundColor Cyan
Write-Host "Note: File paths with spaces should be quoted."
