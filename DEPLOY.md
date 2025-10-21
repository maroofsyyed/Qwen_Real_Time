# Deployment Guide - Qwen Vision-Language Service

Complete production deployment guide for Ubuntu 24.04 with ROCm.

## Table of Contents

1. [System Prerequisites](#system-prerequisites)
2. [Initial Server Setup](#initial-server-setup)
3. [Model Setup](#model-setup)
4. [vLLM Configuration](#vllm-configuration)
5. [WebRTC Server Setup](#webrtc-server-setup)
6. [TURN Server (coturn)](#turn-server-coturn)
7. [Nginx Reverse Proxy](#nginx-reverse-proxy)
8. [SSL/TLS Certificates](#ssltls-certificates)
9. [Systemd Services](#systemd-services)
10. [Monitoring & Logging](#monitoring--logging)
11. [Scaling Strategies](#scaling-strategies)
12. [Maintenance](#maintenance)

## System Prerequisites

### Hardware Verification

```bash
# Check GPU
rocm-smi
rocminfo | grep "Name:"

# Check VRAM (should show ~192 GB)
rocm-smi --showmeminfo vram

# Check CPU and RAM
lscpu
free -h
```

### ROCm Installation

If ROCm is not installed:

```bash
# Add ROCm repository
wget https://repo.radeon.com/rocm/rocm.gpg.key -O - | gpg --dearmor | \
    sudo tee /etc/apt/keyrings/rocm.gpg > /dev/null

echo 'deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] \
    https://repo.radeon.com/rocm/apt/7.0 ubuntu main' | \
    sudo tee /etc/apt/sources.list.d/rocm.list

# Update and install
sudo apt update
sudo apt install rocm-hip-sdk rocm-smi-lib

# Add user to video/render groups
sudo usermod -aG video,render $USER

# Reboot
sudo reboot
```

Verify after reboot:
```bash
/opt/rocm/bin/rocminfo
```

## Initial Server Setup

### 1. System Update

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git git-lfs curl wget \
    python3-venv python3-pip ffmpeg libsndfile1 nginx
```

### 2. Firewall Configuration

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow WebRTC (STUN/TURN)
sudo ufw allow 3478/tcp
sudo ufw allow 3478/udp
sudo ufw allow 49152:65535/udp  # RTP/RTCP range

# Enable firewall
sudo ufw enable
sudo ufw status
```

### 3. Create Directory Structure

```bash
# Project directory
sudo mkdir -p /root/qwen-camera
sudo chown $USER:$USER /root/qwen-camera

# Logs
sudo mkdir -p /var/log/qwen-service
sudo chown $USER:$USER /var/log/qwen-service

# Models
mkdir -p ~/models
```

## Model Setup

### 1. Download Model Weights

```bash
cd /root/qwen-camera

# Ensure git-lfs is installed
git lfs install

# Download model (requires HuggingFace access)
./scripts/download_model.sh

# Or manually:
# git clone https://huggingface.co/Qwen/Qwen2.5-VL-32B-Instruct ~/models/qwen2.5-vl-32b
```

**Note**: This downloads ~60-80 GB. Ensure sufficient disk space.

### 2. Model Verification

```bash
# Verify model files
./scripts/convert_model.py \
    --model-path ~/models/qwen2.5-vl-32b \
    --verify-only
```

### 3. Optional: Quantization

For better throughput or memory efficiency:

```bash
# 8-bit quantization
./scripts/convert_model.py \
    --model-path ~/models/qwen2.5-vl-32b \
    --output-path ~/models/qwen2.5-vl-32b-int8 \
    --quantize 8

# Update MODEL_PATH in .env
```

**Tradeoff**: Quantization reduces VRAM usage by ~50% but may slightly reduce quality.

## vLLM Configuration

### 1. Install vLLM for ROCm

```bash
cd /root/qwen-camera
source venv/bin/activate

# Run setup script
./scripts/setup_vllm.sh
```

If automatic install fails, build from source:

```bash
git clone https://github.com/vllm-project/vllm.git /tmp/vllm
cd /tmp/vllm
pip install -e .
```

### 2. Test vLLM

```bash
# Dry run to check memory usage
python -c "
from vllm import LLM
llm = LLM(
    model='~/models/qwen2.5-vl-32b',
    dtype='float16',
    gpu_memory_utilization=0.90,
    trust_remote_code=True
)
print('vLLM loaded successfully!')
"
```

**Watch GPU memory** during this test with `watch -n 1 rocm-smi`.

Expected VRAM usage: ~70-100 GB for FP16.

### 3. Optimize vLLM Settings

Edit `.env`:

```bash
# Conservative settings (stable)
GPU_MEMORY_UTILIZATION=0.85
MODEL_MAX_TOKENS=1024
RESPONSE_MAX_TOKENS=64

# Aggressive settings (maximum throughput)
GPU_MEMORY_UTILIZATION=0.95
MODEL_MAX_TOKENS=2048
RESPONSE_MAX_TOKENS=128
```

## WebRTC Server Setup

### 1. Install Dependencies

```bash
cd /root/qwen-camera
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp env.example .env
nano .env
```

**Critical settings**:

```bash
HOST=0.0.0.0
PORT=8000
HTTPS_ENABLED=false  # Set true if using direct HTTPS (not nginx)

MODEL_PATH=/root/models/qwen2.5-vl-32b
VLLM_HOST=localhost
VLLM_PORT=12345

FRAME_SAMPLE_RATE=2.0
REQUIRE_AUTH=true
JWT_SECRET_KEY=$(openssl rand -hex 32)  # Generate unique key

LOG_LEVEL=INFO
LOG_FILE=/var/log/qwen-service/app.log
```

### 3. Test Manually

```bash
# Terminal 1: Start vLLM
./scripts/start_vllm_server.sh

# Terminal 2: Start WebRTC server
python -m server.main
```

Access `http://server-ip:8000` and test camera connection.

## TURN Server (coturn)

For NAT traversal and reliable WebRTC connections:

### 1. Install coturn

```bash
sudo apt install coturn
```

### 2. Configure

Edit `/etc/turnserver.conf`:

```conf
listening-ip=0.0.0.0
relay-ip=YOUR_SERVER_PUBLIC_IP

fingerprint
lt-cred-mech
use-auth-secret
static-auth-secret=YOUR_RANDOM_SECRET

realm=your-domain.com
total-quota=100
stale-nonce=600

cert=/etc/letsencrypt/live/your-domain.com/fullchain.pem
pkey=/etc/letsencrypt/live/your-domain.com/privkey.pem

no-tcp-relay
no-multicast-peers

log-file=/var/log/turnserver.log
```

### 3. Enable and Start

```bash
sudo systemctl enable coturn
sudo systemctl start coturn
sudo systemctl status coturn
```

### 4. Update Client Config

Edit `client/client.js`:

```javascript
const config = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        {
            urls: 'turn:your-domain.com:3478',
            username: 'user',
            credential: 'password'
        }
    ]
};
```

## Nginx Reverse Proxy

### 1. Install Nginx

```bash
sudo apt install nginx
```

### 2. Configure Site

```bash
# Copy template
sudo cp deploy/nginx.conf /etc/nginx/sites-available/qwen-vision

# Update with your domain and SSL paths
sudo nano /etc/nginx/sites-available/qwen-vision

# Enable site
sudo ln -s /etc/nginx/sites-available/qwen-vision /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site

# Test configuration
sudo nginx -t

# Reload
sudo systemctl reload nginx
```

### 3. Serve Client Files

```bash
# Copy client to nginx-accessible location
sudo mkdir -p /var/www/qwen-vision
sudo cp -r /root/qwen-camera/client/* /var/www/qwen-vision/
sudo chown -R www-data:www-data /var/www/qwen-vision

# Update nginx.conf root to /var/www/qwen-vision
```

## SSL/TLS Certificates

### Using Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Certbot will automatically configure nginx
# Certificates auto-renew via systemd timer
```

### Using Self-Signed (Development Only)

```bash
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/qwen-selfsigned.key \
    -out /etc/ssl/certs/qwen-selfsigned.crt

# Update nginx.conf with these paths
```

## Systemd Services

### 1. Install Services

```bash
cd /root/qwen-camera
sudo ./deploy/install.sh
```

This installs:
- `qwen-vllm.service` - vLLM inference server
- `qwen-webrtc.service` - WebRTC and API server

### 2. Start Services

```bash
# Start vLLM first
sudo systemctl start qwen-vllm
sudo systemctl status qwen-vllm

# Wait ~2 minutes for model to load, then start WebRTC
sudo systemctl start qwen-webrtc
sudo systemctl status qwen-webrtc

# Enable auto-start on boot
sudo systemctl enable qwen-vllm qwen-webrtc
```

### 3. View Logs

```bash
# Real-time logs
journalctl -u qwen-vllm -f
journalctl -u qwen-webrtc -f

# Last 100 lines
journalctl -u qwen-vllm -n 100
```

### 4. Restart Services

```bash
# Restart individual service
sudo systemctl restart qwen-webrtc

# Restart both
sudo systemctl restart qwen-vllm qwen-webrtc
```

## Monitoring & Logging

### 1. Service Health

```bash
# Health endpoint
curl http://localhost:8000/health | jq

# Metrics endpoint
curl http://localhost:8000/metrics
```

### 2. Real-time Monitor

```bash
cd /root/qwen-camera
source venv/bin/activate
./scripts/monitor.py
```

### 3. Prometheus + Grafana (Optional)

Install Prometheus:

```bash
sudo apt install prometheus
```

Configure scrape target in `/etc/prometheus/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'qwen-vision'
    static_configs:
      - targets: ['localhost:8000']
```

### 4. Log Rotation

Create `/etc/logrotate.d/qwen-service`:

```
/var/log/qwen-service/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root adm
}
```

## Scaling Strategies

### Horizontal Scaling (Multiple Servers)

1. **Load Balancer**: Use nginx or HAProxy to distribute WebRTC signaling
2. **Shared vLLM**: Multiple WebRTC servers → single vLLM endpoint
3. **Session Affinity**: Ensure WebSocket reconnects go to same server

### Vertical Scaling (Multi-GPU)

For multiple GPUs on one server:

```bash
# In vLLM start script, specify tensor parallelism
python -m vllm.entrypoints.openai.api_server \
    --model ~/models/qwen2.5-vl-32b \
    --tensor-parallel-size 2  # Use 2 GPUs
```

### Alternative WebRTC Backends

For higher concurrency, replace aiortc with:

- **Janus**: C-based, very high performance
- **mediasoup**: Node.js, excellent scaling
- **Pion** (Go): Great performance, containerization

## Maintenance

### Model Updates

```bash
# Download new model version
cd ~/models
git clone https://huggingface.co/Qwen/Qwen2.5-VL-40B-Instruct qwen2.5-vl-40b

# Update .env
MODEL_PATH=/root/models/qwen2.5-vl-40b

# Restart services
sudo systemctl restart qwen-vllm qwen-webrtc
```

### Dependency Updates

```bash
cd /root/qwen-camera
source venv/bin/activate

# Update packages
pip install -U -r requirements.txt

# Test before deploying
pytest tests/

# Restart
sudo systemctl restart qwen-webrtc
```

### GPU Driver Updates

```bash
# Check current version
rocm-smi --version

# Update ROCm (example)
sudo apt update
sudo apt install --only-upgrade rocm-hip-sdk

# Reboot
sudo reboot
```

### Backup

**What to back up**:
- `.env` configuration
- Custom scripts or modifications
- SSL certificates (if custom)

**Do NOT back up**:
- Model weights (re-downloadable)
- Logs (ephemeral)
- venv (recreate from requirements.txt)

```bash
# Backup script
tar -czf qwen-backup-$(date +%Y%m%d).tar.gz \
    /root/qwen-camera/.env \
    /root/qwen-camera/deploy/*.service \
    /etc/nginx/sites-available/qwen-vision
```

## Troubleshooting Production Issues

### Service Won't Start

```bash
# Check service status
sudo systemctl status qwen-vllm
sudo systemctl status qwen-webrtc

# View detailed logs
journalctl -u qwen-vllm --since "10 minutes ago"

# Check for port conflicts
sudo netstat -tulpn | grep -E '(8000|12345)'
```

### High Latency

1. Check GPU utilization: `rocm-smi -d 0`
2. Review inference queue: `curl localhost:8000/health | jq .inference`
3. Reduce `FRAME_SAMPLE_RATE` or `RESPONSE_MAX_TOKENS`
4. Consider quantization

### Out of Memory

```bash
# Check VRAM usage
rocm-smi --showmeminfo vram

# Solutions:
# 1. Lower GPU_MEMORY_UTILIZATION to 0.80
# 2. Reduce MODEL_MAX_TOKENS to 1024
# 3. Use quantized model (8-bit)
# 4. Restart vLLM service to clear cache
sudo systemctl restart qwen-vllm
```

### WebRTC Connection Fails

1. Verify TURN server is running: `sudo systemctl status coturn`
2. Check firewall allows UDP ports
3. Test STUN: `stunclient your-server-ip 3478`
4. Review browser console for WebRTC errors

---

**Production Checklist**:

- [ ] ROCm installed and GPU visible
- [ ] Model downloaded and verified
- [ ] vLLM serving successfully
- [ ] WebRTC server running
- [ ] TURN server configured
- [ ] Nginx with SSL/TLS
- [ ] Systemd services enabled
- [ ] Firewall configured
- [ ] Monitoring in place
- [ ] Logs rotating
- [ ] Backup strategy defined

For additional help, see README.md and SECURITY.md.

