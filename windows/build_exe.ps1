# build_exe.ps1 - Compile the bipmrcocr wrapper to a standalone EXE

$ProjectDir = Get-Location
$WrapperFile = "windows\bipmrcocr_wrapper.py"
$DistDir = "dist"

Write-Host "--- Building bipmrcocr.exe ---" -ForegroundColor Cyan

if (!(Test-Path $WrapperFile)) {
    Write-Host "Error: Wrapper file not found at $WrapperFile" -ForegroundColor Red
    exit 1
}

# Check for PyInstaller
if (!(Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "PyInstaller not found. Installing..." -ForegroundColor Yellow
    pip install pyinstaller
}

Write-Host "Compiling to EXE..." -ForegroundColor Blue
pyinstaller --onefile --name bipmrcocr --distpath $DistDir $WrapperFile

if (Test-Path "$DistDir\bipmrcocr.exe") {
    Write-Host "`nSuccessfully built: $DistDir\bipmrcocr.exe" -ForegroundColor Green
} else {
    Write-Host "`nBuild failed!" -ForegroundColor Red
}
