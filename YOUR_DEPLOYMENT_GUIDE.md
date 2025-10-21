# Your Personal Deployment Guide
## Qwen Vision-Language Service on 129.212.185.219

---

## 📋 Pre-Flight Checklist

- ✅ Code pushed to GitHub: https://github.com/maroofsyyed/Qwen_Real_Time
- ✅ Droplet IP: **129.212.185.219**
- ⬜ SSH access verified
- ⬜ ROCm verified
- ⬜ Model downloaded
- ⬜ Service running
- ⬜ Browser tested

---

## STEP 1: Initial SSH Connection (2 minutes)

### Open Terminal on Your Mac

```bash
# SSH into your droplet
ssh root@129.212.185.219

# If asked about fingerprint, type: yes
```

**Expected**: You should see a prompt like:
```
root@your-hostname:~#
```

### Verify System Info

```bash
# Check OS version
cat /etc/os-release | grep PRETTY_NAME
# Expected: Ubuntu 24.04

# Check ROCm installation
rocm-smi

# Expected output: GPU information with ~192 GB VRAM
# Example:
# GPU[0]     : GPU ID: 0x740f
# GPU[0]     : Temperature: 45.0 C
# GPU[0]     : GPU Memory Total: 196608 MB
```

**✅ Checkpoint**: If you see GPU info, proceed. If not, ROCm needs installation.

**Troubleshooting**:
```bash
# If rocm-smi not found, try:
/opt/rocm/bin/rocm-smi

# If still fails, check ROCm installation:
ls -la /opt/rocm/

# You may need to install ROCm - see DEPLOY.md
```

---

## STEP 2: Install System Dependencies (5 minutes)

### Update System

```bash
# Update package lists
apt update

# This will show available updates - just wait for it to complete
```

### Install Required Packages

```bash
# Install all dependencies in one command
apt install -y \
    git \
    git-lfs \
    build-essential \
    python3 \
    python3-venv \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    curl \
    wget \
    tmux

# This takes 3-5 minutes
```

### Initialize Git LFS

```bash
git lfs install
```

**Expected output**: `Git LFS initialized.`

### Verify Installation

```bash
# Check Python
python3 --version
# Expected: Python 3.10 or higher

# Check git-lfs
git-lfs --version
# Expected: git-lfs/3.x.x

# Check tmux (for keeping services running)
tmux -V
# Expected: tmux 3.x
```

**✅ Checkpoint**: All commands should show version numbers.

---

## STEP 3: Clone Your Repository (2 minutes)

### Clone from GitHub

```bash
# Navigate to root home
cd /root

# Clone your repository
git clone https://github.com/maroofsyyed/Qwen_Real_Time.git qwen-camera

# Enter directory
cd qwen-camera

# Verify files
ls -la
```

**Expected files**:
- `README.md`
- `requirements.txt`
- `server/` directory
- `client/` directory
- `scripts/` directory
- `deploy/` directory

**✅ Checkpoint**: You should see all these files and directories.

---

## STEP 4: Setup Python Environment (5 minutes)

### Create Virtual Environment

```bash
# Make sure you're in the project directory
cd /root/qwen-camera

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Your prompt should now show: (venv) root@hostname:~/qwen-camera#
```

### Upgrade pip and Install Dependencies

```bash
# Upgrade pip (suppress warnings)
pip install --upgrade pip setuptools wheel --quiet

# Install all requirements (this takes 3-5 minutes)
pip install -r requirements.txt

# You'll see packages being installed...
```

**This will install**:
- FastAPI
- PyTorch
- Transformers
- aiortc (WebRTC)
- And ~30 other packages

### Verify Installation

```bash
# Test imports
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"
python -c "import aiortc; print(f'aiortc: {aiortc.__version__}')"
python -c "import transformers; print(f'Transformers: {transformers.__version__}')"
```

**Expected**: All should print version numbers without errors.

**✅ Checkpoint**: If all imports work, Python environment is ready!

---

## STEP 5: Download Qwen Model (20-30 minutes) ⏰

This is the **longest step** - the model is ~60-80 GB.

### Check Disk Space

```bash
df -h /root
# Make sure you have 100+ GB free
```

### Start Model Download

```bash
# Make sure you're in the project directory
cd /root/qwen-camera

# Make script executable (if needed)
chmod +x scripts/download_model.sh

# Start download
./scripts/download_model.sh
```

**What happens**:
1. Creates `/root/models/qwen2.5-vl-32b/` directory
2. Downloads model files from HuggingFace
3. Takes 20-30 minutes depending on network speed

**Expected output**:
```
==================================================
Qwen2.5-VL-32B Model Download Script
==================================================

Model: Qwen/Qwen2.5-VL-32B-Instruct
Target directory: /root/models/qwen2.5-vl-32b

Downloading model from HuggingFace...
...
```

