# Step-by-Step Deployment Guide

Follow these steps **in order** to deploy your Qwen Vision-Language Service on your Ubuntu 24.04 droplet.

## 🎯 Overview

**Time estimate**: 45-60 minutes (most of it is model download)  
**Location**: Your Ubuntu 24.04 droplet with ROCm 7.0  
**Goal**: Get the service running and accessible via browser

---

## STEP 1: Verify Hardware & ROCm (5 minutes)

SSH into your droplet and verify everything is ready.

```bash
# SSH into your droplet
ssh root@YOUR_DROPLET_IP

# Check ROCm installation
rocm-smi

# Expected output: Should show your GPU with ~192 GB VRAM
# Example:
# GPU[0] : GPU ID: 0x740f
# GPU Memory: 196608 MB (total), 196608 MB (free)
```

**Verification checklist**:
- ✅ `rocm-smi` command works
- ✅ GPU is visible
- ✅ VRAM shows ~192 GB
- ✅ No errors displayed

**If rocm-smi fails**:
```bash
# Try with full path
/opt/rocm/bin/rocm-smi

# If still fails, check ROCm installation
ls -la /opt/rocm/

# You may need to install ROCm - see DEPLOY.md section on ROCm Installation
```

**✅ Proceed only when GPU is visible**

---

## STEP 2: Upload Project to Droplet (5 minutes)

You have two options: Git or SCP

### Option A: Via Git (Recommended)

```bash
# On your droplet
cd /root
git clone https://github.com/YOUR_USERNAME/newqwen.git qwen-camera
cd qwen-camera
```

**Note**: You'll need to push your local project to GitHub first:

```bash
# On your Mac (in /Users/maroofakhtar/Documents/GitHub/newqwen)
git init
git add .
git commit -m "Initial commit: Qwen Vision-Language Service"
git remote add origin https://github.com/YOUR_USERNAME/newqwen.git
git push -u origin main
```

### Option B: Via SCP (Quick alternative)

```bash
# On your Mac
cd /Users/maroofakhtar/Documents/GitHub
tar -czf newqwen.tar.gz newqwen/
scp newqwen.tar.gz root@YOUR_DROPLET_IP:/root/

# On your droplet
cd /root
tar -xzf newqwen.tar.gz
mv newqwen qwen-camera
cd qwen-camera
```

**Verify upload**:
```bash
ls -la
# Should see: server/, client/, scripts/, deploy/, README.md, etc.
```

---

## STEP 3: System Dependencies (5 minutes)

Install required system packages:

```bash
# Update package list
sudo apt update

# Install dependencies
sudo apt install -y \
    git \
    git-lfs \
    build-essential \
    python3 \
    python3-venv \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    curl \
    wget

# Initialize git-lfs (needed for model download)
git lfs install
```

**Verify**:
```bash
python3 --version  # Should show Python 3.10+
git-lfs --version  # Should show git-lfs version
```

---

## STEP 4: Python Environment Setup (3 minutes)

Create and activate virtual environment:

```bash
cd /root/qwen-camera

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies (this takes 2-3 minutes)
pip install -r requirements.txt
```

**Verify installation**:
```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"
python -c "import aiortc; print(f'aiortc: {aiortc.__version__}')"
```

All should print version numbers without errors.

---

## STEP 5: Download Qwen Model (20-30 minutes)

This is the longest step - downloads ~60-80 GB.

```bash
cd /root/qwen-camera

# Check available disk space (need ~100 GB free)
df -h /root

# Download model
./scripts/download_model.sh

# This will:
# - Clone Qwen2.5-VL-32B-Instruct from HuggingFace
# - Download to: /root/models/qwen2.5-vl-32b
# - Take 20-30 minutes depending on network speed
```

**While downloading**, you can monitor progress in another terminal:
```bash
# New terminal window
ssh root@YOUR_DROPLET_IP
watch -n 5 "du -sh /root/models/qwen2.5-vl-32b 2>/dev/null || echo 'Not created yet'"
```

