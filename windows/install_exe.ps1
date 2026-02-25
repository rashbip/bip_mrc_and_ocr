# install_exe.ps1 - Install the built bipmrcocr.exe globally

$ExePath = "dist\bipmrcocr.exe"
$InstallDir = Join-Path $HOME ".bipmrcocr"

Write-Host "--- Installing bipmrcocr globally ---" -ForegroundColor Cyan

if (!(Test-Path $ExePath)) {
    Write-Host "Error: Executable not found at $ExePath. Run build_exe.ps1 first." -ForegroundColor Red
    exit 1
}

if (!(Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir | Out-Null
}

Copy-Item -Path $ExePath -Destination (Join-Path $InstallDir "bipmrcocr.exe") -Force
Write-Host "Installed to $InstallDir\bipmrcocr.exe" -ForegroundColor Green

# Update PATH
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$InstallDir*") {
    $NewPath = "$UserPath;$InstallDir"
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    Write-Host "PATH updated. Restart your terminal to use 'bipmrcocr' globally." -ForegroundColor Yellow
} else {
    Write-Host "PATH already includes the installation directory." -ForegroundColor Green
}