### Monitor Download Progress (Optional)

While download runs, open a **new terminal on your Mac**:

```bash
# In a new terminal window
ssh root@129.212.185.219

# Watch download progress
watch -n 10 "du -sh /root/models/qwen2.5-vl-32b 2>/dev/null || echo 'Downloading...'"

# Press Ctrl+C to stop watching
```

### Wait for Completion

**Go get coffee! ☕ This takes 20-30 minutes.**

### Verify Download Complete

```bash
# Back in your original terminal, after download finishes:

# Check model directory
ls -lh /root/models/qwen2.5-vl-32b/

# Expected files:
# - config.json
# - model-00001-of-000XX.safetensors (multiple files, each 10-30 GB)
# - tokenizer files
# - generation_config.json

# Check total size
du -sh /root/models/qwen2.5-vl-32b/
# Expected: 60-80 GB
```

**✅ Checkpoint**: Model directory should contain .safetensors files totaling 60-80 GB.

**Troubleshooting**:
If download fails:
```bash
# Manual download method
cd /root/models
git lfs clone https://huggingface.co/Qwen/Qwen2.5-VL-32B-Instruct qwen2.5-vl-32b

# If you need HuggingFace authentication:
pip install huggingface_hub
huggingface-cli login
# Follow prompts to enter your HF token
```

---

## STEP 6: Configure Environment (3 minutes)

### Create Configuration File

```bash
# Navigate to project
cd /root/qwen-camera

# Copy template
cp env.example .env

# Edit configuration
nano .env
```

### Edit Configuration in nano

You'll see a file with many settings. **Change these lines**:

#### Required Changes:

Find and update these lines (use arrow keys to navigate):

```bash
# Line ~10: Set model path
MODEL_PATH=/root/models/qwen2.5-vl-32b

# Line ~30: Generate and set JWT secret
JWT_SECRET_KEY=PASTE_YOUR_SECRET_HERE
```

**Generate JWT Secret**: 
In a **new terminal on your Mac**, run:
```bash
openssl rand -hex 32
```

Copy the output (64-character hex string) and paste it as `JWT_SECRET_KEY` value.

#### Recommended Settings:

```bash
HOST=0.0.0.0
PORT=8000
HTTPS_ENABLED=false
FRAME_SAMPLE_RATE=2.0
GPU_MEMORY_UTILIZATION=0.90
RESPONSE_MAX_TOKENS=128
REQUIRE_AUTH=true
LOG_LEVEL=INFO
```

### Save and Exit nano

1. Press `Ctrl+X`
2. Press `Y` (yes to save)
3. Press `Enter` (confirm filename)

### Verify Configuration

```bash
# Check critical settings
cat .env | grep MODEL_PATH
cat .env | grep JWT_SECRET_KEY

# Both should show values (not defaults)
```

**✅ Checkpoint**: MODEL_PATH and JWT_SECRET_KEY should be set.

---

## STEP 7: Setup tmux Sessions (2 minutes)

We'll use tmux to keep services running in the background.

### Create tmux Session

```bash
# Create new tmux session named 'qwen'
tmux new -s qwen

# You're now in a tmux session
# Your prompt looks the same, but there's a green bar at the bottom
```

**tmux Quick Reference**:
- `Ctrl+B then C` = Create new window
- `Ctrl+B then N` = Next window
- `Ctrl+B then P` = Previous window
- `Ctrl+B then D` = Detach (leave running)
- `tmux attach -t qwen` = Re-attach later

---

## STEP 8: Start vLLM Server (5 minutes)

### In tmux Window 0 (vLLM)

```bash
# Make sure you're in project directory
cd /root/qwen-camera

# Activate Python environment
source venv/bin/activate

# Start vLLM server
./scripts/start_vllm_server.sh
```

**What happens**:
1. Loads Qwen2.5-VL-32B model into GPU memory
2. Takes 2-3 minutes for model loading
3. Starts inference server on port 12345

**Expected output**:
```
==================================================
Starting vLLM Server for Qwen2.5-VL-32B
==================================================

Configuration:
  Model: /root/models/qwen2.5-vl-32b
  Host: 0.0.0.0:12345
  Data type: float16
  GPU memory utilization: 0.90

Loading model from: /root/models/qwen2.5-vl-32b
...
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:12345 (Press CTRL+C to quit)
```

**✅ Checkpoint**: Wait until you see "Application startup complete"

### Monitor GPU Usage

While vLLM loads, open **another terminal on your Mac**:

```bash
ssh root@129.212.185.219

# Watch GPU memory
watch -n 1 rocm-smi

# You should see VRAM usage climb to ~70-100 GB
# Press Ctrl+C to stop
```

**Expected**: GPU memory usage reaches ~70-100 GB and stabilizes.

### Test vLLM Server

