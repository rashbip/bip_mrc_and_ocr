#!/bin/bash
# setup_wsl.sh - Install dependencies for archive-pdf-tools in WSL (Ubuntu)

set -e

echo "Updating system packages..."
sudo apt update

echo "Installing system dependencies..."
sudo apt install -y \
    libleptonica-dev \
    libopenjp2-tools \
    libxml2-dev \
    libxslt-dev \
    python3-dev \
    python3-pip \
    python3-venv \
    git \
    tesseract-ocr \
    tesseract-ocr-eng \
    ghostscript \
    libjbig2dec0-dev

# Build jbig2enc from source (essential for MRC)
echo "Building jbig2enc from source..."
if [ ! -d "jbig2enc" ]; then
    git clone https://github.com/agl/jbig2enc
fi
cd jbig2enc
./autogen.sh
./configure
make
sudo make install
cd ..

# Install archive-pdf-tools and Python requirements
echo "Installing archive-pdf-tools..."
pip3 install --upgrade pip
pip3 install archive-pdf-tools pymupdf

echo "Checking installation..."
recode_pdf --version || echo "recode_pdf installation might need checking"

echo "Setup complete!"
