# Complete Installation Fix Guide

## You're Getting Compilation Errors

Two packages are failing to build from source:
1. ✅ `av` - **FIXED** (FFmpeg dev libraries installed)
2. ❌ `sentencepiece` - **NEEDS FIX**

---

## Quick Fix - Install Missing Build Tools

Run these commands in your droplet terminal:

```bash
# Install build dependencies for sentencepiece
apt install -y cmake libgoogle-perftools-dev

# Retry pip install
pip install -r requirements.txt
```

This should work now!

---

## Alternative Fix - Use Pre-Built Wheels (Faster!)

If you still get errors, use this approach instead:

```bash
# Install packages preferring binary wheels (no compilation needed)
pip install --prefer-binary -r requirements.txt
```

This tells pip to use pre-compiled packages when available, avoiding build issues.

---

## Step-by-Step Recovery

Here's exactly what to do on your droplet:

### 1. Install All Build Dependencies (One-Time Setup)

```bash
# Install everything needed for compilation
apt install -y \
    cmake \
    libgoogle-perftools-dev \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    pkg-config \
    g++ \
    gcc

echo "✅ Build dependencies installed!"
```

### 2. Clean Previous Failed Installs

```bash
# Make sure you're in the right directory with venv activated
cd /root/qwen-camera
source venv/bin/activate

# Clean pip cache
pip cache purge

echo "✅ Cache cleaned!"
```

### 3. Retry Installation

```bash
# Try with binary preference first (fastest)
pip install --prefer-binary -r requirements.txt
```

**Expected**: This should succeed now!

---

## Verify Installation Success

After installation completes, verify:

```bash
# Test critical imports
python -c "import torch; print(f'✅ PyTorch: {torch.__version__}')"
python -c "import fastapi; print(f'✅ FastAPI: {fastapi.__version__}')"
python -c "import aiortc; print(f'✅ aiortc: {aiortc.__version__}')"
python -c "import transformers; print(f'✅ Transformers: {transformers.__version__}')"
python -c "import av; print(f'✅ av: {av.__version__}')"
python -c "import sentencepiece; print(f'✅ sentencepiece: {sentencepiece.__version__}')"
```

**Expected**: All should print version numbers with ✅

---

## What Changed in requirements.txt?

If you want to avoid these build issues in future, you could modify `requirements.txt` to specify binary-only installs for problematic packages. But the `--prefer-binary` flag is easier.

---

## Continue Deployment After Fix

Once `pip install -r requirements.txt` succeeds:

### ✅ Checkpoint: Python packages installed

Continue with **Step 6** in YOUR_DEPLOYMENT_GUIDE.md:

```bash
# Download model (this is next - takes 20-30 minutes)
./scripts/download_model.sh
```

---

## Why These Errors Happened

- **`av` package**: Python bindings for FFmpeg - needs FFmpeg development headers
- **`sentencepiece` package**: Tokenization library - needs cmake and C++ build tools

Ubuntu 24.04 doesn't include these development packages by default, only the runtime binaries.

**Solution**: Install the `-dev` packages that contain header files and build tools.

---

## Complete Command Summary

Copy and paste this entire block to fix everything:

```bash
# Install all build dependencies
apt install -y \
    cmake \
    libgoogle-perftools-dev \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    pkg-config \
    g++ \
    gcc

# Go to project directory
cd /root/qwen-camera

# Activate venv
source venv/bin/activate

# Clean cache
pip cache purge

# Install with binary preference
pip install --prefer-binary -r requirements.txt

# Verify success
python -c "import torch, fastapi, aiortc, transformers, av, sentencepiece; print('✅ All packages installed successfully!')"
```

If that last command prints "✅ All packages installed successfully!", you're ready to continue!

---

## Next Step

After successful installation, proceed to download the model:

```bash
./scripts/download_model.sh
```

This takes 20-30 minutes (downloads ~60-80 GB).

While it downloads, you can read ahead in YOUR_DEPLOYMENT_GUIDE.md to prepare for the next steps.

