import subprocess
import sys
import os
from pathlib import Path

def win_to_wsl_path(win_path):
    """Convert a Windows path to a WSL path (e.g., C:\foo\bar -> /mnt/c/foo/bar)."""
    p = Path(win_path).resolve()
    drive = p.drive.replace(":", "").lower()
    # Path.parts[0] is the drive ('C:\\'), rest are folders
    rest = "/".join(p.parts[1:]).replace("\\", "/")
    return f"/mnt/{drive}/{rest}"

def is_ubuntu_installed():
    """Check if WSL Ubuntu distribution is installed. Handles UTF-16 output."""
    result = subprocess.run(["wsl", "--list", "--quiet"], capture_output=True)
    # wsl --list outputs UTF-16LE on Windows
    try:
        text = result.stdout.decode("utf-16-le", errors="ignore")
    except Exception:
        text = result.stdout.decode("utf-8", errors="ignore")
    return "ubuntu" in text.lower()

def ensure_wsl_environment():
    """Ensure WSL Ubuntu is installed and the pipeline environment is ready."""
    print("[bipmrcocr] Checking WSL Ubuntu environment...")

    if not is_ubuntu_installed():
        print("[bipmrcocr] Ubuntu not found. Installing WSL Ubuntu (this may take a few minutes)...")
        result = subprocess.run(["wsl", "--install", "-d", "Ubuntu"])
        if result.returncode != 0:
            print("[bipmrcocr] Error: Failed to install WSL Ubuntu.")
            print("  Please run manually: wsl --install -d Ubuntu")
            sys.exit(1)
        print("[bipmrcocr] Ubuntu installed. Please finish the user setup in the Ubuntu window, then re-run bipmrcocr.")
        sys.exit(0)

    print("[bipmrcocr] Ubuntu is installed. Verifying pipeline dependencies...")
    project_dir_wsl = win_to_wsl_path(r"d:\Python\bipmrcocrwin")
    # Run robust_setup.sh - it is idempotent and skips already-installed items
    result = subprocess.run(
        ["wsl", "-d", "Ubuntu", "bash", "-c", f"cd '{project_dir_wsl}' && bash ./robust_setup.sh"]
    )
    if result.returncode != 0:
        print("[bipmrcocr] Error: Environment setup failed. Check the output above.")
        sys.exit(1)
    print("[bipmrcocr] Environment is ready.")

def main():
    if len(sys.argv) < 2:
        print("Usage: bipmrcocr <input.pdf>")
        print("  Output: <input>_bip.pdf saved in the same folder.")
        sys.exit(0)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"[bipmrcocr] Error: File not found: {input_file}")
        sys.exit(1)

    input_path = Path(input_file).resolve()
    output_path = input_path.with_name(f"{input_path.stem}_bip{input_path.suffix}")

    en_only = "--enonly" in sys.argv
    lang_str = "English only" if en_only else "English + Bengali"
    print(f"[bipmrcocr] Input:  {input_path}")
    print(f"[bipmrcocr] Output: {output_path}")
    print(f"[bipmrcocr] OCR Language: {lang_str}")

    ensure_wsl_environment()

    # Convert paths to WSL format
    input_wsl  = win_to_wsl_path(str(input_path))
    output_wsl = win_to_wsl_path(str(output_path))
    project_dir_wsl = win_to_wsl_path(r"d:\Python\bipmrcocrwin")

    venv_python     = "/home/biplob/pdf_pipeline_venv/bin/python3"
    pipeline_script = f"{project_dir_wsl}/mrc_ocr_pipeline.py"

    enonly_flag = "--enonly" if en_only else ""
    print("\n[bipmrcocr] --- Running OCR + MRC pipeline ---")
    result = subprocess.run(
        ["wsl", "-d", "Ubuntu", "bash", "-c",
         f"{venv_python} '{pipeline_script}' '{input_wsl}' '{output_wsl}' {enonly_flag}"]
    )

    if result.returncode == 0:
        print(f"\n[bipmrcocr] Done! Output saved to:\n  {output_path}")
    else:
        print("\n[bipmrcocr] Pipeline failed. See output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
