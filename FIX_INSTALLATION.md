# Fix for av Package Installation Error

## Error You're Seeing

```
Package libavdevice was not found in the pkg-config search path.
pkg-config could not find libraries ['avformat', 'avcodec', 'avdevice', 'avutil', 'avfilter', 'swscale', 'swresample']
```

## Solution

The `av` Python package needs FFmpeg **development libraries** (not just the ffmpeg binary).

### Run These Commands:

```bash
# Install FFmpeg development packages
apt install -y \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    pkg-config

# Now retry pip install
pip install -r requirements.txt
```

This should complete successfully now!

## What This Does

- `libavformat-dev`, `libavcodec-dev`, etc. - FFmpeg development headers
- `pkg-config` - Tool that helps find these libraries during compilation

The `av` package (PyAV) is a Python binding for FFmpeg and needs these to compile.

## Continue After Fix

Once `pip install -r requirements.txt` succeeds, continue with:

```bash
# Download model (20-30 minutes)
./scripts/download_model.sh
```

Then follow the rest of YOUR_DEPLOYMENT_GUIDE.md from Step 6 onwards.

