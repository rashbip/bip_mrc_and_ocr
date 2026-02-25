import subprocess
import os
import sys
import shutil
from pathlib import Path

VENV_PYTHON = "/home/biplob/pdf_pipeline_venv/bin/python3"
RECODE_PDF  = "/home/biplob/pdf_pipeline_venv/bin/recode_pdf"

def run_command(cmd, log_output=True):
    if log_output:
        print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if log_output:
            print(f"Error: {result.stderr}")
        return False, result.stderr
    return True, result.stdout

def ocr_mrc_pipeline(input_pdf, output_pdf, lang="eng+ben"):
    input_path  = Path(input_pdf).resolve()
    output_path = Path(output_pdf).resolve()

    # Temporary directory for processing
    temp_dir = output_path.parent / f"work_{input_path.stem}"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("Error: PyMuPDF (fitz) not found in WSL environment.")
        sys.exit(1)

    print(f"\n--- Starting Per-Page Pipeline for {input_path.name} ---")
    
    doc = fitz.open(str(input_path))
    total_pages = len(doc)
    page_pdfs = []

    for i in range(total_pages):
        page_num = i + 1
        print(f"\n--- Processing Page {page_num}/{total_pages} ---")
        
        # 1. Extract page as high-quality JPEG (lighter than PNG)
        page = doc[i]
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
        img_path = temp_dir / f"page_{page_num:04d}.jpg"
        pix.save(str(img_path))
        print(f"  [1/4] Extracted image: {img_path.name}")

        # 2. OCR → hOCR
        hocr_base = temp_dir / f"page_{page_num:04d}"
        hocr_file = temp_dir / f"page_{page_num:04d}.hocr"
        success, err = run_command(["tesseract", str(img_path), str(hocr_base), "-l", lang, "hocr"])
        if not success:
            print(f"  [ERROR] OCR failed for page {page_num}: {err}")
            continue
        print(f"  [2/4] Generated hOCR: {hocr_file.name}")

        # 3. Recode single page with MRC
        page_pdf_out = temp_dir / f"mrc_{page_num:04d}.pdf"
        # Using -P (PDF) might be better if we have the original, but we want to compress the image.
        # archive-pdf-tools' recode_pdf -I with a single file works if we pass it correctly.
        # Based on previous failure with directory, let's try passing the image file directly.
        
        # We use -I for imagestack (a single image works as a stack of 1)
        # We need to make sure we don't pass a directory but the actual file.
        success, err = run_command([
            RECODE_PDF,
            "-I", str(img_path),
            "-T", str(hocr_file),
            "-o", str(page_pdf_out),
            "-m", "2"  # MRC mode
        ])
        
        if not success:
            print(f"  [ERROR] MRC Recoding failed for page {page_num}: {err}")
            # Fallback: create a basic searchable PDF if recoding fails? 
            # For now, we skip to avoid breaking the merge.
            continue
            
        print(f"  [3/4] Created MRC PDF: {page_pdf_out.name}")
        page_pdfs.append(str(page_pdf_out))

    doc.close()

    if not page_pdfs:
        print("\n[ERROR] No pages were successfully processed.")
        sys.exit(1)

    # 4. Merge all single-page PDFs
    print(f"\n--- Step 4: Merging {len(page_pdfs)} pages into final PDF ---")
    out_doc = fitz.open()
    for p_pdf in page_pdfs:
        with fitz.open(p_pdf) as p_doc:
            out_doc.insert_pdf(p_doc)
    
    out_doc.save(str(output_path))
    out_doc.close()

    print(f"\n--- Pipeline Complete! ---")
    print(f"  Final PDF: {output_path}")

    # Cleanup
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 mrc_ocr_pipeline.py <input.pdf> <output.pdf> [--enonly]")
        sys.exit(1)

    input_pdf  = sys.argv[1]
    output_pdf = sys.argv[2]
    lang = "eng" if "--enonly" in sys.argv else "eng+ben"

    if not os.path.exists(input_pdf):
        print(f"File not found: {input_pdf}")
        sys.exit(1)

    ocr_mrc_pipeline(input_pdf, output_pdf, lang=lang)