**Verify download completed**:
```bash
ls -lh /root/models/qwen2.5-vl-32b/

# Should see files like:
# - config.json
# - model-*.safetensors (multiple large files, ~20-30 GB each)
# - tokenizer files
# Total size: 60-80 GB
```

**If download fails**:
```bash
# Check HuggingFace access
git lfs clone https://huggingface.co/Qwen/Qwen2.5-VL-32B-Instruct /root/models/qwen2.5-vl-32b

# If you need authentication:
pip install huggingface_hub
huggingface-cli login
# Then retry download
```

---

## STEP 6: Configure Environment (2 minutes)

Set up your configuration file:

```bash
cd /root/qwen-camera

# Copy template
cp env.example .env

# Edit configuration
nano .env
```

**Required changes in `.env`**:

```bash
# Model settings
MODEL_PATH=/root/models/qwen2.5-vl-32b

# Security - IMPORTANT: Generate a secure secret key
JWT_SECRET_KEY=REPLACE_WITH_RANDOM_SECRET

# Server settings
HOST=0.0.0.0
PORT=8000
```

**Generate secure JWT secret**:
```bash
# In another terminal, run:
openssl rand -hex 32

# Copy the output (64 character hex string)
# Paste it as JWT_SECRET_KEY value in .env
```

**Optional settings to adjust**:
```bash
# Frame sampling (1-5 fps, default 2)
FRAME_SAMPLE_RATE=2.0

# GPU memory (0.80-0.95, default 0.90)
GPU_MEMORY_UTILIZATION=0.90

# Response length (64-256, default 128)
RESPONSE_MAX_TOKENS=128
```

**Save and exit**: Press `Ctrl+X`, then `Y`, then `Enter`

**Verify configuration**:
```bash
cat .env | grep -E "MODEL_PATH|JWT_SECRET_KEY"
# Both should have values set
```

---

## STEP 7: Test vLLM Server (5 minutes)

Start vLLM server to verify model loads correctly:

```bash
cd /root/qwen-camera
source venv/bin/activate

# Start vLLM server
./scripts/start_vllm_server.sh
```

**What to expect**:
```
Starting vLLM Server for Qwen2.5-VL-32B
...
Loading model from: /root/models/qwen2.5-vl-32b
...
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:12345
```

**This takes 2-3 minutes** to load the model into GPU memory.

**Watch GPU memory usage** (in another terminal):
```bash
ssh root@YOUR_DROPLET_IP
watch -n 1 rocm-smi
```

You should see VRAM usage increase to ~70-100 GB.

**Test the endpoint** (in another terminal):
```bash
curl http://localhost:12345/health
# Should return: {"status":"ok"} or similar
```

**✅ If successful**: vLLM is working! Keep it running.

**❌ If it crashes**:
- Check error message
- Most common: Out of memory → Reduce `GPU_MEMORY_UTILIZATION` in `.env` to 0.85
- Model not found → Verify MODEL_PATH in `.env`
- See troubleshooting section at bottom

**Keep this terminal open** with vLLM running.

---

## STEP 8: Start WebRTC Server (2 minutes)

Open a **new terminal/tmux/screen session**:

```bash
# New SSH session or use tmux/screen
ssh root@YOUR_DROPLET_IP

cd /root/qwen-camera
source venv/bin/activate

# Start WebRTC server
python -m server.main
```

**Expected output**:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Connecting to vLLM server at http://localhost:12345
INFO:     Qwen VL inference engine initialized successfully
INFO:     Inference worker started
INFO:     Session manager started
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**✅ Success indicators**:
- "Qwen VL inference engine initialized successfully"
- "Uvicorn running on http://0.0.0.0:8000"
- No errors

**Keep this terminal open** as well.

---

## STEP 9: Test the Service (5 minutes)

### From Your Mac/Local Machine:

Open a web browser and navigate to:
```
http://YOUR_DROPLET_IP:8000
```

