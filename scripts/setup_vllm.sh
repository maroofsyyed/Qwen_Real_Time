#!/bin/bash
# Setup and configure vLLM for ROCm
# Run this script to prepare vLLM for serving Qwen2.5-VL

set -e

echo "=================================================="
echo "vLLM + ROCm Setup Script"
echo "=================================================="
echo ""

# Check ROCm installation
echo "Checking ROCm installation..."
if command -v rocm-smi &> /dev/null; then
    rocm-smi
    echo ""
else
    echo "Warning: rocm-smi not found. Is ROCm installed?"
    echo "Expected location: /opt/rocm/bin/rocm-smi"
fi

# Check GPU visibility
echo "Checking GPU..."
if command -v rocminfo &> /dev/null; then
    GPU_COUNT=$(rocminfo | grep -c "Name:.*gfx" || true)
    echo "Found $GPU_COUNT GPU(s)"
else
    echo "Warning: rocminfo not available"
fi

echo ""
echo "Python environment:"
python3 --version
pip --version

echo ""
echo "Installing/Upgrading vLLM for ROCm..."

# Check if vLLM is already installed
if python3 -c "import vllm" 2>/dev/null; then
    echo "vLLM is already installed:"
    python3 -c "import vllm; print(f'  Version: {vllm.__version__}')"
    echo ""
    read -p "Reinstall/upgrade? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping vLLM installation"
        exit 0
    fi
fi

# Install vLLM
# Note: ROCm builds may require specific wheel or building from source
echo ""
echo "Installing vLLM..."
echo "Note: For ROCm, you may need a specific build or to build from source."
echo ""

# Try pip install first
pip install vllm==0.9.2 || {
    echo ""
    echo "Standard pip install failed. Trying alternative methods..."
    echo ""
    
    # Try nightly or ROCm-specific wheel
    echo "Attempting to install ROCm-compatible wheel..."
    pip install "vllm @ https://files.pythonhosted.org/packages/.../vllm-0.9.2+rocm-..." || {
        echo ""
        echo "Could not find ROCm wheel. You may need to build from source:"
        echo ""
        echo "  git clone https://github.com/vllm-project/vllm.git"
        echo "  cd vllm"
        echo "  pip install -e ."
        echo ""
        echo "Or check vLLM documentation for ROCm installation:"
        echo "  https://docs.vllm.ai/en/latest/getting_started/amd-installation.html"
        echo ""
        exit 1
    }
}

echo ""
echo "vLLM installed successfully!"

# Verify installation
echo ""
echo "Verifying vLLM installation..."
python3 -c "
import vllm
print(f'vLLM version: {vllm.__version__}')

import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')

if torch.cuda.is_available():
    print(f'Device: {torch.cuda.get_device_name(0)}')
    print(f'Device count: {torch.cuda.device_count()}')
"

echo ""
echo "=================================================="
echo "Setup complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Download model: ./scripts/download_model.sh"
echo "2. Start vLLM server: ./scripts/start_vllm_server.sh"

