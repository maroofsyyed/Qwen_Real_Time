#!/bin/bash
# Installation script for Qwen Vision-Language Service
# Run as root or with sudo

set -e

echo "=================================================="
echo "Qwen Vision-Language Service - Installation"
echo "=================================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root or with sudo"
    exit 1
fi

# Configuration
PROJECT_DIR="${PROJECT_DIR:-/root/qwen-camera}"
LOG_DIR="/var/log/qwen-service"
VENV_DIR="$PROJECT_DIR/venv"

echo "Installation configuration:"
echo "  Project directory: $PROJECT_DIR"
echo "  Log directory: $LOG_DIR"
echo "  Virtual environment: $VENV_DIR"
echo ""

# Create log directory
echo "Creating log directory..."
mkdir -p "$LOG_DIR"
chmod 755 "$LOG_DIR"

# Create project directory if needed
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Project directory does not exist: $PROJECT_DIR"
    echo "Please clone the repository first:"
    echo "  git clone <repo-url> $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# Check for .env file
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    if [ -f env.example ]; then
        cp env.example .env
        echo "Please edit .env and configure your settings:"
        echo "  nano .env"
        read -p "Press Enter after editing .env..."
    else
        echo "Warning: No .env file found. Create one before starting services."
    fi
fi

# Create virtual environment if needed
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate venv and install dependencies
echo "Installing Python dependencies..."
source "$VENV_DIR/bin/activate"
pip install -U pip setuptools wheel
pip install -r requirements.txt

echo ""
echo "Installing systemd services..."

# Install systemd service files
cp deploy/qwen-vllm.service /etc/systemd/system/
cp deploy/qwen-webrtc.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

echo ""
echo "=================================================="
echo "Installation complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Download the model:"
echo "   ./scripts/download_model.sh"
echo ""
echo "2. Update .env with correct MODEL_PATH"
echo ""
echo "3. Enable and start services:"
echo "   systemctl enable qwen-vllm qwen-webrtc"
echo "   systemctl start qwen-vllm"
echo "   systemctl start qwen-webrtc"
echo ""
echo "4. Check service status:"
echo "   systemctl status qwen-vllm"
echo "   systemctl status qwen-webrtc"
echo ""
echo "5. View logs:"
echo "   journalctl -u qwen-vllm -f"
echo "   journalctl -u qwen-webrtc -f"
echo ""
echo "6. Access the service:"
echo "   http://your-server:8000"
echo ""

