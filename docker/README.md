# docker/

Pinned Docker image `fmcw3-tools` for running ERC/DRC and the repo tooling reproducibly.
No KiCad GUI use, no simulation tools (fnd-05 decides those).

Build: `docker build -t fmcw3-tools docker/` (the `./run` wrapper builds it on first use).

## Base image

`kicad/kicad:10.0.5` exists on Docker Hub (Debian 13 trixie, linux/amd64), so the exact tag
matching the native KiCad is used. It is pinned by index digest as well:

`sha256:182c8005cb775a2c448a4c18681d489f1ff472a761885eba3e08b07e3c0564de`

Added on top: Python 3.13, `uv`, `pandoc`, TeX Live (pdflatex, the PDF engine), `git`, `git-lfs`.
The image runs as root by default; `./run` passes the caller's uid. `HOME`, the uv cache and the
uv venv point at `/tmp` so an arbitrary uid works.

## Versions recorded from inside the image

- `kicad-cli version`: `10.0.5`
- `uv --version`: `uv 0.13.9`
- `pandoc --version`: `pandoc 3.1.11.1`
- `git lfs version`: `git-lfs/3.6.1`
- `pdflatex --version`: `pdfTeX 3.141592653-2.6-1.40.26 (TeX Live 2025/dev/Debian)`
