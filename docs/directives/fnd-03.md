# fnd-03: Repeatable environment (setup guide, pinned Docker image, run wrapper, .env)
Status: approved
Goal: foundation
Node: any
Deliverable: code
Verify: ./run --docker checks/run_checks.sh && ./run --native checks/run_checks.sh && ./run uv run pytest tests -q && test -f .env.example && ! git ls-files --error-unmatch .env
Hardware: none

## Goal
Anyone can set up a new Linux machine from `docs/setup.md` and get the same check results, either
with native KiCad 10.0.5 or with a pinned Docker image. It holds when the checks pass both ways
through the `./run` wrapper.

## Steps
1. `docker/Dockerfile`: based on the official KiCad image pinned to an exact 10.0.x tag and
   digest (confirm the tag that matches 10.0.5 exists; if not, record the nearest and why), plus
   Python, `uv`, `pandoc` and a PDF engine, `git-lfs`. Image name `fmcw3-tools`. Record
   `kicad-cli version` from inside the image in `docker/README.md`.
2. `run` (root, executable): `./run <cmd...>` runs the command in the container with the repo
   mounted and the caller's uid, passing `.env` when present; `--native` runs it on the host;
   with no flag it uses Docker when available and falls back to native. Builds the image on
   first use.
3. `pyproject.toml` and `uv.lock` for the repo's Python tooling (pytest, pyyaml, python-pptx,
   matplotlib, requests); `tests/` with a test of the baseline comparison logic in
   `checks/run_checks.sh` (fixture JSON: equal, more errors, fewer errors, unconnected > 0).
4. `.env.example` listing every key the tools read (DigiKey client id and secret now; JLCPCB or
   others later) with empty values and a comment per key. `.env` is gitignored. Port
   `parts/check_digikey.py` to read `.env`; the old `.digikey.env` name is dropped.
5. `docs/setup.md`: install KiCad 10.0.5 on Ubuntu (PPA and version pin), pointers for
   macOS/Windows, Docker, git-lfs, uv; how to get DigiKey API keys step by step and fill `.env`;
   how to run checks natively and in Docker; the rule that the GUI must be closed when tools
   edit project files. Have a fresh container follow the Docker path of the guide as a test.
6. Compare native and Docker ERC/DRC results once and record any difference in `checks/README.md`.
   Update `README.md` and `CLAUDE.md` with the `./run` commands.

## Out of scope
- Running the KiCad GUI in Docker.
- Simulation tools in the image (fnd-05 decides those).
- CI on GitHub.

## Allowed commands
- `docker build -t fmcw3-tools* *`
- `./run *`

## Log
