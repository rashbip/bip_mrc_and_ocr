import subprocess
import os
import sys
import shutil
import concurrent.futures
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

def process_page(page_data):
    """Worker function to process a single page: OCR + MRC."""
    page_num, img_path, temp_dir, lang = page_data
    
    # 2. OCR → hOCR
    hocr_base = temp_dir / f"page_{page_num:04d}"
    hocr_file = temp_dir / f"page_{page_num:04d}.hocr"
    success, err = run_command(["tesseract", str(img_path), str(hocr_base), "-l", lang, "hocr"], log_output=False)
    if not success:
        return None, f"OCR failed for page {page_num}: {err}"

    # 3. Recode single page with MRC
    page_pdf_out = temp_dir / f"mrc_{page_num:04d}.pdf"
    success, err = run_command([
        RECODE_PDF,
        "-I", str(img_path),
        "-T", str(hocr_file),
        "-o", str(page_pdf_out),
        "-m", "2"  # MRC mode
    ], log_output=False)
    
    if not success:
        return None, f"MRC Recoding failed for page {page_num}: {err}"
        
    return str(page_pdf_out), None

def ocr_mrc_pipeline(input_pdf, output_pdf, lang="eng+ben", threads=None):
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

    print(f"\n--- Starting Parallel Pipeline for {input_path.name} ---")
    
    doc = fitz.open(str(input_path))
    total_pages = len(doc)
    
    # ── Step 1: Extract all pages as JPEGs (Sequential) ────────────────────
    print(f"--- Step 1: Extracting {total_pages} pages ---")
    page_tasks = []
    for i in range(total_pages):
        page_num = i + 1
        page = doc[i]
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
        img_path = temp_dir / f"page_{page_num:04d}.jpg"
        pix.save(str(img_path))
        page_tasks.append((page_num, img_path, temp_dir, lang))
    doc.close()
    print("  All pages extracted.")

    # ── Step 2 & 3: Parallel OCR + MRC ─────────────────────────────────────
    print(f"--- Step 2 & 3: Processing pages in parallel ({threads or 'auto'} threads) ---")
    page_pdfs = [None] * total_pages
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        future_to_page = {executor.submit(process_page, task): task[0] for task in page_tasks}
        for future in concurrent.futures.as_completed(future_to_page):
            page_num = future_to_page[future]
            try:
                pdf_path, error = future.result()
                if error:
                    print(f"  [Error] Page {page_num}: {error}")
                else:
                    page_pdfs[page_num-1] = pdf_path
                    print(f"  [Done] Page {page_num}/{total_pages}")
            except Exception as exc:
                print(f"  [Exception] Page {page_num} generated an exception: {exc}")

    # Filter out failed pages
    valid_pdfs = [p for p in page_pdfs if p is not None]

    if not valid_pdfs:
        print("\n[ERROR] No pages were successfully processed.")
        sys.exit(1)

    # ── Step 4: Merge ──────────────────────────────────────────────────────
    print(f"--- Step 4: Merging {len(valid_pdfs)} pages ---")
    out_doc = fitz.open()
    for p_pdf in valid_pdfs:
        with fitz.open(p_pdf) as p_doc:
            out_doc.insert_pdf(p_doc)
    
    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            out_doc.save(str(output_path))
            break
        except Exception as e:
            if "Permission denied" in str(e) or "cannot remove file" in str(e):
                if attempt < max_retries - 1:
                    print(f"  [Warning] Output file is locked. Please close it. Retrying in 3s... ({attempt+1}/{max_retries})")
                    time.sleep(3)
                else:
                    print(f"\n[ERROR] Could not save final PDF. Is it open in another program?\n  {e}")
                    sys.exit(1)
            else:
                raise e
    out_doc.close()

    print(f"\n--- Pipeline Complete! ---")
    print(f"  Final PDF: {output_path}")

    # Cleanup
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 mrc_ocr_pipeline.py <input.pdf> <output.pdf> [--enonly] [--threads N]")
        sys.exit(1)

    input_pdf  = sys.argv[1]
    output_pdf = sys.argv[2]
    lang = "eng" if "--enonly" in sys.argv else "eng+ben"
    
    threads = None
    if "--threads" in sys.argv:
        idx = sys.argv.index("--threads")
        if len(sys.argv) > idx + 1:
            try:
                threads = int(sys.argv[idx + 1])
            except ValueError:
                pass

    if not os.path.exists(input_pdf):
        print(f"File not found: {input_pdf}")
        sys.exit(1)

    ocr_mrc_pipeline(input_pdf, output_pdf, lang=lang, threads=threads)