**Expected behavior**:
1. Page loads showing "Qwen Vision - Live Camera AI"
2. Status shows "Disconnected" initially
3. Click **"Start Camera"** button
4. Browser asks for camera permission → **Allow**
5. Video feed appears
6. Status changes to "Connected" (green dot)
7. Type a question: "What do you see?"
8. AI responds within 1-2 seconds

**Test questions to try**:
- "What do you see?"
- "Describe this image"
- "What objects are visible?"
- "What color is [object]?"

**✅ If working**: Congratulations! Your service is live!

### Verify in Logs:

Back in your server terminals, you should see:
```
# In WebRTC terminal:
INFO - Session abc123 connected
INFO - Session abc123: sampled frame 1
INFO - Sent response to session abc123: I see...
```

---

## STEP 10: Run Benchmark (5 minutes)

Open a third terminal and test performance:

```bash
ssh root@YOUR_DROPLET_IP
cd /root/qwen-camera
source venv/bin/activate

# Run benchmark
./scripts/benchmark.py --num-requests 100 --monitor-gpu
```

**Expected results** (your hardware):
```
Latency Statistics (seconds):
  Mean:   0.850
  Median: 0.750
  P95:    1.800
  P99:    2.200

Throughput:
  2.5 requests/second
```

**✅ Target metrics**:
- Median < 1.5s ✅
- P95 < 2.5s ✅
- No errors ✅

Results saved to `benchmark_results/`.

---

## STEP 11: Production Deployment (Optional, 10 minutes)

For persistent deployment with auto-restart:

### Option A: Using systemd (Recommended)

```bash
cd /root/qwen-camera

# Stop manual servers (Ctrl+C in both terminals)

# Install as systemd services
sudo ./deploy/install.sh

# Start services
sudo systemctl start qwen-vllm
sudo systemctl start qwen-webrtc

# Enable auto-start on boot
sudo systemctl enable qwen-vllm
sudo systemctl enable qwen-webrtc

# Check status
sudo systemctl status qwen-vllm
sudo systemctl status qwen-webrtc
```

**View logs**:
```bash
# vLLM logs
journalctl -u qwen-vllm -f

# WebRTC logs
journalctl -u qwen-webrtc -f
```

### Option B: Using tmux/screen (Quick alternative)

```bash
# Install tmux
sudo apt install tmux

# Create tmux session
tmux new -s qwen

# In tmux window 0: Start vLLM
cd /root/qwen-camera
source venv/bin/activate
./scripts/start_vllm_server.sh

# Press Ctrl+B then C to create new window
# In window 1: Start WebRTC
source venv/bin/activate
python -m server.main

# Detach: Press Ctrl+B then D
# Reattach later: tmux attach -t qwen
```

---

## STEP 12: Setup HTTPS (Production, 15 minutes)

**Required for remote camera access** (browsers require HTTPS).

### Prerequisites:
- Domain name pointing to your droplet IP
- Nginx installed

```bash
# Install nginx
sudo apt install nginx

# Install certbot
sudo apt install certbot python3-certbot-nginx

# Copy nginx config
sudo cp /root/qwen-camera/deploy/nginx.conf /etc/nginx/sites-available/qwen-vision

# Edit with your domain
sudo nano /etc/nginx/sites-available/qwen-vision
# Change: server_name your-domain.com;
# To:     server_name actual-domain.com;

# Enable site
sudo ln -s /etc/nginx/sites-available/qwen-vision /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Follow prompts, select redirect HTTP to HTTPS

# Test nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

**Access via HTTPS**:
```
https://your-domain.com
```

---

## STEP 13: Monitor & Verify (Ongoing)

### Real-time Monitoring:

```bash
cd /root/qwen-camera
source venv/bin/activate

