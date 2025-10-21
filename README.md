# Qwen Vision-Language Realtime Service

Production-ready realtime camera streaming service with Qwen2.5-VL-32B-Instruct multimodal AI inference. Point your camera, ask questions, and get intelligent responses about what the AI sees.

## 🎯 Features

- **Live Camera Streaming**: WebRTC-based realtime video capture (no file uploads)
- **Vision-Language AI**: Qwen2.5-VL-32B-Instruct for multimodal understanding
- **Low Latency**: Sub-second to low-second inference times
- **Production Ready**: Systemd services, Docker support, monitoring tools
- **Privacy First**: No video storage, camera stream only, optional face blurring
- **Security**: JWT authentication, HTTPS support, explicit file upload blocking

## 📋 Requirements

### Hardware
- **GPU**: AMD GPU with ROCm support (tested on mi300x-like)
- **VRAM**: 192 GB recommended for FP16 (minimum ~80 GB with optimizations)
- **CPU**: 20+ vCPUs
- **RAM**: 240 GB+
- **OS**: Ubuntu 24.04

### Software
- ROCm 7.0+
- Python 3.10+
- vLLM 0.9.2 (ROCm build)
- Git LFS (for model download)

## 🚀 Quick Start

### 1. Hardware Check

```bash
# Verify ROCm installation
rocm-smi
rocminfo | grep "Name:"

# Expected: GPU visible with ~192 GB VRAM
```

**Assessment**: With 192 GB VRAM on a mi300x-like GPU, you can comfortably serve Qwen2.5-VL-32B in FP16. Expected latency: 0.5-2s per processed frame.

### 2. Clone and Setup

```bash
# Clone repository
git clone <repo-url> ~/qwen-camera
cd ~/qwen-camera

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Download Model

```bash
# Download Qwen2.5-VL-32B-Instruct weights
./scripts/download_model.sh

# This downloads ~60-80 GB from HuggingFace
# Default location: ~/models/qwen2.5-vl-32b
```

### 4. Configure

```bash
# Copy environment template
cp env.example .env

# Edit configuration
nano .env
```

**Key settings**:
```bash
MODEL_PATH=/root/models/qwen2.5-vl-32b
MODEL_DTYPE=float16
FRAME_SAMPLE_RATE=2.0  # Process 2 frames/second
GPU_MEMORY_UTILIZATION=0.90
JWT_SECRET_KEY=<generate-random-secret>
```

### 5. Start Services

#### Option A: Using systemd (recommended for production)

```bash
# Install systemd services
sudo ./deploy/install.sh

# Start vLLM server
sudo systemctl start qwen-vllm
sudo systemctl status qwen-vllm

# Start WebRTC server
sudo systemctl start qwen-webrtc
sudo systemctl status qwen-webrtc

# Enable auto-start on boot
sudo systemctl enable qwen-vllm qwen-webrtc
```

#### Option B: Manual start (for development)

```bash
# Terminal 1: Start vLLM server
./scripts/start_vllm_server.sh

# Terminal 2: Start WebRTC server
source venv/bin/activate
python -m server.main
```

#### Option C: Using Docker

```bash
# Start with docker-compose
docker-compose -f deploy/docker-compose.yml up -d

# View logs
docker-compose logs -f
```

### 6. Access the Service

Open browser and navigate to:
```
http://your-server-ip:8000
```

- Click **"Start Camera"** (allow camera access)
- WebRTC connection establishes
- Type questions in the chat about what you're showing
- Get AI responses based on live camera feed

**Note**: For remote access, use HTTPS and proper domain/certificates.

## 📊 Architecture

```
[Mobile Browser] 
    |
    | WebRTC Video (2 fps sampling)
    ↓
[WebRTC Server (aiortc)]
    |
    | Frame extraction & preprocessing
    ↓
[Inference Queue]
    |
    | Async worker
    ↓
[vLLM Server] → [Qwen2.5-VL-32B]
    |
    | Vision→Language inference
    ↓
[WebSocket] → [Client UI]
```

### Components

- **Client**: HTML/JS WebRTC + chat UI (camera only, no upload)
- **Server**: FastAPI + aiortc for WebRTC ingestion
- **Inference**: vLLM (ROCm) serving Qwen2.5-VL-32B
- **Session Management**: Ephemeral sessions with JWT tokens
- **Monitoring**: Prometheus metrics, health checks

## 🔧 Configuration

### Frame Sampling

Control inference frequency (balance latency vs. responsiveness):

```bash
FRAME_SAMPLE_RATE=2.0  # 2 frames/second (default)
# Increase to 5.0 for faster reactions
# Decrease to 1.0 to reduce GPU load
```

### Response Length

Adjust token generation for speed:

```bash
RESPONSE_MAX_TOKENS=128  # Short answers (faster)
# Increase to 256 for more detailed responses
```

### GPU Memory

Fine-tune VRAM utilization:

```bash
GPU_MEMORY_UTILIZATION=0.90  # Use 90% of VRAM
# Reduce if running into OOM errors
# Increase to 0.95 for maximum batch size
```

### Quantization (Optional)

For higher throughput or if memory-constrained:

```bash
# Convert model to 8-bit
./scripts/convert_model.py \
  --model-path ~/models/qwen2.5-vl-32b \
  --quantize 8

# Update MODEL_PATH in .env to the quantized version
```

## 📈 Monitoring & Benchmarks

### Real-time Monitoring

```bash
# Monitor service health and GPU usage
./scripts/monitor.py

# Optional: specify server URL
./scripts/monitor.py --server-url http://localhost:8000
```

### Run Benchmarks

```bash
# Run latency benchmark (100 requests)
./scripts/benchmark.py --num-requests 100 --monitor-gpu