In the monitoring terminal:

```bash
# Test health endpoint
curl http://localhost:12345/health

# Expected: Some JSON response (exact format depends on vLLM version)
```

**✅ Checkpoint**: vLLM responds to health check.

**Keep vLLM running!** Don't close this terminal or tmux window.

---

## STEP 9: Start WebRTC Server (2 minutes)

### Create New tmux Window

In your tmux session with vLLM running:

1. Press `Ctrl+B` then press `C` (creates new window)
2. You're now in tmux window 1

### Start WebRTC Server

```bash
# Navigate to project
cd /root/qwen-camera

# Activate environment
source venv/bin/activate

# Start WebRTC server
python -m server.main
```

**Expected output**:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Connecting to vLLM server at http://localhost:12345
INFO:     Qwen VL inference engine initialized successfully
INFO:     Inference worker started
INFO:     Session manager started
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**✅ Success indicators**:
- "Qwen VL inference engine initialized successfully" ← This is key!
- "Uvicorn running on http://0.0.0.0:8000"
- No error messages

**✅ Checkpoint**: Both servers running successfully!

### Detach from tmux

Both servers are now running. Detach from tmux to leave them running:

1. Press `Ctrl+B` then press `D`

You're back to a regular shell, but services keep running in the background.

**To reattach later**: `tmux attach -t qwen`

---

## STEP 10: Configure Firewall (2 minutes)

### Open Required Ports

```bash
# Check if firewall is active
ufw status

# If active, allow our ports
ufw allow 8000/tcp
ufw allow 12345/tcp
ufw allow 22/tcp  # SSH (make sure this is allowed!)

# Reload firewall
ufw reload

# Verify
ufw status
```

**Expected**: Ports 8000 and 12345 should show as ALLOW.

---

## STEP 11: Test from Your Mac (5 minutes)

### Open Browser

On your Mac, open a web browser and go to:

```
http://129.212.185.219:8000
```

**Expected**: You should see the Qwen Vision interface!

### Test Camera Connection

1. **Click "Start Camera"** button
2. **Allow camera access** when browser asks
3. Video feed should appear
4. Status indicator turns **green** ("Connected")

### Test AI Inference

In the chat box at the bottom, type:

```
What do you see?
```

Press Send or hit Enter.

**Expected**:
- Response appears within 1-2 seconds
- AI describes what's in your camera view

### Try More Questions

```
Describe this image in detail.
What objects are visible?
What color is [object you're showing]?
```

**✅ Checkpoint**: If AI responds to your questions, **IT'S WORKING!** 🎉

---

## STEP 12: Run Benchmark (5 minutes)

### SSH into Droplet

```bash
ssh root@129.212.185.219

cd /root/qwen-camera
source venv/bin/activate
```

### Run Performance Test

```bash
./scripts/benchmark.py --num-requests 100 --monitor-gpu
```

**What it does**:
- Sends 100 test requests
- Measures response times
- Shows GPU memory usage

**Expected output** (after a few minutes):

```
==================================================
BENCHMARK RESULTS
==================================================

Latency Statistics (seconds):
  Mean:   0.850
  Median: 0.750
  Min:    0.521
  Max:    2.104
  StdDev: 0.312

Percentiles:
  P50: 0.750s
  P95: 1.820s
  P99: 2.050s

Throughput:
  2.5 requests/second

Results saved to: benchmark_results/benchmark_20251021_123456.json
```

**✅ Target Metrics** (your hardware):
- Median < 1.5s ✅
- P95 < 2.5s ✅
- No errors ✅

**If metrics are worse**:
1. Check GPU utilization: `rocm-smi`
2. Reduce `RESPONSE_MAX_TOKENS` in `.env`
3. Lower `FRAME_SAMPLE_RATE` in `.env`

---

## STEP 13: Real-time Monitoring (Optional)

### Start Monitor Dashboard

```bash
cd /root/qwen-camera
source venv/bin/activate

./scripts/monitor.py
```

**Shows**:
- Service status
- Active sessions
- GPU memory usage
- Request statistics
- Inference times

Press `Ctrl+C` to exit.

---

## STEP 14: Production Deployment (Optional - 15 minutes)

For persistent deployment with auto-restart:

### Install Systemd Services

```bash
cd /root/qwen-camera

# Stop tmux services first
tmux kill-session -t qwen

# Install services
./deploy/install.sh

# Start services
systemctl start qwen-vllm
systemctl start qwen-webrtc

# Enable auto-start on boot
systemctl enable qwen-vllm
systemctl enable qwen-webrtc

# Check status
systemctl status qwen-vllm
systemctl status qwen-webrtc
```

### View Logs

```bash
# vLLM logs
journalctl -u qwen-vllm -f

# WebRTC logs (in new terminal)
journalctl -u qwen-webrtc -f
```

