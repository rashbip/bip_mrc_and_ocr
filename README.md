# MRC Compression & OCR Pipeline

An automated Python tool designed to replicate the **Internet Archive (Archive.org)** high-quality PDF compression pipeline. This script converts scanned PDFs into highly compressed, searchable MRC (Mixed Raster Content) PDFs with crisp text and optimized file sizes.

## 🚀 Features

- **High-Quality MRC**: Uses `recode_pdf` to separate text (foreground) from background images for optimal compression.
- **Archive.org Master Settings**: Defaulting to 400 DPI, MRC Preset 2, and JPEG 2000 compression.
- **Advanced OCR**: Powered by Tesseract 5 with **Sauvola Binarization** for superior text recognition on aged or shadowed documents.
- **Interactive GUI**: Easy file selection and settings adjustment via a built-in graphical interface.
- **Lossless Extraction**: Uses TIFF as an intermediate format to maintain visual fidelity during processing.
- **Cross-Platform**: Designed for Fedora/Linux and Windows.

## 🛠️ Prerequisites

Ensure the following tools are installed and available in your system `PATH`:

1.  **Poppler-utils** (for `pdfimages`)
2.  **Tesseract OCR** (v5.0+ recommended)
3.  **archive-pdf-tools** (via pip)
4.  **jbig2enc** (for mask compression)
5.  **tkinter** (usually included with Python, or `python3-tkinter` on Fedora)

### Fedora Installation
```bash
sudo dnf install poppler-utils tesseract tesseract-langpack-ben python3-tkinter
pip install archive-pdf-tools
```

## 📖 Usage

### Interactive Mode (Recommended)
Simply run the script without arguments to open the GUI:
```bash
python3 mrc_compress.py
```
1. Select your input PDF.
2. Adjust settings (DPI, Language, Sauvola, etc.) in the popup window.
3. Click "Start Compression".
4. After processing, select your save location.

### CLI Mode (Automation)
For batch processing or advanced command-line use:
```bash
python3 mrc_compress.py input.pdf output.pdf --lang eng+ben --two-pass --dpi 400
```

## ⚙️ Settings Explained

- **DPI**: Output resolution (400 is the IA standard).
- **Sauvola Binarization**: Advanced adaptive thresholding that cleans up backgrounds for better OCR.
- **Two-Pass OCR**: Slower but more accurate page segmentation.
- **MRC Preset 2**: The high-quality segmentation preset.
- **BG Downsample**: Reduces background image resolution (default 3) to save space without affecting text sharpness.

## 🤝 Acknowledgments
- Based on `archive-pdf-tools` by the Internet Archive.
- Developed for professional Bengali and English document digitisation.
