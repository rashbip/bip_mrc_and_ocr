import os
import subprocess
import shutil
import tempfile
import argparse
import sys
import glob

def run_command(cmd, shell=False):
    """Utility to run a command and handle errors."""
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        # We use list form for security, but allow shell if globbing is needed
        process = subprocess.run(cmd, check=True, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if process.stdout:
            print(process.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        if e.output:
            print(f"Command output: {e.output}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Automated MRC Compression Pipeline (Archive.org style)")
    parser.add_argument("input_pdf", help="Path to the source PDF file")
    parser.add_argument("output_pdf", help="Path for the compressed output PDF")
    parser.add_argument("--lang", default="eng", help="OCR Language (e.g., 'eng', 'ben', 'eng+ben')")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for the output PDF (default: 300)")
    parser.add_argument("--downsample", type=int, default=3, help="Background downsample factor (default: 3)")
    parser.add_argument("--keep-tmp", action="store_true", help="Keep temporary files for debugging")
    
    args = parser.parse_args()

    # 1. Verification of tools
    tools = ['recode_pdf', 'tesseract', 'pdfimages', 'jbig2']
    missing = [t for t in tools if not shutil.which(t)]
    if missing:
        print(f"Error: Missing required tools: {', '.join(missing)}")
        print("Please ensure Poppler-utils, Tesseract, and archive-pdf-tools are installed.")
        sys.exit(1)

    # 2. Setup Workspace
    tmp_base = tempfile.mkdtemp(prefix="mrc_")
    print(f"Created temporary workspace: {tmp_base}")
    
    try:
        img_dir = os.path.join(tmp_base, "images")
        os.makedirs(img_dir)
        
        # 3. Extract Images
        # Note: pdfimages -all -png extracts images with a prefix
        print("\n--- Step 1: Extracting images from PDF ---")
        img_prefix = os.path.join(img_dir, "page")
        run_command(['pdfimages', '-all', '-png', args.input_pdf, img_prefix])
        
        # Get list of images and sort them numerically
        # pdfimages uses -000, -001, etc.
        images = sorted(glob.glob(os.path.join(img_dir, "page-*")))
        if not images:
            print("No images found in PDF. Make sure it's a scanned PDF or contains images.")
            sys.exit(1)
        
        print(f"Extracted {len(images)} image parts.")
        
        # 4. Generate Batch OCR (hOCR)
        print("\n--- Step 2: Running Tesseract OCR (Batch) ---")
        list_file = os.path.join(tmp_base, "images_list.txt")
        with open(list_file, "w") as f:
            for img in images:
                f.write(f"{img}\n")
        
        hocr_base = os.path.join(tmp_base, "output")
        # Tesseract returns .hocr extension automatically
        run_command(['tesseract', list_file, hocr_base, '-l', args.lang, 'hocr'])
        hocr_file = f"{hocr_base}.hocr"
        
        if not os.path.exists(hocr_file):
            print(f"Error: hOCR file was not generated at {hocr_file}")
            sys.exit(1)
        
        # 5. MRC Compression
        print("\n--- Step 3: Performing MRC Compression via recode_pdf ---")
        # recode_pdf --from-imagestack takes a shell glob string
        # We need to use shell=True for the glob to be expanded by the shell or pass it as a string
        # Actually recode_pdf handles the glob itself if passed as a string with *
        recode_cmd = [
            'recode_pdf',
            '--from-imagestack', os.path.join(img_dir, "page-*"),
            '--hocr-file', hocr_file,
            '--dpi', str(args.dpi),
            '--bg-downsample', str(args.downsample),
            '--mask-compression', 'jbig2',
            '-J', 'openjpeg',
            '-o', args.output_pdf
        ]
        run_command(recode_cmd)
        
        print(f"\nSuccess! Compressed PDF saved to: {args.output_pdf}")
        
    finally:
        if not args.keep_tmp:
            print(f"Cleaning up {tmp_base}...")
            shutil.rmtree(tmp_base)
        else:
            print(f"Temporary files kept at: {tmp_base}")

if __name__ == "__main__":
    main()
