#!/bin/bash
# Download Qwen2.5-VL-32B-Instruct model weights
# Requires: git-lfs, huggingface-cli

set -e

MODEL_NAME="Qwen/Qwen2.5-VL-32B-Instruct"
MODEL_DIR="${MODEL_DIR:-$HOME/models/qwen2.5-vl-32b}"

echo "=================================================="
echo "Qwen2.5-VL-32B Model Download Script"
echo "=================================================="
echo ""
echo "Model: $MODEL_NAME"
echo "Target directory: $MODEL_DIR"
echo ""

# Check prerequisites
if ! command -v git-lfs &> /dev/null; then
    echo "Error: git-lfs is not installed"
    echo "Install with: sudo apt install git-lfs"
    exit 1
fi

if ! command -v huggingface-cli &> /dev/null; then
    echo "Error: huggingface-cli is not installed"
    echo "Install with: pip install huggingface-hub[cli]"
    exit 1
fi

# Initialize git-lfs
git lfs install

# Create model directory
mkdir -p "$MODEL_DIR"

# Check if already downloaded
if [ -d "$MODEL_DIR/.git" ]; then
    echo "Model directory already exists. Updating..."
    cd "$MODEL_DIR"
    git pull
else
    echo "Downloading model from HuggingFace..."
    echo ""
    echo "Note: This will download ~60-80 GB of data."
    echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
    sleep 5
    
    # Clone the repository
    cd "$(dirname "$MODEL_DIR")"
    git clone "https://huggingface.co/$MODEL_NAME" "$(basename "$MODEL_DIR")"
fi

echo ""
echo "=================================================="
echo "Download complete!"
echo "=================================================="
echo ""
echo "Model location: $MODEL_DIR"
echo ""
echo "Files:"
ls -lh "$MODEL_DIR"
echo ""
echo "Next steps:"
echo "1. Review the model files"
echo "2. Run conversion script if needed: ./scripts/convert_model.sh"
echo "3. Update MODEL_PATH in .env to: $MODEL_DIR"