# Start monitor dashboard
./scripts/monitor.py
```

**Shows**:
- Service status
- Active sessions
- GPU memory usage
- Inference statistics

### Check GPU:

```bash
watch -n 1 rocm-smi
```

### Check Metrics:

```bash
curl http://localhost:8000/metrics
```

---

## 📊 Success Checklist

After completing all steps, verify:

- ✅ GPU visible with `rocm-smi`
- ✅ Model downloaded (~60-80 GB)
- ✅ vLLM server running (port 12345)
- ✅ WebRTC server running (port 8000)
- ✅ Browser can connect and stream camera
- ✅ AI responds to questions (< 2s latency)
- ✅ Benchmark shows median < 1.5s
- ✅ No errors in logs
- ✅ (Optional) HTTPS configured
- ✅ (Optional) Systemd services enabled

---

## 🐛 Troubleshooting

### vLLM Server Crashes (OOM)

**Symptom**: vLLM exits with "CUDA out of memory" or similar

**Solution**:
```bash
# Edit .env
nano /root/qwen-camera/.env

# Reduce memory utilization
GPU_MEMORY_UTILIZATION=0.80  # Down from 0.90

# Or use quantization
cd /root/qwen-camera
source venv/bin/activate
./scripts/convert_model.py \
  --model-path /root/models/qwen2.5-vl-32b \
  --quantize 8

# Update .env
MODEL_PATH=/root/models/qwen2.5-vl-32b_int8

# Restart vLLM
```

### WebRTC Won't Connect

**Symptom**: Browser shows "Failed to establish WebRTC connection"

**Solutions**:
1. **For local testing**: Use `http://localhost:8000` (if accessing from droplet itself)
2. **For remote access**: **Must use HTTPS** (Step 12)
3. **Check firewall**:
   ```bash
   sudo ufw allow 8000/tcp
   sudo ufw allow 12345/tcp
   sudo ufw status
   ```

### Camera Access Denied

**Symptom**: Browser says "Permission denied" for camera

**Solutions**:
- **Must use HTTPS** for remote access (browsers require secure context)
- Or test on `localhost` for development
- Check browser camera permissions in settings

### Slow Responses (> 3s)

**Solutions**:
```bash
# Edit .env
nano /root/qwen-camera/.env

# Reduce token generation
RESPONSE_MAX_TOKENS=64  # Down from 128

# Reduce sampling rate
FRAME_SAMPLE_RATE=1.0  # Down from 2.0

# Restart servers
```

### Model Download Fails

**Solutions**:
```bash
# Check disk space
df -h /root

# Check git-lfs
git lfs install

# Manual download
cd /root/models
git lfs clone https://huggingface.co/Qwen/Qwen2.5-VL-32B-Instruct qwen2.5-vl-32b

# If need auth:
pip install huggingface_hub
huggingface-cli login
```

### Port Already in Use

**Symptom**: "Address already in use" error

**Solution**:
```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill it
sudo kill -9 PID

# Or use different port in .env
PORT=8001
```

---

## 🎯 Quick Reference Commands

```bash
# Start services (manual)
./scripts/start_vllm_server.sh              # Terminal 1
python -m server.main                        # Terminal 2

# Start services (systemd)
sudo systemctl start qwen-vllm qwen-webrtc

# View logs
journalctl -u qwen-vllm -f
journalctl -u qwen-webrtc -f

# Monitor
./scripts/monitor.py
rocm-smi

# Benchmark
./scripts/benchmark.py --num-requests 100

# Stop services
sudo systemctl stop qwen-vllm qwen-webrtc

# Restart
sudo systemctl restart qwen-vllm qwen-webrtc
```

---

## 📚 Next Steps After Deployment

1. **Optimize**: Adjust `FRAME_SAMPLE_RATE` and `RESPONSE_MAX_TOKENS` based on your use case
2. **Scale**: See DEPLOY.md for multi-GPU or multi-server setups
3. **Monitor**: Set up Prometheus/Grafana for long-term metrics
4. **Secure**: Review SECURITY.md checklist
5. **Customize**: Modify prompts in `server/inference.py` for your domain

---

## 🆘 Need Help?

- **Full docs**: README.md, DEPLOY.md, SECURITY.md
- **Logs**: `journalctl -u qwen-webrtc -f`
- **GPU**: `rocm-smi`
- **Health**: `curl http://localhost:8000/health`

---

**Estimated Total Time**: 45-60 minutes (including model download)

**You're ready to deploy!** Start with Step 1.

