#!/bin/bash
# robust_setup.sh - A script to check, install, and verify all dependencies for the OCR+MRC pipeline.

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=== Starting Robust Environment Check and Setup ===${NC}"

# 1. System Dependencies Check
check_sys_dep() {
    if dpkg -s "$1" >/dev/null 2>&1; then
        echo -e "${GREEN}[OK]${NC} System package: $1 is already installed."
    else
        echo -e "System package: $1 is missing. Installing..."
        sudo apt update && sudo apt install -y "$1"
    fi
}

echo -e "\n${BLUE}--- Checking System Packages ---${NC}"
SYSTEM_DEPS=("libleptonica-dev" "libopenjp2-7-dev" "tesseract-ocr" "tesseract-ocr-eng" "tesseract-ocr-ben" "ghostscript" "libxml2-dev" "libxslt-dev" "python3-pip" "python3-venv" "automake" "libtool" "pkg-config")
for dep in "${SYSTEM_DEPS[@]}"; do
    check_sys_dep "$dep"
done

# 2. jbig2enc Check (Essential for MRC)
echo -e "\n${BLUE}--- Checking jbig2enc ---${NC}"
if command -v jbig2 >/dev/null 2>&1; then
    echo -e "${GREEN}[OK]${NC} jbig2enc is installed."
else
    echo -e "jbig2enc not found. Building from source in home directory..."
    pushd ~
    if [ ! -d "jbig2enc" ]; then
        git clone https://github.com/agl/jbig2enc
    fi
    cd jbig2enc
    ./autogen.sh
    ./configure
    make
    sudo make install
    popd
fi

# 3. Python Virtual Environment and Library Check
echo -e "\n${BLUE}--- Setting up Python Virtual Environment ---${NC}"
VENV_DIR="/home/biplob/pdf_pipeline_venv"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "Creating virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

echo -e "Installing Python libraries..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install archive-pdf-tools pymupdf

# 4. Final Verification
echo -e "\n${BLUE}--- Final Verification ---${NC}"

if "$VENV_DIR/bin/python3" -c "import fitz; import internetarchivepdf; print('Python libs OK')" >/dev/null 2>&1; then
    echo -e "${GREEN}[OK]${NC} Python libraries (PyMuPDF, archive-pdf-tools) verified."
else
    echo -e "${RED}[ERROR]${NC} Python library verification failed."
    exit 1
fi

if command -v tesseract >/dev/null 2>&1; then
    echo -e "${GREEN}[OK]${NC} Tesseract verified."
else
     echo -e "${RED}[ERROR]${NC} Tesseract not found."
     exit 1
fi

echo -e "\n${GREEN}=== Environment is READY! ===${NC}"
echo -e "To run your pipeline, use the virtual environment Python:"
echo -e "${BLUE}$VENV_DIR/bin/python3 mrc_ocr_pipeline.py input.pdf output.pdf${NC}"
