import os
import subprocess
import shutil
import tempfile
import argparse
import sys
import glob
from tkinter import filedialog, ttk, messagebox
import tkinter as tk
from typing import Any, Dict, Optional

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
        # Note: We don't exit here so callers can handle the exception
        raise

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
            self.quit()
        except ValueError:
            messagebox.showerror("Error", "DPI, Downsample, etc. must be integers.")

    def on_cancel(self):
        print("Settings cancelled.")
        self.result = None
        self.quit()

def get_input_and_settings():
    """Gather input file and settings from user via GUI."""
    # 1. Select Input File (using a temporary hidden root)
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

    # 2. Configure Settings
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
    app.destroy()

    if res is None:
        return None
        
    settings: Dict[str, Any] = res
    settings['input_pdf'] = input_pdf
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
    
    # Determine if we should use GUI
    if is_interactive:
        print("No input file provided. Launching interactive mode...")
        try:
            settings_dict = get_input_and_settings()
            if not settings_dict:
                print("Operation cancelled.")
                return
            
            settings: Dict[str, Any] = settings_dict
            args = argparse.Namespace(
                input_pdf=settings.get('input_pdf'),
                output_pdf=None,
                lang=settings.get('lang'),
                dpi=settings.get('dpi'),
                downsample=settings.get('downsample'),
                mrc_preset=settings.get('mrc_preset'),
                threshold=settings.get('threshold'),
                sauvola=settings.get('sauvola'),
                two_pass=settings.get('two_pass'),
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
    
    try:
        img_dir = os.path.join(tmp_base, "images")
        os.makedirs(img_dir)
        
        # 3. Extract Images
        print("\n--- Step 1: Extracting images from PDF (Lossless TIFF) ---")
        img_prefix = os.path.join(img_dir, "page")
        run_command(['pdfimages', '-all', '-tiff', args.input_pdf, img_prefix])
        
        images = sorted(glob.glob(os.path.join(img_dir, "page-*")))
        if not images:
            print("TIFF extraction failed or empty, trying PNG...")
            run_command(['pdfimages', '-all', '-png', args.input_pdf, img_prefix])
            images = sorted(glob.glob(os.path.join(img_dir, "page-*")))

        if not images:
            print("No images found in PDF.")
            sys.exit(1)
        
        print(f"Extracted {len(images)} image parts.")
        
        # 4. Generate Batch OCR (hOCR)
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
            
        run_command(tess_cmd)
        hocr_file = f"{hocr_base}.hocr"
        
        if not os.path.exists(hocr_file):
            print(f"Error: hOCR file was not generated at {hocr_file}")
            sys.exit(1)
        
        # 5. MRC Compression
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
        run_command(recode_cmd)
        
        # 6. Finalize Save
        if is_interactive:
            final_path = save_output_file(final_save_path_target, args.input_pdf)
            print(f"\nSuccess! High-quality MRC PDF saved to: {final_path}")
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo("Success", f"Compression finished!\nSaved to: {final_path}")
            root.destroy()
        else:
            print(f"\nSuccess! High-quality MRC PDF saved to: {args.output_pdf}")
        
    except Exception as e:
        print(f"Error during processing: {e}")
        if not is_interactive:
             sys.exit(1)
        else:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Error", f"An error occurred:\n{e}")
            root.destroy()
    finally:
        if not args.keep_tmp:
            print(f"Cleaning up workspace {tmp_base}...")
            shutil.rmtree(tmp_base)
        else:
            print(f"Temporary files kept at: {tmp_base}")

if __name__ == "__main__":
    main()