**✅ Checkpoint**: Services show "active (running)"

---

## STEP 15: Setup HTTPS (Production - Optional)

**Required for remote camera access** (browsers need HTTPS for camera).

### Prerequisites

You need a domain name pointing to `129.212.185.219`.

Example: `qwen.yourdomain.com` → `129.212.185.219`

### Install Nginx and Certbot

```bash
apt install -y nginx certbot python3-certbot-nginx
```

### Configure Nginx

```bash
# Copy config template
cp /root/qwen-camera/deploy/nginx.conf /etc/nginx/sites-available/qwen-vision

# Edit with your domain
nano /etc/nginx/sites-available/qwen-vision

# Change line: server_name your-domain.com;
# To:          server_name qwen.yourdomain.com;
```

Save and exit (Ctrl+X, Y, Enter).

```bash
# Enable site
ln -s /etc/nginx/sites-available/qwen-vision /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default

# Test config
nginx -t

# Reload
systemctl reload nginx
```

### Get SSL Certificate

```bash
certbot --nginx -d qwen.yourdomain.com

# Follow prompts:
# - Enter email
# - Agree to terms
# - Choose: Redirect HTTP to HTTPS (option 2)
```

### Access via HTTPS

```
https://qwen.yourdomain.com
```

Camera should now work from any device!

---

## 🎉 CONGRATULATIONS!

Your Qwen Vision-Language Service is now **LIVE** at:

### Public Access URLs:

**HTTP** (for testing):
```
http://129.212.185.219:8000
```

**HTTPS** (if configured):
```
https://qwen.yourdomain.com
```

---

## 📊 Quick Reference

### Service Management

```bash
# Using tmux (development)
tmux attach -t qwen          # Reattach to services
tmux kill-session -t qwen    # Stop all services

# Using systemd (production)
systemctl start qwen-vllm qwen-webrtc    # Start
systemctl stop qwen-vllm qwen-webrtc     # Stop
systemctl restart qwen-vllm qwen-webrtc  # Restart
systemctl status qwen-vllm qwen-webrtc   # Check status
```

### Monitoring

```bash
# Real-time dashboard
./scripts/monitor.py

# GPU usage
watch -n 1 rocm-smi

# Logs (systemd)
journalctl -u qwen-vllm -f
journalctl -u qwen-webrtc -f

# Health check
curl http://localhost:8000/health
```

### Useful Commands

```bash
# SSH into droplet
ssh root@129.212.185.219

# Navigate to project
cd /root/qwen-camera

# Activate Python environment
source venv/bin/activate

# View configuration
cat .env

# Edit configuration
nano .env

# Restart services (systemd)
systemctl restart qwen-vllm qwen-webrtc
```

---

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
journalctl -u qwen-vllm -n 50
journalctl -u qwen-webrtc -n 50

# Check GPU
rocm-smi

# Check ports
netstat -tulpn | grep -E '(8000|12345)'
```

### Out of Memory

```bash
# Edit config
nano /root/qwen-camera/.env

# Reduce memory utilization
GPU_MEMORY_UTILIZATION=0.80  # Down from 0.90

# Restart
systemctl restart qwen-vllm
```

### Camera Won't Connect

**For remote access, you MUST use HTTPS** (see Step 15).

Or test locally from the droplet:
```bash
curl http://localhost:8000
```

### Slow Responses

```bash
# Edit config
nano /root/qwen-camera/.env

# Reduce tokens
RESPONSE_MAX_TOKENS=64  # Down from 128

# Reduce sampling
FRAME_SAMPLE_RATE=1.0  # Down from 2.0

# Restart
systemctl restart qwen-webrtc
```

---

## 📚 Documentation

- **Complete Guide**: `/root/qwen-camera/README.md`
- **Deployment**: `/root/qwen-camera/DEPLOY.md`
- **Security**: `/root/qwen-camera/SECURITY.md`
- **GitHub**: https://github.com/maroofsyyed/Qwen_Real_Time

---

## ✅ Final Checklist

- ✅ SSH access to 129.212.185.219
- ✅ ROCm installed and GPU visible
- ✅ Model downloaded (60-80 GB)
- ✅ Configuration file set up
- ✅ vLLM server running (port 12345)
- ✅ WebRTC server running (port 8000)
- ✅ Firewall ports opened
- ✅ Browser can connect
- ✅ Camera streaming works
- ✅ AI responds to questions
- ✅ Benchmark shows good latency
- ⬜ (Optional) Systemd services installed
- ⬜ (Optional) HTTPS configured

---

**Service URL**: http://129.212.185.219:8000

**Your hardware is perfect for this!** Expected performance:
- Median latency: 0.5-1.5 seconds
- P95 latency: < 2.5 seconds
- Concurrent users: 5-10

Enjoy your AI vision assistant! 🚀

