#!/bin/bash
# bipmrcocr.sh - Native Linux wrapper for the pipeline

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$PROJECT_ROOT/src"
VENV_PYTHON="/home/$USER/pdf_pipeline_venv/bin/python3"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Environment not found. Running setup..."
    bash "$SRC_DIR/robust_setup.sh"
fi

"$VENV_PYTHON" "$SRC_DIR/mrc_ocr_pipeline.py" "$@"