# Results saved to benchmark_results/
```

**Expected Performance** (single GPU, FP16):
- Median latency: 0.5-1.5s
- P95 latency: 1.5-2.5s
- Throughput: 1-3 frames/second (depending on answer length)

### View Logs

```bash
# Systemd logs
journalctl -u qwen-vllm -f
journalctl -u qwen-webrtc -f

# Application logs (if LOG_FILE configured)
tail -f /var/log/qwen-service/app.log
```

### Metrics Endpoint

```
http://your-server:8000/metrics
```

Prometheus-compatible metrics for sessions, inference times, queue depth.

## 🔒 Security

### No File Upload Policy

This service **strictly prohibits file uploads**. Only live camera streams are accepted.

**Enforcement**:
- No upload endpoints in API
- Explicit 403 blocking of `/upload` routes
- Client UI has no file input controls
- Only WebRTC video tracks accepted

### Authentication

```bash
# Enable authentication (recommended for production)
REQUIRE_AUTH=true

# Generate secure secret
JWT_SECRET_KEY=$(openssl rand -hex 32)
```

### HTTPS

For production, **always use HTTPS**:

1. Obtain SSL certificate (Let's Encrypt recommended)
2. Configure in `.env`:
   ```bash
   HTTPS_ENABLED=true
   SSL_CERT_PATH=/path/to/cert.pem
   SSL_KEY_PATH=/path/to/key.pem
   ```
3. Or use Nginx reverse proxy (see `deploy/nginx.conf`)

### Privacy Features

```bash
# Optional: Blur faces in frames
ENABLE_FACE_BLUR=true

# Optional: NSFW filter
ENABLE_NSFW_FILTER=true
```

### Data Retention

**Default**: No frames are persisted to disk. All processing is in-memory and ephemeral.

- Chat history kept only in session (RAM)
- Sessions expire after 1 hour of inactivity
- No video recording or storage

## 🌐 Production Deployment

See [DEPLOY.md](DEPLOY.md) for detailed production deployment guide including:

- TURN server setup (coturn)
- Scaling with mediasoup/Janus
- Load balancing
- Firewall configuration
- SSL/TLS setup
- Monitoring and alerting

## 🐛 Troubleshooting

### vLLM fails to start

**Issue**: Model loading fails or OOM error

**Solutions**:
1. Check GPU memory: `rocm-smi`
2. Reduce `GPU_MEMORY_UTILIZATION` to 0.85
3. Use quantized model (8-bit)
4. Reduce `MODEL_MAX_TOKENS` to 1024

### WebRTC connection fails

**Issue**: Camera stream doesn't reach server

**Solutions**:
1. Check firewall allows WebRTC ports
2. Use STUN/TURN server for NAT traversal
3. Verify browser camera permissions
4. Check browser console for errors

### Inference too slow

**Issue**: Responses take >3 seconds

**Solutions**:
1. Reduce `RESPONSE_MAX_TOKENS` to 64
2. Lower `FRAME_SAMPLE_RATE` to 1.0
3. Use quantized model
4. Check GPU utilization with `rocm-smi`
5. Verify vLLM is using GPU (not CPU fallback)

### Model conversion fails

**Issue**: `convert_model.py` errors

**Solutions**:
1. Install conversion dependencies:
   ```bash
   pip install auto-gptq bitsandbytes
   ```
2. Use `--verify-only` to check model integrity
3. Check disk space (conversion needs ~2x model size)

## 📚 API Reference

### REST Endpoints

- `GET /` - Health check
- `GET /health` - Detailed health status
- `POST /api/token` - Get ephemeral session token
- `POST /api/webrtc/offer` - WebRTC signaling (requires auth)
- `GET /metrics` - Prometheus metrics

### WebSocket

Connect to `/ws/{session_id}` for bidirectional chat.

**Send**:
```json
{
  "type": "chat",
  "content": "What do you see?"
}
```

**Receive**:
```json
{
  "type": "response",
  "text": "I see a laptop on a desk...",
  "inference_time": 0.842
}
```

## 🛠️ Development

### Project Structure

```
qwen-camera/
├── server/           # Backend Python code
│   ├── main.py       # FastAPI application
│   ├── webrtc_server.py  # WebRTC handling
│   ├── inference.py  # vLLM inference worker
│   ├── auth.py       # JWT authentication
│   └── session_manager.py
├── client/           # Frontend HTML/JS
│   ├── index.html
│   └── client.js
├── scripts/          # Utilities
│   ├── download_model.sh
│   ├── convert_model.py
│   ├── benchmark.py
│   └── monitor.py
├── deploy/           # Deployment configs
│   ├── install.sh
│   ├── *.service     # Systemd units
│   ├── docker-compose.yml
│   └── nginx.conf
├── requirements.txt
├── config.py
└── README.md
```

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio

# Run tests (when available)
pytest tests/
```

### Code Quality

```bash
# Format code
black server/ scripts/

# Type checking (optional)
mypy server/
```

## 🤝 Contributing

Contributions welcome! Please:

1. Follow existing code style (black formatting)
2. Add tests for new features
3. Update documentation
4. Ensure no file upload paths are added

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

- **Qwen Team** - Qwen2.5-VL-32B-Instruct model
- **vLLM** - High-performance LLM serving
- **aiortc** - WebRTC in Python
- **ROCm** - AMD GPU acceleration

## 📞 Support

For issues and questions:
- GitHub Issues: [repo-url]/issues
- Documentation: See DEPLOY.md, SECURITY.md

---

**Version**: 1.0.0  
**Last Updated**: 2025-10-21

