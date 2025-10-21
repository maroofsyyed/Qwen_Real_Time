# Quickstart Guide - 5 Minutes to Running

Get Qwen Vision-Language Service running on your Ubuntu 24.04 + ROCm droplet in 5 minutes.

## Prerequisites Check

```bash
# Verify GPU
rocm-smi

# Expected output: GPU visible with ~192GB VRAM
```

✅ **You're good to proceed!** Your hardware (1x mi300x-like GPU, 192GB VRAM) is perfect for this.

## Installation Steps

### 1. Clone and Setup (2 minutes)

```bash
cd ~
git clone <YOUR_REPO_URL> qwen-camera
cd qwen-camera

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Download Model (15-30 minutes)

```bash
# This downloads ~60-80GB
./scripts/download_model.sh

# Default location: ~/models/qwen2.5-vl-32b
```

**While downloading**, proceed to step 3.

### 3. Configure (1 minute)

```bash
# Create .env file
cp env.example .env

# Edit configuration
nano .env
```

**Minimum required changes**:
```bash
MODEL_PATH=/root/models/qwen2.5-vl-32b  # Or your download path
JWT_SECRET_KEY=$(openssl rand -hex 32)   # Generate secure key
```

Save and exit (Ctrl+X, Y, Enter).

### 4. Start Services (2 minutes)

```bash
# Terminal 1: Start vLLM server
./scripts/start_vllm_server.sh

# Wait for "Application startup complete" (~2 minutes for model load)

# Terminal 2: Start WebRTC server
source venv/bin/activate
python -m server.main
```

### 5. Test (30 seconds)

Open browser:
```
http://YOUR_SERVER_IP:8000
```

1. Click "Start Camera"
2. Allow camera access
3. Type question: "What do you see?"
4. Get AI response!

## Expected Performance

With your hardware (mi300x-like, 192GB VRAM, FP16):

- **Median latency**: 0.5-1.5 seconds
- **P95 latency**: 1.5-2.5 seconds
- **Throughput**: 1-3 frames/second
- **VRAM usage**: ~70-100 GB

## Troubleshooting

### vLLM fails to start
```bash
# Check GPU
rocm-smi

# If OOM error, reduce memory in .env:
GPU_MEMORY_UTILIZATION=0.85
```

### "Can't connect to camera"
- Use HTTPS (required for camera access on remote servers)
- Or test on localhost first

### Slow responses (>3 seconds)
```bash
# In .env, reduce:
RESPONSE_MAX_TOKENS=64
FRAME_SAMPLE_RATE=1.0
```

## Production Deployment

For production (HTTPS, systemd, monitoring):

```bash
# Install as systemd services
sudo ./deploy/install.sh

sudo systemctl start qwen-vllm
sudo systemctl start qwen-webrtc
```

See [DEPLOY.md](DEPLOY.md) for full production guide.

## Next Steps

- **Benchmark**: `./scripts/benchmark.py --num-requests 100`
- **Monitor**: `./scripts/monitor.py`
- **Optimize**: Try quantization with `./scripts/convert_model.py --quantize 8`
- **Secure**: Read [SECURITY.md](SECURITY.md)

## Hardware Assessment Summary

✅ **FEASIBLE** - Your droplet is excellent for this workload:

| Component | Your Spec | Required | Status |
|-----------|-----------|----------|--------|
| GPU VRAM | 192 GB | ~80 GB | ✅ Excellent |
| Model Size | 32B params | FP16: ~64GB | ✅ Fits comfortably |
| CPU | 20 vCPU | 8+ | ✅ Sufficient |
| RAM | 240 GB | 64+ GB | ✅ Excellent |

**Expected latency**: Sub-second to low-second (0.5-2s) per processed frame.

**Recommendation**: Start with FP16 (as configured). If you need higher throughput, try 8-bit quantization to free up VRAM for larger batches.

---

**Need help?** See README.md for full documentation.

