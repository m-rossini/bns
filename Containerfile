# Containerfile for Bean World simulation
# Podman uses this by default; Docker also understands Containerfile.
FROM python:3.10-slim

# System dependencies required by Arcade / OpenGL.
# mesa drivers are needed for software rendering (llvmpipe) under Xvfb.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libegl1 \
    libgles2 \
    libgl1 \
    libgl1-mesa-dri \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxi6 \
    libfontconfig1 \
    xvfb \
    xauth \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Isolated Python environment inside the container
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --upgrade pip && pip install arcade pytest pytest-cov coverage

# Copy application source
COPY sim/ ./sim/

# Headless mode by default inside containers (no display unless overridden).
# Headless mode does not import Arcade/OpenGL, so it also works without Xvfb.
ENV BEAN_HEADLESS=1
ENV BEAN_HEADLESS_FRAMES=600
ENV PYTHONUNBUFFERED=1

# Note: do NOT run xvfb-run as PID 1. Xvfb only signals readiness (SIGUSR1)
# when its parent is not init, so xvfb-run would wait forever in a container.
# For a windowed run inside the container, use:
#   xvfb-run -a python -m sim.main            (with BEAN_HEADLESS=0)
# started from a shell wrapper, or bind-mount the host X11 socket.
CMD ["python", "-m", "sim.main"]
