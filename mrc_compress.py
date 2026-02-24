import os
import subprocess
import shutil
import tempfile
import argparse
import sys
import glob
import threading
import queue
import re
from tkinter import filedialog, ttk, messagebox
import tkinter as tk
from typing import Any, Dict, Optional, List, Callable

def run_command(cmd: List[str], shell: bool = False, progress_callback: Optional[Callable[[str], None]] = None):
    """Utility to run a command and handle errors with optional incremental feedback."""
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            shell=shell,
            bufsize=1,
            universal_newlines=True
        )
        
        stdout = process.stdout
        if stdout is not None:
            for line in stdout:
                line_str = line.strip()
                if line_str:
                    print(line_str)
                    cb = progress_callback
                    if cb is not None:
                        cb(line_str)
        
        return_code = process.wait()
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, cmd)
            
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        raise

class ProgressWindow(tk.Toplevel):
    def __init__(self, parent, title="Processing..."):
        super().__init__(parent)
        self.title(title)
        self.geometry("450x200")
        self.protocol("WM_DELETE_WINDOW", lambda: None) # Disable close
        self.transient(parent)
        self.grab_set()
        
        self.status_label = ttk.Label(self, text="Preparing...", font=('Helvetica', 10))
        self.status_label.pack(pady=(30, 10), padx=20, anchor=tk.W)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=20, pady=10)
        
        self.sub_status_label = ttk.Label(self, text="", font=('Helvetica', 9), foreground="gray")
        self.sub_status_label.pack(padx=20, anchor=tk.W)
        
        self.center_window()

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def update_status(self, text, progress=None, sub_text=None):
        self.status_label.config(text=text)
        if progress is not None:
            self.progress_var.set(progress)
        if sub_text is not None:
            self.sub_status_label.config(text=sub_text)
        self.update()

