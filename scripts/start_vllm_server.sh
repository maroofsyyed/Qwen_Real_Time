#!/bin/bash
# Start vLLM server for Qwen2.5-VL-32B-Instruct
# Optimized for single GPU (192GB VRAM)

set -e

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configuration
MODEL_PATH="${MODEL_PATH:-$HOME/models/qwen2.5-vl-32b}"
VLLM_HOST="${VLLM_HOST:-0.0.0.0}"
VLLM_PORT="${VLLM_PORT:-12345}"
DTYPE="${MODEL_DTYPE:-float16}"
GPU_MEMORY="${GPU_MEMORY_UTILIZATION:-0.90}"
MAX_MODEL_LEN="${MODEL_MAX_TOKENS:-2048}"

echo "=================================================="
echo "Starting vLLM Server for Qwen2.5-VL-32B"
echo "=================================================="
echo ""
echo "Configuration:"
echo "  Model: $MODEL_PATH"
echo "  Host: $VLLM_HOST:$VLLM_PORT"
echo "  Data type: $DTYPE"
echo "  GPU memory utilization: $GPU_MEMORY"
echo "  Max model length: $MAX_MODEL_LEN"
echo ""

# Check if model exists
if [ ! -d "$MODEL_PATH" ]; then
    echo "Error: Model not found at $MODEL_PATH"
    echo "Please download the model first: ./scripts/download_model.sh"
    exit 1
fi

# Check GPU
echo "GPU Status:"
rocm-smi || echo "Warning: Could not check GPU status"
echo ""

# Start vLLM server
echo "Starting vLLM server..."
echo ""

# Use vLLM's OpenAI-compatible server
python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_PATH" \
    --host "$VLLM_HOST" \
    --port "$VLLM_PORT" \
    --dtype "$DTYPE" \
    --max-model-len "$MAX_MODEL_LEN" \
    --gpu-memory-utilization "$GPU_MEMORY" \
    --trust-remote-code \
    --disable-log-requests \
    2>&1 | tee vllm_server.log

# Alternative: Use vLLM offline inference if server mode doesn't work
# python scripts/vllm_inference_server.py

