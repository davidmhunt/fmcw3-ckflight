# fmcw3-tools: KiCad 10.0.5 CLI plus the repo's tooling. No GUI use.
# Build: docker build -t fmcw3-tools docker/
FROM kicad/kicad:10.0.5@sha256:182c8005cb775a2c448a4c18681d489f1ff472a761885eba3e08b07e3c0564de

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3 python3-venv python3-pip pandoc git git-lfs ca-certificates curl \
      texlive-latex-base texlive-latex-recommended texlive-fonts-recommended lmodern \
 && rm -rf /var/lib/apt/lists/*

# uv, installed from PyPI into a system location.
RUN python3 -m pip install --no-cache-dir --break-system-packages uv

# ./run starts the container with the caller's uid, which has no passwd entry.
ENV HOME=/tmp \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_PROJECT_ENVIRONMENT=/tmp/venv
WORKDIR /work
ENTRYPOINT []
CMD ["bash"]