class MRCSettingsWindow(tk.Tk):
    def __init__(self, defaults: Dict[str, Any]):
        super().__init__()
        self.title("MRC Compression Settings")
        self.geometry("400x520")
        self.result: Optional[Dict[str, Any]] = None
        
        # Bring to front
        self.lift()
        self.attributes('-topmost', True)
        
        def _clear_topmost(*args: Any) -> None:
            self.attributes('-topmost', False)
        
        self.after(200, _clear_topmost)
        self.focus_force()

        # Vars
        self.lang_var = tk.StringVar(value=defaults.get('lang', 'eng+ben'))
        self.dpi_var = tk.StringVar(value=str(defaults.get('dpi', 400)))
        self.downsample_var = tk.StringVar(value=str(defaults.get('downsample', 3)))
        self.mrc_preset_var = tk.StringVar(value=str(defaults.get('mrc_preset', 2)))
        self.threshold_var = tk.StringVar(value=str(defaults.get('threshold', 10)))
        self.sauvola_var = tk.BooleanVar(value=defaults.get('sauvola', True))
        self.twopass_var = tk.BooleanVar(value=defaults.get('twopass', False))

        # Layout
        frame = ttk.Frame(self, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="OCR Language (e.g. eng+ben):", font=('Helvetica', 10, 'bold')).pack(anchor=tk.W, pady=(5,0))
        ttk.Entry(frame, textvariable=self.lang_var).pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Output DPI (Archive uses 400):", font=('Helvetica', 10, 'bold')).pack(anchor=tk.W, pady=(5,0))
        ttk.Entry(frame, textvariable=self.dpi_var).pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="BG Downsample (1-4):", font=('Helvetica', 10, 'bold')).pack(anchor=tk.W, pady=(5,0))
        ttk.Entry(frame, textvariable=self.downsample_var).pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="MRC Preset (2):", font=('Helvetica', 10, 'bold')).pack(anchor=tk.W, pady=(5,0))
        ttk.Entry(frame, textvariable=self.mrc_preset_var).pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="MRC Threshold (10):", font=('Helvetica', 10, 'bold')).pack(anchor=tk.W, pady=(5,0))
        ttk.Entry(frame, textvariable=self.threshold_var).pack(fill=tk.X, pady=5)

        ttk.Checkbutton(frame, text="Use Sauvola Binarization", variable=self.sauvola_var).pack(anchor=tk.W, pady=8)
        ttk.Checkbutton(frame, text="Use Two-Pass OCR", variable=self.twopass_var).pack(anchor=tk.W, pady=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Start Processing", command=self.on_ok).pack(side=tk.RIGHT, padx=5)

    def on_ok(self):
        try:
            self.result = {
                'lang': self.lang_var.get(),
                'dpi': int(self.dpi_var.get()),
                'downsample': int(self.downsample_var.get()),
                'mrc_preset': int(self.mrc_preset_var.get()),
                'threshold': int(self.threshold_var.get()),
                'sauvola': self.sauvola_var.get(),
                'twopass': self.twopass_var.get()
            }
            print("Settings confirmed.")
            self.withdraw() # Hide self instead of quitting yet
            self.quit()
        except ValueError:
            messagebox.showerror("Error", "DPI, Downsample, etc. must be integers.")

    def on_cancel(self):
        print("Settings cancelled.")
        self.result = None
        self.quit()

def get_input_and_settings():
    """Gather input file and settings from user via GUI."""
    temp_root = tk.Tk()
    temp_root.withdraw()
    temp_root.update()
    
    print("Waiting for file selection window...")
    input_pdf = filedialog.askopenfilename(
        parent=temp_root,
        title="Select Scanned PDF to Compress",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
    )
    temp_root.destroy()
    
    if not input_pdf:
        return None

    print(f"File selected: {input_pdf}")

    defaults = {
        'lang': 'eng+ben',
        'dpi': 400,
        'downsample': 3,
        'mrc_preset': 2,
        'threshold': 10,
        'sauvola': True,
        'twopass': False
    }
    
    print("Launching settings window...")
    app = MRCSettingsWindow(defaults)
    app.mainloop()
    
    res: Optional[Dict[str, Any]] = app.result
    # Note: We don't destroy app yet because it's technically the 'root' 
    # and we might want to keep it alive for the progress window.
    # But for this flow, we'll return settings and let main handle it.
    
    if res is None:
        app.destroy()
        return None
        
    settings: Dict[str, Any] = res
    settings['input_pdf'] = input_pdf
    settings['_app'] = app # Keep root reference
    return settings

def save_output_file(temp_output, original_input):
    """Prompt user to save the finished file."""
    root = tk.Tk()
    root.withdraw()
    
    base_name = os.path.splitext(original_input)[0]
    suggested_output = f"{base_name}_bipmrcocr.pdf"
    
    output_pdf = filedialog.asksaveasfilename(
        title="Compression Finished! Save PDF As",
        initialfile=os.path.basename(suggested_output),
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf")]
    )
    
    if not output_pdf:
        output_pdf = suggested_output
        print(f"No output selected, defaulting to: {output_pdf}")
    
    shutil.move(temp_output, output_pdf)
    root.destroy()
    return output_pdf

def main():
    parser = argparse.ArgumentParser(description="Automated MRC Compression Pipeline (Archive.org High Quality)")
    parser.add_argument("input_pdf", nargs='?', help="Path to the source PDF file")
    parser.add_argument("output_pdf", nargs='?', help="Path for the compressed output PDF")
    parser.add_argument("--lang", default="eng+ben", help="OCR Language")
    parser.add_argument("--dpi", type=int, default=400, help="DPI for the output PDF")
    parser.add_argument("--downsample", type=int, default=3, help="Background downsample factor")
    parser.add_argument("--mrc-preset", type=int, default=2, help="MRC Preset")
    parser.add_argument("--threshold", type=int, default=10, help="MRC Threshold")
    parser.add_argument("--sauvola", action="store_true", default=True, help="Use Sauvola binarization")
    parser.add_argument("--two-pass", action="store_true", help="Use two-pass OCR")
    parser.add_argument("--keep-tmp", action="store_true", help="Keep temporary files")
    
    cli_args = parser.parse_args()
    is_interactive = not cli_args.input_pdf
    args: Any
    
    gui_app = None
    if is_interactive:
        print("No input file provided. Launching interactive mode...")
        try:
            settings_dict = get_input_and_settings()
            if not settings_dict:
                print("Operation cancelled.")
                return
            
            gui_app = settings_dict.pop('_app')
            args = argparse.Namespace(
                input_pdf=settings_dict.get('input_pdf'),
                output_pdf=None,
                lang=settings_dict.get('lang'),
                dpi=settings_dict.get('dpi'),
                downsample=settings_dict.get('downsample'),
                mrc_preset=settings_dict.get('mrc_preset'),
                threshold=settings_dict.get('threshold'),
                sauvola=settings_dict.get('sauvola'),
                two_pass=settings_dict.get('twopass'), # Note: 'twopass' from settings_dict, 'two_pass' for argparse
                keep_tmp=False
            )
        except Exception as e:
            print(f"Error launching GUI: {e}")
            sys.exit(1)
    else:
        args = cli_args
        # Initialize attributes if they are missing or None to satisfy linter
        if not getattr(args, 'output_pdf', None):
            if getattr(args, 'input_pdf', None):
                setattr(args, 'output_pdf', f"{os.path.splitext(args.input_pdf)[0]}_bipmrcocr.pdf")
            else:
                setattr(args, 'output_pdf', "output_bipmrcocr.pdf")
        
        # Ensure keep_tmp is always there for the finally block
        if not hasattr(args, 'keep_tmp'):
            setattr(args, 'keep_tmp', False)
        if not hasattr(args, 'input_pdf'):
            setattr(args, 'input_pdf', None)

    # 1. Verification of tools
    tools = ['recode_pdf', 'tesseract', 'pdfimages', 'jbig2']
    missing = [t for t in tools if not shutil.which(t)]
    if missing:
        print(f"Error: Missing required tools: {', '.join(missing)}")
        sys.exit(1)

    # 2. Setup Workspace
    tmp_base = tempfile.mkdtemp(prefix="mrc_")
    # Intermediate temp file for compression if we need to prompt for save later
    temp_result_pdf = os.path.join(tmp_base, "mrc_result.pdf")
    
    # Progress Window for GUI mode
    pw: Optional[ProgressWindow] = None
    if is_interactive and gui_app is not None:
        pw = ProgressWindow(gui_app)
        pw.update_status("Starting pipeline...", 5.0)

    try:
        img_dir = os.path.join(tmp_base, "images")
        os.makedirs(img_dir)
        
        # 3. Extract Images
        if pw is not None: pw.update_status("Step 1: Extracting images...", 10.0)
        print("\n--- Step 1: Extracting images from PDF (Lossless TIFF) ---")
        img_prefix = os.path.join(img_dir, "page")
        run_command(['pdfimages', '-all', '-tiff', args.input_pdf, img_prefix])
        
        images = sorted(glob.glob(os.path.join(img_dir, "page-*")))
        if not images:
            if pw is not None: pw.update_status("Falling back to PNG extraction...", 15.0)
            print("TIFF extraction failed or empty, trying PNG...")
            run_command(['pdfimages', '-all', '-png', args.input_pdf, img_prefix])
            images = sorted(glob.glob(os.path.join(img_dir, "page-*")))

        if not images:
            raise Exception("No images found in PDF.")
        
        total_pages = len(images)
        if pw is not None: pw.update_status(f"Extracted {total_pages} images.", 20.0)
        print(f"Extracted {total_pages} image parts.")
        
        # 4. Generate Batch OCR (hOCR)
        if pw is not None: pw.update_status("Step 2: Running Tesseract OCR...", 30.0)
        print("\n--- Step 2: Running Tesseract OCR (Batch with High Quality Segmentation) ---")
        list_file = os.path.join(tmp_base, "images_list.txt")
        with open(list_file, "w") as f:
            for img in images:
                f.write(f"{img}\n")
        
        hocr_base = os.path.join(tmp_base, "output")
        # IMPORTANT: Flags MUST come after input/outputBase in some Tesseract versions, 
        # but configs (like hocr) must be at the VERY end.
        tess_cmd = [
            'tesseract',
            list_file, 
            hocr_base,
            '-l', args.lang,
            '--dpi', str(args.dpi)
        ]
        
        if getattr(args, 'sauvola', True):
            tess_cmd.extend(['-c', 'thresholding_method=2'])
        
        if getattr(args, 'two_pass', False):
            tess_cmd.extend(['--psm', '1'])
        else:
            tess_cmd.extend(['--psm', '3'])
            
        tess_cmd.append('hocr') # Config file always last
            
        def tess_progress(line: str):
            if "Page" in line:
                try:
                    match = re.search(r"Page (\d+)", line)
                    if match:
                        page_num = int(match.group(1))
                        prog = 30.0 + (page_num / total_pages * 30.0) # 30% to 60%
                        if pw is not None: pw.update_status(f"OCR: Processing page {page_num}/{total_pages}", prog, line)
                except Exception: pass

        run_command(tess_cmd, progress_callback=tess_progress)
        hocr_file = f"{hocr_base}.hocr"
        
        if not os.path.exists(hocr_file):
            raise Exception(f"hOCR file was not generated at {hocr_file}")
        
        # 5. MRC Compression
        if pw is not None: pw.update_status("Step 3: Performing MRC Compression...", 60.0)
        print("\n--- Step 3: Performing MRC Compression via recode_pdf (Master Settings) ---")
        # If interactive, we use temp location; if CLI, we use args.output_pdf
        final_save_path_target = args.output_pdf if not is_interactive else temp_result_pdf
        
        recode_cmd = [
            'recode_pdf',
            '--from-imagestack', os.path.join(img_dir, "page-*"),
            '--hocr-file', hocr_file,
            '--dpi', str(args.dpi),
            '--bg-downsample', str(args.downsample),
            '-m', str(getattr(args, 'mrc_preset', 2)),
            '-t', str(getattr(args, 'threshold', 10)),
            '--mask-compression', 'jbig2',
            '-J', 'openjpeg',
            '-o', final_save_path_target
        ]

        def recode_progress(line: str):
            if "Processed" in line:
                try:
                    match = re.search(r"Processed (\d+)", line)
                    if match:
                        pcount = int(match.group(1))
                        prog = 60.0 + (pcount / total_pages * 35.0) # 60% to 95%
                        if pw is not None: pw.update_status(f"MRC: Compressed {pcount}/{total_pages} pages", prog, line)
                except Exception: pass

        run_command(recode_cmd, progress_callback=recode_progress)
        
        # 6. Finalize Save
        if is_interactive:
            if pw is not None:
                 pw.update_status("Finalizing...", 98.0)
                 pw.destroy()
                 pw = None
            final_path = save_output_file(temp_result_pdf, args.input_pdf)
            print(f"\nSuccess! Saved to: {final_path}")
            messagebox.showinfo("Success", f"Compression finished!\nSaved to: {final_path}")
        else:
            print(f"\nSuccess! High-quality MRC PDF saved to: {args.output_pdf}")
        
    except Exception as e:
        print(f"Error during processing: {e}")
        if pw is not None: 
            pw.destroy()
            pw = None
        if not is_interactive:
             sys.exit(1)
        else:
            messagebox.showerror("Error", f"An error occurred:\n{e}")
    finally:
        if gui_app is not None:
            gui_app.destroy()
            gui_app = None
        if not args.keep_tmp:
            print(f"Cleaning up workspace {tmp_base}...")
            shutil.rmtree(tmp_base)
        else:
            print(f"Temporary files kept at: {tmp_base}")

if __name__ == "__main__":
    main()
